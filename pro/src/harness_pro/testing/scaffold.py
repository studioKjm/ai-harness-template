"""Test scaffold generator from seed spec acceptance criteria.

Reads acceptance_criteria from seed spec and generates test file
scaffolds with describe/it blocks (JS/TS) or test functions (Python).
"""

from __future__ import annotations

import re
import yaml
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class TestCase:
    ac_id: str
    description: str
    verification: str  # manual | automated | both
    priority: str  # must | should | nice
    test_name: str
    entity: str  # related entity if detectable


@dataclass
class TestScaffoldResult:
    test_cases: list[TestCase]
    output_files: list[Path]
    skipped: list[str]  # AC IDs skipped (manual only)


# Stack to test framework mapping
STACK_TEST_CONFIG = {
    "nextjs": {"framework": "jest", "ext": ".test.tsx", "dir": "__tests__"},
    "react": {"framework": "jest", "ext": ".test.tsx", "dir": "__tests__"},
    "nestjs": {"framework": "jest", "ext": ".spec.ts", "dir": "test"},
    "typescript": {"framework": "jest", "ext": ".test.ts", "dir": "__tests__"},
    "nodejs": {"framework": "jest", "ext": ".test.js", "dir": "__tests__"},
    "fastapi": {"framework": "pytest", "ext": "_test.py", "dir": "tests"},
    "django": {"framework": "pytest", "ext": "_test.py", "dir": "tests"},
    "flask": {"framework": "pytest", "ext": "_test.py", "dir": "tests"},
    "python": {"framework": "pytest", "ext": "_test.py", "dir": "tests"},
    "go": {"framework": "go-test", "ext": "_test.go", "dir": ""},
    "rust": {"framework": "cargo-test", "ext": ".rs", "dir": "tests"},
    "vue": {"framework": "vitest", "ext": ".test.ts", "dir": "__tests__"},
    "svelte": {"framework": "vitest", "ext": ".test.ts", "dir": "__tests__"},
    "sveltekit": {"framework": "vitest", "ext": ".test.ts", "dir": "__tests__"},
    "remix": {"framework": "vitest", "ext": ".test.ts", "dir": "__tests__"},
    "express": {"framework": "jest", "ext": ".test.ts", "dir": "__tests__"},
    "fastify": {"framework": "jest", "ext": ".test.ts", "dir": "__tests__"},
    "hono": {"framework": "vitest", "ext": ".test.ts", "dir": "__tests__"},
}


