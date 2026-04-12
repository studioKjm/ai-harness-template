"""Drift Monitor — measures deviation from seed spec after code changes.

Used as a PostToolUse hook: fires after every Write/Edit to check
if the implementation is drifting from the specification.
"""

from __future__ import annotations

import re
import yaml
from pathlib import Path


class DriftMonitor:
    """Measures how far the implementation has drifted from the seed spec."""

    def __init__(self, project_root: Path = Path(".")):
        self.project_root = Path(project_root)

    def measure(self, changed_file: Path) -> float:
        """Measure drift for a specific file change.

        Returns a score from 0.0 (no drift) to 1.0 (complete drift).
        """
        seed = self._load_latest_seed()
        if not seed:
            return 0.0  # No seed = no drift tracking

        scores = []

        # 1. Ontology alignment — are entity/field names from spec used in code?
        ontology_drift = self._check_ontology_alignment(seed, changed_file)
        scores.append(ontology_drift)

        # 2. Scope drift — is the file in an expected area?
        scope_drift = self._check_scope_drift(seed, changed_file)
        scores.append(scope_drift)

        # 3. Constraint compliance — any must_not patterns violated?
        constraint_drift = self._check_constraint_compliance(seed, changed_file)
        scores.append(constraint_drift)

        return round(sum(scores) / len(scores), 4) if scores else 0.0

    def _check_ontology_alignment(self, seed: dict, changed_file: Path) -> float:
        """Check if code uses entity/field names from the ontology.

        Returns 0.0 (aligned) to 1.0 (fully drifted).
        High coverage of ontology terms = low drift.
        """
        ontology = seed.get("ontology", {})
        entities = ontology.get("entities", [])
        if not entities:
            return 0.0

        # Skip non-code files early
        if changed_file.suffix not in {".py", ".ts", ".tsx", ".js", ".jsx", ".java", ".go", ".rs"}:
            return 0.0

        # Collect expected entity names (group variations per entity)
        entity_groups: list[set[str]] = []
        for entity in entities:
            name = entity.get("name", "")
            if not name:
                continue
            variants = {
                name.lower(),
                self._to_snake_case(name),
                self._to_camel_case(name),
            }
            entity_groups.append(variants)

        # Collect field names separately
        field_names: set[str] = set()
        for entity in entities:
            for f in entity.get("fields", []):
                fname = f.get("name", "")
                if fname:
                    field_names.add(fname.lower())
                    field_names.add(self._to_snake_case(fname))

        if not entity_groups and not field_names:
            return 0.0

        # Read the changed file
        try:
            content = changed_file.read_text(errors="ignore")
        except (OSError, UnicodeDecodeError):
            return 0.0

        content_lower = content.lower()

        # Count entity coverage: an entity is "found" if any of its variants appear
        entities_found = 0
        for variants in entity_groups:
            if any(v in content_lower for v in variants):
                entities_found += 1

        # Count field coverage
        fields_found = sum(1 for name in field_names if name in content_lower)

        # Calculate weighted coverage
        total_expected = len(entity_groups) + len(field_names)
        total_found = entities_found + fields_found

        if total_expected == 0:
            return 0.0

        coverage = total_found / total_expected

        # Drift = inverse of coverage (high coverage = low drift)
        # Utility files touching no ontology terms get moderate drift (0.5),
        # not maximum, since they may be legitimate infrastructure code.
        if total_found == 0:
            return 0.5  # No ontology terms at all — moderate signal
        return round(1.0 - coverage, 4)

    def _check_scope_drift(self, seed: dict, changed_file: Path) -> float:
        """Check if changes are within expected scope."""
        # Simple heuristic: if the file is in a new top-level directory
        # that wasn't part of the original structure, flag potential drift
        scope = seed.get("scope", {})
        non_goals = seed.get("goal", {}).get("non_goals", [])

        if not non_goals:
            return 0.0

        # Check if filename/path contains non-goal keywords
        file_str = str(changed_file).lower()
        for non_goal in non_goals:
            keywords = re.findall(r'\w+', non_goal.lower())
            matches = sum(1 for kw in keywords if kw in file_str and len(kw) > 3)
            if matches >= 2:
                return 0.5  # Possible scope creep

        return 0.0

    def _check_constraint_compliance(self, seed: dict, changed_file: Path) -> float:
        """Check must_not constraints against file content."""
        constraints = seed.get("constraints", {})
        must_nots = constraints.get("must_not", [])

        if not must_nots:
            return 0.0

        try:
            content = changed_file.read_text(errors="ignore").lower()
        except (OSError, UnicodeDecodeError):
            return 0.0

        violations = 0
        for constraint in must_nots:
            keywords = re.findall(r'\w+', constraint.lower())
            significant = [kw for kw in keywords if len(kw) > 3]
            matches = sum(1 for kw in significant if kw in content)
            if significant and matches / len(significant) > 0.5:
                violations += 1

        if violations > 0:
            return min(1.0, violations * 0.3)
        return 0.0

    def _load_latest_seed(self) -> dict | None:
        seeds_dir = self.project_root / ".ouroboros" / "seeds"
        if not seeds_dir.exists():
            return None
        files = sorted(seeds_dir.glob("seed-v*.yaml"), reverse=True)
        if not files:
            return None
        with open(files[0]) as f:
            return yaml.safe_load(f)

    @staticmethod
    def _to_snake_case(name: str) -> str:
        s1 = re.sub(r'(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

    @staticmethod
    def _to_camel_case(name: str) -> str:
        if "_" in name:
            parts = name.split("_")
            return parts[0].lower() + "".join(p.title() for p in parts[1:])
        return name[0].lower() + name[1:] if name else name
