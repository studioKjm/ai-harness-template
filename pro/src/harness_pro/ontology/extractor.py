"""Ontology extraction and comparison engine.

Extracts domain models from interview data and measures
ontology similarity across seed generations for convergence detection.
"""

from __future__ import annotations

import re
import yaml
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class Entity:
    name: str
    fields: list[dict[str, str]] = field(default_factory=list)
    relationships: list[dict[str, str]] = field(default_factory=list)


@dataclass
class Action:
    name: str
    actor: str = ""
    input: str = ""
    output: str = ""
    side_effects: list[str] = field(default_factory=list)


@dataclass
class Ontology:
    entities: list[Entity] = field(default_factory=list)
    actions: list[Action] = field(default_factory=list)

    @property
    def entity_names(self) -> set[str]:
        return {e.name for e in self.entities}

    @property
    def field_names(self) -> set[str]:
        names = set()
        for e in self.entities:
            for f in e.fields:
                names.add(f"{e.name}.{f.get('name', '')}")
        return names

    @property
    def field_types(self) -> dict[str, str]:
        types = {}
        for e in self.entities:
            for f in e.fields:
                key = f"{e.name}.{f.get('name', '')}"
                types[key] = f.get("type", "unknown")
        return types


# Common stop words to exclude from entity extraction
_STOP_WORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "must", "this",
    "that", "these", "those", "i", "you", "we", "they", "it", "my",
    "your", "our", "their", "its", "what", "which", "who", "when",
    "where", "how", "not", "no", "yes", "all", "each", "every", "some",
    "any", "few", "more", "most", "other", "also", "just", "about",
    "very", "too", "so", "than", "then", "there", "here", "with",
    "from", "into", "for", "and", "but", "or", "if", "of", "in", "on",
    "at", "to", "by", "up", "out", "off", "over", "under", "again",
    "further", "once", "use", "using", "used", "like", "want", "make",
    "thing", "something", "nothing", "everything", "way", "case",
}

# Relationship indicator patterns
_RELATIONSHIP_PATTERNS = [
    (r'(\w+)\s+(?:has|have|contains?|includes?)\s+(?:many|multiple|several)\s+(\w+)', "has_many"),
    (r'(\w+)\s+(?:has|have|contains?|includes?)\s+(?:a|an|one)\s+(\w+)', "has_one"),
    (r'(\w+)\s+(?:belongs?\s+to|is\s+part\s+of|is\s+owned\s+by)\s+(\w+)', "belongs_to"),
    (r'(\w+)\s+(?:creates?|generates?|produces?)\s+(\w+)', "creates"),
    (r'(\w+)\s+(?:sends?|emits?|publishes?)\s+(\w+)', "sends"),
]

# Action verb patterns
_ACTION_PATTERNS = [
    r'(\w+)\s+(create|delete|update|send|receive|process|validate|authenticate|authorize|upload|download|search|filter|sort|export|import|notify|subscribe|cancel|approve|reject|pay|refund)s?\s+(?:a|an|the)?\s*(\w+)',
    r'(user|admin|system|api|service|worker|cron)\s+(?:can|will|should|must)\s+(create|delete|update|send|receive|process|validate|upload|download|search|filter|export|import|notify)\s+(\w+)',
]


