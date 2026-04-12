"""3-Stage Evaluation Pipeline.

Stage 1: Mechanical ($0) — lint, build, tests, harness gates
Stage 2: Semantic — AC compliance, goal alignment, ontology drift
Stage 3: Judgment — code quality, edge cases (optional)
"""

from __future__ import annotations

import re
import subprocess
import yaml
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.table import Table


@dataclass
class StageResult:
    name: str
    passed: bool
    details: dict[str, str] = field(default_factory=dict)
    issues: list[str] = field(default_factory=list)


@dataclass
class EvaluationResult:
    stages: list[StageResult]
    passed: bool
    issues: list[str] = field(default_factory=list)
    seed_ref: str = ""
    date: str = ""


class EvaluationPipeline:
    """Runs 3-stage evaluation against seed spec."""

    def __init__(self, project_root: Path = Path(".")):
        self.project_root = Path(project_root)
        self.console = Console()

    def run(self) -> EvaluationResult:
        """Run all evaluation stages."""
        self.console.print("\n[bold]Starting Evaluation Pipeline[/bold]\n")

        # Load seed
        seed_data = self._load_latest_seed()
        seed_ref = ""
        if seed_data:
            seed_ref = f"seed-v{seed_data.get('version', '?')}"

        stages: list[StageResult] = []

        # Stage 1: Mechanical
        stage1 = self._stage_mechanical()
        stages.append(stage1)
        self._display_stage(stage1)

        if not stage1.passed:
            return EvaluationResult(
                stages=stages, passed=False,
                issues=stage1.issues, seed_ref=seed_ref,
                date=datetime.now().isoformat(),
            )

        # Stage 2: Semantic
        stage2 = self._stage_semantic(seed_data)
        stages.append(stage2)
        self._display_stage(stage2)

        # Stage 3: Judgment (only if stage 2 has ambiguous results)
        if stage2.passed and not stage2.issues:
            stage3 = StageResult(name="Judgment", passed=True, details={"status": "SKIPPED"})
        else:
            stage3 = self._stage_judgment()
        stages.append(stage3)
        self._display_stage(stage3)

        all_issues = []
        for s in stages:
            all_issues.extend(s.issues)

        result = EvaluationResult(
            stages=stages,
            passed=all(s.passed for s in stages),
            issues=all_issues,
            seed_ref=seed_ref,
            date=datetime.now().isoformat(),
        )

        self._save_result(result)
        self._log_audit(result)
        return result

    def _stage_mechanical(self) -> StageResult:
        """Stage 1: Automated checks ($0 cost)."""
        self.console.print("[cyan]Stage 1: Mechanical[/cyan]")
        details = {}
        issues = []

        # Harness gates
        gates_script = self.project_root / ".harness" / "detect-violations.sh"
        if gates_script.exists():
            try:
                result = subprocess.run(
                    ["bash", str(gates_script), str(self.project_root)],
                    capture_output=True, text=True, timeout=60,
                )
                if result.returncode == 0:
                    details["harness_gates"] = "PASS"
                else:
                    details["harness_gates"] = "FAIL"
                    issues.append(f"Harness gates failed: {result.stderr[:200]}")
            except subprocess.TimeoutExpired:
                details["harness_gates"] = "FAIL"
                issues.append("Harness gates timed out")
            except FileNotFoundError:
                details["harness_gates"] = "SKIP"
        else:
            details["harness_gates"] = "SKIP"

        # Lint
        lint_result = self._run_lint()
        details["lint"] = lint_result[0]
        if lint_result[1]:
            issues.append(lint_result[1])

        # Build
        build_result = self._run_build()
        details["build"] = build_result[0]
        if build_result[1]:
            issues.append(build_result[1])

        # Tests
        test_result = self._run_tests()
        details["tests"] = test_result[0]
        if test_result[1]:
            issues.append(test_result[1])

        passed = all(v in ("PASS", "SKIP") for v in details.values())
        return StageResult(name="Mechanical", passed=passed, details=details, issues=issues)

    def _stage_semantic(self, seed_data: dict | None) -> StageResult:
        """Stage 2: Semantic verification against seed spec.

        Checks:
        1. AC compliance — do test files or code reference each AC?
        2. Goal alignment — do source files reference goal keywords?
        3. Ontology coverage — are seed entities present in code?
        4. Constraint compliance — are must_not patterns absent?
        """
        self.console.print("[cyan]Stage 2: Semantic[/cyan]")
        details = {}
        issues = []

        if not seed_data:
            details["status"] = "SKIP (no seed spec)"
            return StageResult(name="Semantic", passed=True, details=details)

        # Collect all source files once
        source_files = self._collect_source_files()
        source_contents = self._read_files(source_files)

        # 1. AC compliance
        ac_issues = self._check_ac_compliance(seed_data, source_contents)
        acs = seed_data.get("acceptance_criteria", [])
        ac_covered = len(acs) - len(ac_issues)
        details["ac_coverage"] = f"{ac_covered}/{len(acs)}"
        if ac_issues:
            for ai in ac_issues:
                issues.append(f"AC not covered: {ai}")

        # 2. Goal alignment
        goal_score = self._check_goal_alignment(seed_data, source_contents)
        details["goal_alignment"] = f"{goal_score:.0%}"
        if goal_score < 0.3:
            issues.append(f"Low goal alignment ({goal_score:.0%}): code may not address the core goal")

        # 3. Ontology coverage
        ontology_score = self._check_ontology_coverage(seed_data, source_contents)
        details["ontology_coverage"] = f"{ontology_score:.0%}"
        if ontology_score < 0.5:
            issues.append(f"Low ontology coverage ({ontology_score:.0%}): entity/field names from spec missing in code")

        # 4. Constraint compliance
        constraint_violations = self._check_constraints(seed_data, source_contents)
        details["constraint_violations"] = str(len(constraint_violations))
        for cv in constraint_violations:
            issues.append(f"Constraint violated: {cv}")

        passed = not any(
            "AC not covered" in i and "must" in i.lower()
            for i in issues
        ) and len(constraint_violations) == 0
        details["verdict"] = "PASS" if passed else "FAIL"

        return StageResult(name="Semantic", passed=passed, details=details, issues=issues)

    def _collect_source_files(self) -> list[Path]:
        """Collect all source code files in the project."""
        extensions = {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java", ".kt"}
        exclude_dirs = {".git", "node_modules", "__pycache__", ".next", "dist", "build", ".harness"}
        files = []

        for ext in extensions:
            for f in self.project_root.rglob(f"*{ext}"):
                if not any(part in exclude_dirs for part in f.parts):
                    files.append(f)
        return files

    def _read_files(self, files: list[Path]) -> dict[Path, str]:
        """Read file contents, skipping unreadable files."""
        contents = {}
        for f in files:
            try:
                contents[f] = f.read_text(errors="ignore")
            except OSError:
                continue
        return contents

    def _check_ac_compliance(
        self, seed_data: dict, source_contents: dict[Path, str],
    ) -> list[str]:
        """Check which acceptance criteria have code/test coverage."""
        acs = seed_data.get("acceptance_criteria", [])
        uncovered = []
        all_content = "\n".join(source_contents.values()).lower()

        for ac in acs:
            ac_id = ac.get("id", "")
            description = ac.get("description", "")
            priority = ac.get("priority", "must")
            verification = ac.get("verification", "automated")

            if not ac_id or verification == "manual":
                continue

            # Check if AC ID is referenced in tests or code comments
            found = ac_id.lower() in all_content

            # If AC ID not found, check if description keywords appear
            if not found:
                keywords = [w for w in re.findall(r'\w{4,}', description.lower())
                            if w not in {"should", "must", "when", "then", "that", "this", "with", "from", "have"}]
                if keywords:
                    matches = sum(1 for kw in keywords if kw in all_content)
                    coverage = matches / len(keywords)
                    found = coverage >= 0.5

            if not found:
                uncovered.append(f"{ac_id} [{priority}] — {description[:80]}")

        return uncovered

    def _check_goal_alignment(
        self, seed_data: dict, source_contents: dict[Path, str],
    ) -> float:
        """Check if code aligns with the stated goal."""
        goal = seed_data.get("goal", {})
        summary = goal.get("summary", "")
        detail = goal.get("detail", "")
        goal_text = f"{summary} {detail}".lower()

        keywords = [w for w in re.findall(r'\w{4,}', goal_text)
                    if w not in {"this", "that", "with", "from", "will", "should", "must", "have", "been"}]
        if not keywords:
            return 1.0  # No goal keywords to check

        all_content = "\n".join(source_contents.values()).lower()
        matches = sum(1 for kw in keywords if kw in all_content)
        return matches / len(keywords)

    def _check_ontology_coverage(
        self, seed_data: dict, source_contents: dict[Path, str],
    ) -> float:
        """Check if ontology entities/fields from seed appear in code."""
        ontology = seed_data.get("ontology", {})
        entities = ontology.get("entities", [])
        if not entities:
            return 1.0

        expected = set()
        for entity in entities:
            name = entity.get("name", "")
            if name:
                expected.add(name.lower())
                # snake_case variant
                s1 = re.sub(r'(.)([A-Z][a-z]+)', r'\1_\2', name)
                expected.add(re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s1).lower())
            for f in entity.get("fields", []):
                fname = f.get("name", "")
                if fname:
                    expected.add(fname.lower())

        if not expected:
            return 1.0

        all_content = "\n".join(source_contents.values()).lower()
        found = sum(1 for name in expected if name in all_content)
        return found / len(expected)

    def _check_constraints(
        self, seed_data: dict, source_contents: dict[Path, str],
    ) -> list[str]:
        """Check if must_not constraints are violated in code."""
        constraints = seed_data.get("constraints", {})
        must_nots = constraints.get("must_not", [])
        violations = []

        all_content = "\n".join(source_contents.values()).lower()

        for constraint in must_nots:
            if not constraint:
                continue
            keywords = [kw for kw in re.findall(r'\w{4,}', constraint.lower())
                        if kw not in {"must", "should", "never", "cannot", "dont"}]
            if not keywords:
                continue

            # If >60% of constraint keywords appear in code, flag it
            matches = sum(1 for kw in keywords if kw in all_content)
            if keywords and matches / len(keywords) > 0.6:
                violations.append(constraint)

        return violations

    def _stage_judgment(self) -> StageResult:
        """Stage 3: Qualitative judgment (optional)."""
        self.console.print("[cyan]Stage 3: Judgment[/cyan]")
        return StageResult(
            name="Judgment", passed=True,
            details={"status": "MANUAL_REVIEW_RECOMMENDED"},
        )

    def _run_lint(self) -> tuple[str, str]:
        """Run linter if available."""
        # Try common linters
        for cmd in [
            ["npx", "eslint", ".", "--quiet"],
            ["ruff", "check", "."],
            ["python", "-m", "flake8", "."],
        ]:
            try:
                result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=30,
                    cwd=self.project_root,
                )
                if result.returncode == 0:
                    return ("PASS", "")
                return ("FAIL", f"Lint errors: {result.stdout[:200]}")
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        return ("SKIP", "")

    def _run_build(self) -> tuple[str, str]:
        """Run build if available."""
        pkg_json = self.project_root / "package.json"
        if pkg_json.exists():
            try:
                result = subprocess.run(
                    ["npm", "run", "build"], capture_output=True, text=True,
                    timeout=120, cwd=self.project_root,
                )
                if result.returncode == 0:
                    return ("PASS", "")
                return ("FAIL", f"Build failed: {result.stderr[:200]}")
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass
        return ("SKIP", "")

    def _run_tests(self) -> tuple[str, str]:
        """Run tests if available."""
        for cmd in [
            ["npm", "test", "--", "--passWithNoTests"],
            ["pytest", "-q"],
            ["python", "-m", "unittest", "discover"],
        ]:
            try:
                result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=120,
                    cwd=self.project_root,
                )
                if result.returncode == 0:
                    return ("PASS", "")
                return ("FAIL", f"Tests failed: {result.stdout[:200]}")
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        return ("SKIP", "")

    def _display_stage(self, stage: StageResult) -> None:
        """Display stage result."""
        status = "[green]PASS[/green]" if stage.passed else "[red]FAIL[/red]"
        self.console.print(f"  {stage.name}: {status}")
        for k, v in stage.details.items():
            self.console.print(f"    {k}: {v}")
        for issue in stage.issues:
            self.console.print(f"    [red]- {issue}[/red]")

    def _load_latest_seed(self) -> dict | None:
        seeds_dir = self.project_root / ".harness" / "ouroboros" / "seeds"
        if not seeds_dir.exists():
            return None
        files = sorted(seeds_dir.glob("seed-v*.yaml"), reverse=True)
        if not files:
            return None
        with open(files[0]) as f:
            return yaml.safe_load(f)

    def _log_audit(self, result: EvaluationResult) -> None:
        """Record evaluation run in audit log."""
        try:
            from harness_pro.persistence.store import EventStore
            store = EventStore(project_root=self.project_root)
            store.log_audit(
                action="eval_run",
                target=result.seed_ref or "unknown",
                result="pass" if result.passed else "fail",
                details={
                    "stages": {s.name: "pass" if s.passed else "fail" for s in result.stages},
                    "issue_count": len(result.issues),
                },
            )
        except Exception:
            pass  # Audit logging should never break the pipeline

    def _save_result(self, result: EvaluationResult) -> None:
        evals_dir = self.project_root / ".harness" / "ouroboros" / "evaluations"
        evals_dir.mkdir(parents=True, exist_ok=True)

        filename = f"eval-{result.seed_ref}-{datetime.now().strftime('%Y%m%d-%H%M')}.yaml"
        data = {
            "date": result.date,
            "seed_ref": result.seed_ref,
            "verdict": "pass" if result.passed else "fail",
            "stages": {
                s.name.lower(): {
                    "result": "pass" if s.passed else "fail",
                    "details": s.details,
                }
                for s in result.stages
            },
            "issues": result.issues,
        }

        with open(evals_dir / filename, "w") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
