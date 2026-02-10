"""Bridges SAE diagnosis to machine-readable refactor steps. Domain-only."""
from typing import List, TypedDict

from excelsior_architect.domain.sae_entities import RecommendedStrategy


class SAETransformationContext(TypedDict, total=False):
    """Machine-readable refactor step from SAE blueprint."""
    pattern: str
    affected_files: list[str]
    violations: list[str]
    rationale: str
    steps: list[str]


class SAETranslator:
    """Maps graph diagnosis to transformation contexts for the fixer."""

    def translate_blueprint_to_contexts(
        self, diagnosis: List[RecommendedStrategy]
    ) -> List[SAETransformationContext]:
        """Turn strategy recommendations into machine-readable refactor steps."""
        return [
            {
                "pattern": rec["pattern"],
                "affected_files": list(rec["affected_files"]),
                "violations": list(rec["violations"]),
                "rationale": rec.get("rationale", ""),
                "steps": [],
            }
            for rec in diagnosis
        ]