class OntologyExtractor:
    """Extracts ontology from interview data and generates seed specs."""

    def extract_from_interview(self, interview_data: dict) -> Ontology:
        """Extract ontology hints from interview answers.

        Parses answers for:
        - Entity candidates: capitalized terms, domain nouns, repeated nouns
        - Relationships: "has many", "belongs to", etc.
        - Actions: verb patterns with actor/object
        """
        all_text = self._collect_text(interview_data)
        entities = self._extract_entities(all_text)
        relationships = self._extract_relationships(all_text, entities)
        actions = self._extract_actions(all_text)

        # Attach relationships to entities
        for rel in relationships:
            source_name = rel["source"]
            for entity in entities:
                if entity.name.lower() == source_name.lower():
                    entity.relationships.append({
                        "type": rel["type"],
                        "target": rel["target"],
                    })
                    break

        return Ontology(entities=entities, actions=actions)

    @staticmethod
    def _collect_text(interview_data: dict) -> str:
        """Collect all text from interview for analysis."""
        parts = [interview_data.get("topic", "")]
        for answer in interview_data.get("answers", []):
            parts.append(answer.get("answer", ""))
        for decision in interview_data.get("decisions", []):
            parts.append(decision if isinstance(decision, str) else str(decision))
        return " ".join(parts)

    @staticmethod
    def _extract_entities(text: str) -> list[Entity]:
        """Extract entity candidates from text using heuristics."""
        # Strategy 1: Capitalized multi-word terms (e.g., "User Profile")
        capitalized = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', text)

        # Strategy 2: Frequent nouns (words appearing 2+ times, not stop words)
        words = re.findall(r'\b([a-zA-Z]{3,})\b', text.lower())
        word_freq: dict[str, int] = {}
        for w in words:
            if w not in _STOP_WORDS:
                word_freq[w] = word_freq.get(w, 0) + 1
        frequent_nouns = [w for w, count in word_freq.items() if count >= 2]

        # Strategy 3: Domain-specific patterns
        domain_patterns = re.findall(
            r'\b(user|account|order|product|item|payment|session|token|role|'
            r'message|notification|comment|post|file|image|report|dashboard|'
            r'project|task|team|member|invoice|subscription|plan|event|log|'
            r'category|tag|setting|config|permission|webhook|api|endpoint|'
            r'database|table|queue|cache|worker|service)\b',
            text.lower()
        )

        # Merge and deduplicate candidates
        seen: set[str] = set()
        entities: list[Entity] = []

        # Capitalized terms get priority (likely proper domain names)
        for term in capitalized:
            normalized = term.strip()
            key = normalized.lower()
            if key not in seen and key not in _STOP_WORDS and len(key) > 2:
                seen.add(key)
                entities.append(Entity(name=normalized))

        # Add frequent nouns and domain terms
        for term in frequent_nouns + domain_patterns:
            key = term.lower()
            if key not in seen and len(key) > 2:
                seen.add(key)
                # Title case for consistency
                entities.append(Entity(name=term.title()))

        return entities

    @staticmethod
    def _extract_relationships(text: str, entities: list[Entity]) -> list[dict[str, str]]:
        """Extract relationships between entities."""
        relationships: list[dict[str, str]] = []
        entity_names_lower = {e.name.lower() for e in entities}

        for pattern, rel_type in _RELATIONSHIP_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                source = match.group(1).lower()
                target = match.group(2).lower()
                # Only keep if both sides are known entities (or close matches)
                source_match = source in entity_names_lower
                target_match = target in entity_names_lower
                if source_match or target_match:
                    relationships.append({
                        "source": source.title(),
                        "type": rel_type,
                        "target": target.title(),
                    })

        return relationships

    @staticmethod
    def _extract_actions(text: str) -> list[Action]:
        """Extract actions from verb patterns."""
        actions: list[Action] = []
        seen_actions: set[str] = set()

        for pattern in _ACTION_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                actor = match.group(1).title()
                verb = match.group(2).lower()
                obj = match.group(3).title()
                action_key = f"{verb}_{obj}".lower()

                if action_key not in seen_actions:
                    seen_actions.add(action_key)
                    actions.append(Action(
                        name=f"{verb}_{obj}".lower(),
                        actor=actor,
                        input=obj,
                        output=obj,
                    ))

        return actions

    def generate_seed(self, interview_data: dict, project_root: Path) -> Path:
        """Generate a seed spec YAML from interview data."""
        seeds_dir = project_root / ".ouroboros" / "seeds"
        seeds_dir.mkdir(parents=True, exist_ok=True)

        # Determine version
        existing = sorted(seeds_dir.glob("seed-v*.yaml"))
        version = len(existing) + 1

        seed_data = {
            "version": version,
            "created": datetime.now().isoformat(),
            "interview_ref": interview_data.get("date", ""),
            "goal": {
                "summary": interview_data.get("topic", ""),
                "detail": "",
                "non_goals": [],
            },
            "constraints": {
                "must": [],
                "must_not": [],
                "should": [],
            },
            "acceptance_criteria": [],
            "ontology": {
                "entities": [],
                "actions": [],
            },
            "scope": {
                "mvp": [],
                "future": [],
            },
            "tech_decisions": [],
        }

        # Extract from interview decisions/answers
        for decision in interview_data.get("decisions", []):
            seed_data["tech_decisions"].append({
                "decision": decision,
                "reason": "",
                "alternatives_considered": [],
            })

        output_path = seeds_dir / f"seed-v{version}.yaml"
        with open(output_path, "w") as f:
            yaml.dump(seed_data, f, default_flow_style=False, allow_unicode=True)

        return output_path

    @staticmethod
    def similarity(a: Ontology, b: Ontology) -> float:
        """Calculate ontology similarity between two versions.

        Formula:
            0.5 * name_overlap + 0.3 * type_match + 0.2 * exact_match

        Returns: float between 0.0 and 1.0
        """
        if not a.entity_names and not b.entity_names:
            return 1.0  # Both empty = identical

        # Name overlap (entity + field names)
        all_names_a = a.entity_names | a.field_names
        all_names_b = b.entity_names | b.field_names
        all_names = all_names_a | all_names_b
        if not all_names:
            name_overlap = 1.0
        else:
            common_names = all_names_a & all_names_b
            name_overlap = len(common_names) / len(all_names)

        # Type match (for common fields)
        types_a = a.field_types
        types_b = b.field_types
        common_fields = set(types_a.keys()) & set(types_b.keys())
        if not common_fields:
            type_match = 1.0 if not types_a and not types_b else 0.0
        else:
            matching_types = sum(1 for f in common_fields if types_a[f] == types_b[f])
            type_match = matching_types / len(common_fields)

        # Exact match (field name + type + required)
        exact_a = {
            f"{e.name}.{f.get('name')}:{f.get('type')}:{f.get('required', False)}"
            for e in a.entities for f in e.fields
        }
        exact_b = {
            f"{e.name}.{f.get('name')}:{f.get('type')}:{f.get('required', False)}"
            for e in b.entities for f in e.fields
        }
        all_exact = exact_a | exact_b
        if not all_exact:
            exact_match = 1.0
        else:
            exact_match = len(exact_a & exact_b) / len(all_exact)

        return round(0.5 * name_overlap + 0.3 * type_match + 0.2 * exact_match, 4)

    @staticmethod
    def load_from_seed(seed_path: Path) -> Ontology:
        """Load ontology from a seed YAML file."""
        with open(seed_path) as f:
            data = yaml.safe_load(f)

        ontology_data = data.get("ontology", {})
        entities = []
        for e in ontology_data.get("entities", []):
            entities.append(Entity(
                name=e.get("name", ""),
                fields=e.get("fields", []),
                relationships=e.get("relationships", []),
            ))

        actions = []
        for a in ontology_data.get("actions", []):
            actions.append(Action(
                name=a.get("name", ""),
                actor=a.get("actor", ""),
                input=a.get("input", ""),
                output=a.get("output", ""),
                side_effects=a.get("side_effects", []),
            ))

        return Ontology(entities=entities, actions=actions)