class TestScaffoldGenerator:
    """Generates test file scaffolds from seed spec acceptance criteria."""

    def __init__(self, project_root: Path = Path(".")):
        self.project_root = Path(project_root)

    def generate(self, stack: str = "typescript") -> TestScaffoldResult:
        """Generate test scaffolds from the latest seed spec."""
        seed = self._load_latest_seed()
        if not seed:
            return TestScaffoldResult(test_cases=[], output_files=[], skipped=[])

        criteria = seed.get("acceptance_criteria", [])
        ontology = seed.get("ontology", {})
        entity_names = {
            e.get("name", "").lower(): e.get("name", "")
            for e in ontology.get("entities", [])
            if e.get("name")
        }

        test_cases: list[TestCase] = []
        skipped: list[str] = []

        for ac in criteria:
            ac_id = ac.get("id", "")
            description = ac.get("description", "")
            verification = ac.get("verification", "automated")
            priority = ac.get("priority", "must")

            if not ac_id or not description:
                continue

            # Skip manual-only criteria
            if verification == "manual":
                skipped.append(ac_id)
                continue

            test_name = self._to_test_name(ac_id, description)
            entity = self._match_entity(description, entity_names)

            test_cases.append(TestCase(
                ac_id=ac_id,
                description=description,
                verification=verification,
                priority=priority,
                test_name=test_name,
                entity=entity,
            ))

        # Group by entity for file organization
        config = STACK_TEST_CONFIG.get(stack, STACK_TEST_CONFIG["typescript"])
        output_files = self._write_scaffolds(test_cases, config, seed)

        return TestScaffoldResult(
            test_cases=test_cases,
            output_files=output_files,
            skipped=skipped,
        )

    def _write_scaffolds(
        self,
        test_cases: list[TestCase],
        config: dict,
        seed: dict,
    ) -> list[Path]:
        """Write test scaffold files grouped by entity."""
        if not test_cases:
            return []

        test_dir = self.project_root / (config["dir"] or "tests")
        test_dir.mkdir(parents=True, exist_ok=True)

        # Group by entity
        groups: dict[str, list[TestCase]] = {}
        for tc in test_cases:
            key = tc.entity or "_general"
            groups.setdefault(key, []).append(tc)

        framework = config["framework"]
        ext = config["ext"]
        output_files: list[Path] = []
        goal = seed.get("goal", {}).get("summary", "")

        for group_name, cases in groups.items():
            filename = self._to_filename(group_name) + ext
            filepath = test_dir / filename
            content = self._render(framework, group_name, cases, goal)
            filepath.write_text(content, encoding="utf-8")
            output_files.append(filepath)

        return output_files

    def _render(
        self,
        framework: str,
        group_name: str,
        cases: list[TestCase],
        goal: str,
    ) -> str:
        """Render test file content for the given framework."""
        if framework in ("jest", "vitest"):
            return self._render_js(framework, group_name, cases, goal)
        elif framework == "pytest":
            return self._render_python(group_name, cases, goal)
        elif framework == "go-test":
            return self._render_go(group_name, cases, goal)
        elif framework == "cargo-test":
            return self._render_rust(group_name, cases, goal)
        return self._render_js("jest", group_name, cases, goal)

    @staticmethod
    def _render_js(
        framework: str,
        group_name: str,
        cases: list[TestCase],
        goal: str,
    ) -> str:
        """Render Jest/Vitest test scaffold."""
        lines = [
            f"/**",
            f" * Test scaffold for: {group_name}",
            f" * Goal: {goal}",
            f" * Generated: {datetime.now().strftime('%Y-%m-%d')}",
            f" * Source: seed spec acceptance criteria",
            f" */",
            f"",
        ]

        if framework == "vitest":
            lines.append("import { describe, it, expect } from 'vitest';")
        lines.append("")

        label = group_name if group_name != "_general" else "General"
        lines.append(f"describe('{label}', () => {{")

        for tc in cases:
            priority_tag = f" [{tc.priority.upper()}]" if tc.priority != "must" else ""
            lines.extend([
                f"  // {tc.ac_id}: {tc.description}",
                f"  it('{tc.test_name}'{priority_tag and ''}, () => {{",
                f"    // TODO: Implement test for {tc.ac_id}",
                f"    // Acceptance criteria: {tc.description}",
                f"    expect(true).toBe(false); // Replace with actual assertion",
                f"  }});",
                f"",
            ])

        lines.append("});")
        lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _render_python(
        group_name: str,
        cases: list[TestCase],
        goal: str,
    ) -> str:
        """Render pytest test scaffold."""
        lines = [
            f'"""',
            f"Test scaffold for: {group_name}",
            f"Goal: {goal}",
            f"Generated: {datetime.now().strftime('%Y-%m-%d')}",
            f"Source: seed spec acceptance criteria",
            f'"""',
            f"",
            f"import pytest",
            f"",
            f"",
        ]

        label = group_name if group_name != "_general" else "General"
        lines.append(f"class Test{label.replace(' ', '').title()}:")
        lines.append(f'    """Tests for {label}."""')
        lines.append("")

        for tc in cases:
            lines.extend([
                f"    def {tc.test_name}(self):",
                f'        """{tc.ac_id}: {tc.description}"""',
                f"        # TODO: Implement test for {tc.ac_id}",
                f"        # Acceptance criteria: {tc.description}",
                f"        assert False, 'Not implemented'",
                f"",
            ])

        return "\n".join(lines)

    @staticmethod
    def _render_go(
        group_name: str,
        cases: list[TestCase],
        goal: str,
    ) -> str:
        """Render Go test scaffold."""
        pkg = group_name.lower().replace(" ", "_") if group_name != "_general" else "main"
        lines = [
            f"// Test scaffold for: {group_name}",
            f"// Goal: {goal}",
            f"// Generated: {datetime.now().strftime('%Y-%m-%d')}",
            f"",
            f"package {pkg}",
            f"",
            f'import "testing"',
            f"",
        ]

        for tc in cases:
            func_name = "Test" + "".join(
                w.title() for w in re.sub(r"[^a-zA-Z0-9]+", " ", tc.test_name).split()
            )
            lines.extend([
                f"// {tc.ac_id}: {tc.description}",
                f"func {func_name}(t *testing.T) {{",
                f"\t// TODO: Implement test for {tc.ac_id}",
                f'\tt.Fatal("Not implemented")',
                f"}}",
                f"",
            ])

        return "\n".join(lines)

    @staticmethod
    def _render_rust(
        group_name: str,
        cases: list[TestCase],
        goal: str,
    ) -> str:
        """Render Rust test scaffold."""
        lines = [
            f"// Test scaffold for: {group_name}",
            f"// Goal: {goal}",
            f"// Generated: {datetime.now().strftime('%Y-%m-%d')}",
            f"",
            f"#[cfg(test)]",
            f"mod tests {{",
            f"",
        ]

        for tc in cases:
            func_name = re.sub(r"[^a-z0-9]+", "_", tc.test_name.lower()).strip("_")
            lines.extend([
                f"    // {tc.ac_id}: {tc.description}",
                f"    #[test]",
                f"    fn {func_name}() {{",
                f"        // TODO: Implement test for {tc.ac_id}",
                f'        panic!("Not implemented");',
                f"    }}",
                f"",
            ])

        lines.append("}")
        lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _to_test_name(ac_id: str, description: str) -> str:
        """Convert AC description to a test function name."""
        # Clean description to snake_case
        clean = re.sub(r"[^a-zA-Z0-9\s]", "", description.lower())
        words = clean.split()[:8]  # Limit length
        name = "_".join(words)
        return f"test_{ac_id.lower().replace('-', '_')}_{name}"

    @staticmethod
    def _match_entity(description: str, entity_names: dict[str, str]) -> str:
        """Try to match AC description to an entity name."""
        desc_lower = description.lower()
        for key, name in entity_names.items():
            if key in desc_lower:
                return name
        return ""

    @staticmethod
    def _to_filename(name: str) -> str:
        """Convert group name to a clean filename."""
        if name == "_general":
            return "general"
        clean = re.sub(r"[^a-zA-Z0-9]", "_", name.lower()).strip("_")
        return clean or "general"

    def _load_latest_seed(self) -> dict | None:
        seeds_dir = self.project_root / ".harness" / "ouroboros" / "seeds"
        if not seeds_dir.exists():
            return None
        files = sorted(seeds_dir.glob("seed-v*.yaml"), reverse=True)
        if not files:
            return None
        with open(files[0]) as f:
            return yaml.safe_load(f)
