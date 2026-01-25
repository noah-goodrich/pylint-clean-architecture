"""Domain models for rules and fix suggestions."""

from dataclasses import dataclass, field
from typing import Any, Dict, List

import astroid


@dataclass(frozen=True)
class FixSuggestion:
    """A suggested fix for a code issue."""
    description: str
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Violation:
    """A rule violation with details."""
    rule_id: str
    message: str
    node: astroid.nodes.NodeNG = None  # type: ignore
    line: int = 0


class BaseRule:
    """Base class for architectural rules."""

    priority: int = 0

    def check(self, node: astroid.nodes.NodeNG, context: Dict[str, Any]) -> List[Violation]:
        """Check a node for violations."""
        raise NotImplementedError("Subclasses must implement check()")

    def fix(self, violation: Violation) -> List[FixSuggestion]:
        """Generate fix suggestions for a violation.

        Returns:
            List of FixSuggestion objects with commands for LibCST to apply.
            Return empty list if no automatic fix is available.
        """
        return []  # Default: no automatic fix
