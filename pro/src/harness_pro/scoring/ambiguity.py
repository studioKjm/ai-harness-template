"""Ambiguity scoring engine.

Formula: Ambiguity = 1 - Sum(clarity_i * weight_i)
Gate: Ambiguity <= 0.2 to proceed to Seed
"""

from __future__ import annotations

import yaml
from dataclasses import dataclass
from pathlib import Path
from rich.console import Console
from rich.table import Table


@dataclass
class DimensionResult:
    name: str
    weight: float
    score: float
    criteria_scores: list[tuple[str, float]]  # (question, score)

    @property
    def weighted_score(self) -> float:
        return self.weight * self.score


@dataclass
class AmbiguityResult:
    dimensions: list[DimensionResult]
    total_clarity: float
    ambiguity: float
    passed: bool  # ambiguity <= 0.2

    @property
    def gate_status(self) -> str:
        return "PASS" if self.passed else "FAIL"


class AmbiguityScorer:
    """Calculates ambiguity score from interview data."""

    CHECKLIST_PATH = Path(__file__).parent.parent.parent.parent.parent / "ouroboros" / "scoring" / "ambiguity-checklist.yaml"

    def __init__(self, project_root: Path = Path(".")):
        self.project_root = Path(project_root)
        self.console = Console()

    def calculate(self, interview_data: dict | None = None) -> AmbiguityResult:
        """Calculate ambiguity from interview data or latest interview file."""
        if interview_data is None:
            interview_data = self._load_latest_interview()

        if not interview_data:
            return AmbiguityResult(
                dimensions=[], total_clarity=0.0, ambiguity=1.0, passed=False
            )

        dimensions = []
        dims_data = interview_data.get("dimensions", {})

        for dim_name, dim_info in dims_data.items():
            weight = dim_info.get("weight", 0.0) if isinstance(dim_info, dict) else 0.25
            score = dim_info.get("score", 0.0) if isinstance(dim_info, dict) else float(dim_info)

            dimensions.append(DimensionResult(
                name=dim_name,
                weight=weight,
                score=score,
                criteria_scores=[],
            ))

        total_clarity = sum(d.weighted_score for d in dimensions)
        ambiguity = round(1.0 - total_clarity, 4)

        return AmbiguityResult(
            dimensions=dimensions,
            total_clarity=total_clarity,
            ambiguity=ambiguity,
            passed=ambiguity <= 0.2,
        )

    def calculate_from_criteria(self, criteria_scores: dict[str, list[float]]) -> AmbiguityResult:
        """Calculate from raw criteria scores per dimension.

        Args:
            criteria_scores: {"goal_clarity": [0.8, 0.9, ...], "constraint_clarity": [...]}
        """
        checklist = self._load_checklist()
        dimensions = []

        for dim_name, dim_config in checklist.get("dimensions", {}).items():
            weight = dim_config.get("weight", 0.25)
            scores = criteria_scores.get(dim_name, [])
            avg_score = sum(scores) / len(scores) if scores else 0.0

            criteria_pairs = []
            for i, criterion in enumerate(dim_config.get("criteria", [])):
                s = scores[i] if i < len(scores) else 0.0
                criteria_pairs.append((criterion.get("question", ""), s))

            dimensions.append(DimensionResult(
                name=dim_name,
                weight=weight,
                score=avg_score,
                criteria_scores=criteria_pairs,
            ))

        total_clarity = sum(d.weighted_score for d in dimensions)
        ambiguity = round(1.0 - total_clarity, 4)

        return AmbiguityResult(
            dimensions=dimensions,
            total_clarity=total_clarity,
            ambiguity=ambiguity,
            passed=ambiguity <= 0.2,
        )

    def display(self, result: AmbiguityResult) -> None:
        """Display ambiguity score as rich table."""
        table = Table(title="Ambiguity Score")
        table.add_column("Dimension", style="cyan")
        table.add_column("Score", justify="right")
        table.add_column("Weight", justify="right")
        table.add_column("Weighted", justify="right")

        for dim in result.dimensions:
            label = dim.name.replace("_", " ").title()
            table.add_row(
                label,
                f"{dim.score:.2f}",
                f"{dim.weight:.0%}",
                f"{dim.weighted_score:.2f}",
            )

        table.add_section()
        style = "green" if result.passed else "red"
        table.add_row("Total Clarity", f"{result.total_clarity:.2f}", "", "", style="bold")
        table.add_row("Ambiguity", f"{result.ambiguity:.2f}", "", f"Gate: {result.gate_status}", style=style)

        self.console.print(table)

    def _load_latest_interview(self) -> dict | None:
        interviews_dir = self.project_root / ".ouroboros" / "interviews"
        if not interviews_dir.exists():
            return None
        files = sorted(interviews_dir.glob("*.yaml"), reverse=True)
        if not files:
            return None
        with open(files[0]) as f:
            return yaml.safe_load(f)

    def _load_checklist(self) -> dict:
        if self.CHECKLIST_PATH.exists():
            with open(self.CHECKLIST_PATH) as f:
                return yaml.safe_load(f)
        # Fallback: look in project's .ouroboros
        alt = self.project_root / ".ouroboros" / "scoring" / "ambiguity-checklist.yaml"
        if alt.exists():
            with open(alt) as f:
                return yaml.safe_load(f)
        return {"dimensions": {}}
