"""Socratic Interview Engine with ambiguity scoring."""

from __future__ import annotations

import re
import yaml
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class InterviewAnswer:
    question: str
    answer: str
    dimension: str  # goal | constraint | success | context
    clarity_delta: float = 0.0


@dataclass
class InterviewResult:
    topic: str
    date: str
    ambiguity: float
    dimensions: dict[str, float]
    answers: list[InterviewAnswer]
    decisions: list[str]
    assumptions_surfaced: list[str]
    questions: list[dict[str, str]] = field(default_factory=list)
    output_path: str = ""


@dataclass
class DimensionScore:
    name: str
    weight: float
    score: float = 0.0
    criteria: list[dict[str, Any]] = field(default_factory=list)


# Dimension-specific interview questions
INTERVIEW_QUESTIONS: dict[str, list[dict[str, str]]] = {
    "goal_clarity": [
        {"id": "G1", "question": "What is the core problem this solves? (one sentence)"},
        {"id": "G2", "question": "Who is the primary end user?"},
        {"id": "G3", "question": "Describe the ideal success scenario step by step."},
        {"id": "G4", "question": "What happens if this doesn't exist? What pain remains?"},
        {"id": "G5", "question": "What is MVP scope vs future scope?"},
    ],
    "constraint_clarity": [
        {"id": "C1", "question": "What must this system NEVER do?"},
        {"id": "C2", "question": "Are there tech stack constraints? (language, framework, infra)"},
        {"id": "C3", "question": "What external systems does this integrate with?"},
        {"id": "C4", "question": "Rank priority: performance > security > cost, or different?"},
    ],
    "success_criteria": [
        {"id": "S1", "question": "How will you verify this is done? (testable criteria)"},
        {"id": "S2", "question": "What edge cases have you identified?"},
        {"id": "S3", "question": "Manual or automated verification?"},
        {"id": "S4", "question": "What does failure look like? Define failure scenarios."},
    ],
    "context_clarity": [
        {"id": "X1", "question": "Describe the existing code structure and key modules."},
        {"id": "X2", "question": "What is the blast radius of this change?"},
        {"id": "X3", "question": "What existing tests cover the affected area?"},
    ],
}

# Keywords that indicate clarity per dimension
CLARITY_SIGNALS: dict[str, list[str]] = {
    "goal_clarity": [
        "must", "should", "goal", "purpose", "so that", "in order to",
        "user", "customer", "admin", "developer", "mvp", "scope",
    ],
    "constraint_clarity": [
        "never", "must not", "cannot", "forbidden", "require",
        "stack", "framework", "api", "integrate", "performance", "security",
    ],
    "success_criteria": [
        "test", "verify", "assert", "expect", "when", "then", "given",
        "edge case", "failure", "error", "timeout", "retry",
    ],
    "context_clarity": [
        "existing", "current", "legacy", "migration", "refactor",
        "module", "component", "dependency", "affected", "blast radius",
    ],
}


class InterviewEngine:
    """Manages interview sessions with ambiguity tracking."""

    DIMENSIONS_GREENFIELD = {
        "goal_clarity": DimensionScore("goal_clarity", 0.40),
        "constraint_clarity": DimensionScore("constraint_clarity", 0.30),
        "success_criteria": DimensionScore("success_criteria", 0.30),
    }

    DIMENSIONS_BROWNFIELD = {
        "goal_clarity": DimensionScore("goal_clarity", 0.35),
        "constraint_clarity": DimensionScore("constraint_clarity", 0.25),
        "success_criteria": DimensionScore("success_criteria", 0.25),
        "context_clarity": DimensionScore("context_clarity", 0.15),
    }

    def __init__(self, project_root: Path = Path(".")):
        self.project_root = Path(project_root)
        self.ouroboros_dir = self.project_root / ".ouroboros"
        self.interviews_dir = self.ouroboros_dir / "interviews"
        self.interviews_dir.mkdir(parents=True, exist_ok=True)

        self.is_brownfield = self._detect_brownfield()
        self.dimensions = (
            {k: DimensionScore(v.name, v.weight) for k, v in self.DIMENSIONS_BROWNFIELD.items()}
            if self.is_brownfield
            else {k: DimensionScore(v.name, v.weight) for k, v in self.DIMENSIONS_GREENFIELD.items()}
        )
        self.answers: list[InterviewAnswer] = []
        self.decisions: list[str] = []
        self.assumptions: list[str] = []

    def _detect_brownfield(self) -> bool:
        """Detect if project has existing code."""
        git_dir = self.project_root / ".git"
        if git_dir.exists():
            log_file = git_dir / "logs" / "HEAD"
            if log_file.exists() and log_file.stat().st_size > 0:
                return True
        # Check for common source directories
        for d in ["src", "app", "lib", "components", "pages"]:
            if (self.project_root / d).is_dir():
                return True
        return False

    def get_questions(self) -> list[dict[str, str]]:
        """Get interview questions for active dimensions."""
        questions = []
        for dim_name in self.dimensions:
            for q in INTERVIEW_QUESTIONS.get(dim_name, []):
                questions.append({"dimension": dim_name, **q})
        return questions

    def _score_answer_clarity(self, answer: str, dimension: str) -> float:
        """Score how much clarity an answer provides (0.0-1.0).

        Uses signal keywords, answer length, and specificity heuristics.
        """
        if not answer or not answer.strip():
            return 0.0

        text = answer.lower()
        score = 0.0

        # Length score: very short answers are vague (max 0.3)
        word_count = len(text.split())
        if word_count >= 20:
            score += 0.3
        elif word_count >= 10:
            score += 0.2
        elif word_count >= 5:
            score += 0.1

        # Signal keyword matches (max 0.4)
        signals = CLARITY_SIGNALS.get(dimension, [])
        if signals:
            matches = sum(1 for s in signals if s in text)
            signal_ratio = min(matches / max(len(signals) * 0.4, 1), 1.0)
            score += 0.4 * signal_ratio

        # Specificity: contains concrete nouns, numbers, or proper names (max 0.3)
        has_numbers = bool(re.search(r'\d+', text))
        has_specifics = bool(re.search(r'(?:api|db|sql|http|jwt|oauth|redis|postgres|mongo)', text))
        has_concrete_refs = bool(re.search(r'(?:file|endpoint|table|column|field|route|page|component)', text))
        specificity = sum([has_numbers, has_specifics, has_concrete_refs])
        score += 0.1 * specificity

        return min(score, 1.0)

    def calculate_ambiguity(self) -> float:
        """Calculate ambiguity score: 1.0 - weighted_clarity."""
        total_clarity = 0.0
        for dim in self.dimensions.values():
            total_clarity += dim.weight * dim.score
        return round(1.0 - total_clarity, 4)

    def update_dimension(self, dimension: str, score: float) -> None:
        """Update a dimension's clarity score (0.0-1.0)."""
        if dimension in self.dimensions:
            self.dimensions[dimension].score = max(0.0, min(1.0, score))

    def add_answer(self, answer: InterviewAnswer) -> None:
        """Record an interview answer and update dimensions."""
        # Auto-calculate clarity delta if not provided
        if answer.clarity_delta == 0.0:
            answer.clarity_delta = self._score_answer_clarity(
                answer.answer, answer.dimension
            )

        self.answers.append(answer)
        if answer.dimension in self.dimensions:
            current = self.dimensions[answer.dimension].score
            # Diminishing returns: each answer contributes less as score rises
            remaining = 1.0 - current
            effective_delta = answer.clarity_delta * remaining
            new_score = min(1.0, current + effective_delta)
            self.dimensions[answer.dimension].score = new_score

    def _extract_decisions(self) -> list[str]:
        """Extract implicit decisions from answers."""
        decisions = []
        decision_patterns = [
            r'(?:will use|using|chose|decided on|going with)\s+([^.,]+)',
            r'(?:must be|should be|needs to be)\s+([^.,]+)',
            r'(?:stack|framework|language|tool)(?:\s+is)?\s*:?\s*([^.,]+)',
        ]
        for answer in self.answers:
            text = answer.answer
            for pattern in decision_patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    decision = match.group(1).strip()
                    if len(decision.split()) <= 8 and decision not in decisions:
                        decisions.append(decision)
        return decisions

    def _extract_assumptions(self) -> list[str]:
        """Surface implicit assumptions from answers."""
        assumptions = []
        assumption_patterns = [
            r'(?:I assume|assuming|probably|I think|likely|should be)\s+([^.,]+)',
            r'(?:not sure|unclear|TBD|to be decided)\s*(?:about|whether|if)?\s*([^.,]*)',
        ]
        for answer in self.answers:
            text = answer.answer
            for pattern in assumption_patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    assumption = match.group(1).strip()
                    if assumption and assumption not in assumptions:
                        assumptions.append(assumption)
        return assumptions

    def start(self, topic: str) -> InterviewResult:
        """Start an interview session.

        Generates dimension-specific questions and creates a structured
        interview template. When answers are already recorded (via add_answer),
        calculates clarity scores per dimension.
        """
        questions = self.get_questions()

        # If no answers recorded yet, create template with questions only
        # (CLI/AI will fill in answers interactively)
        if not self.answers:
            # Score initial topic for goal_clarity baseline
            topic_clarity = self._score_answer_clarity(topic, "goal_clarity")
            if topic_clarity > 0:
                self.add_answer(InterviewAnswer(
                    question="What do you want to build?",
                    answer=topic,
                    dimension="goal_clarity",
                ))

        # Extract decisions and assumptions from collected answers
        if not self.decisions:
            self.decisions = self._extract_decisions()
        if not self.assumptions:
            self.assumptions = self._extract_assumptions()

        result = InterviewResult(
            topic=topic,
            date=datetime.now().isoformat(),
            ambiguity=self.calculate_ambiguity(),
            dimensions={k: v.score for k, v in self.dimensions.items()},
            answers=self.answers,
            decisions=self.decisions,
            assumptions_surfaced=self.assumptions,
            questions=questions,
        )
        result.output_path = str(self._save(result))
        return result

    def get_score_display(self) -> str:
        """Generate ambiguity score display string."""
        lines = [
            "+---------------------------------+",
            "| Ambiguity Score                 |",
            "+--------------+------------------+",
        ]
        for name, dim in self.dimensions.items():
            label = name.replace("_", " ").title()
            pct = f"({dim.weight:.0%})"
            lines.append(f"| {label:<12} | {dim.score:.2f} / 1.0 {pct:>5} |")

        ambiguity = self.calculate_ambiguity()
        lines.extend([
            "+--------------+------------------+",
            f"| AMBIGUITY    | {ambiguity:.2f}              |",
            f"| GATE         | {'PASS' if ambiguity <= 0.2 else 'FAIL':>4} (<= 0.2)      |",
            "+--------------+------------------+",
        ])
        return "\n".join(lines)

    def _save(self, result: InterviewResult) -> Path:
        """Save interview results to YAML."""
        filename = datetime.now().strftime("%Y-%m-%d-%H-%M") + ".yaml"
        output_path = self.interviews_dir / filename

        data = {
            "date": result.date,
            "topic": result.topic,
            "brownfield": self.is_brownfield,
            "dimensions": {
                k: {"weight": self.dimensions[k].weight, "score": v}
                for k, v in result.dimensions.items()
            },
            "ambiguity_score": result.ambiguity,
            "questions": result.questions,
            "answers": [
                {
                    "question": a.question,
                    "answer": a.answer,
                    "dimension": a.dimension,
                    "clarity_delta": a.clarity_delta,
                }
                for a in result.answers
            ],
            "decisions": result.decisions,
            "assumptions_surfaced": result.assumptions,
        }

        with open(output_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

        return output_path

    def load_latest(self) -> dict | None:
        """Load the most recent interview data."""
        files = sorted(self.interviews_dir.glob("*.yaml"), reverse=True)
        if not files:
            return None
        with open(files[0]) as f:
            return yaml.safe_load(f)
