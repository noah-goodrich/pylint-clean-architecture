"""Domain models for rules and violations."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Protocol

import astroid  # type: ignore[import-untyped]


@dataclass(frozen=True)
class Violation:
    """A rule violation with code, message, location, and fixability."""

    code: str
    message: str
    location: str
    node: astroid.nodes.NodeNG
    fixable: bool = False


class BaseRule(Protocol):
    """The fundamental unit of architectural governance."""

    code: str
    description: str

    def check(self, node: astroid.nodes.NodeNG) -> List[Violation]:
        """Interrogate a node for a specific architectural breach."""
        ...

    def get_fix_instructions(self, violation: Violation) -> str:
        """Provide human/AI instructions for a manual fix."""
        ...


@dataclass(frozen=True)
class FixSuggestion:
    """A suggested fix for a code issue. Retained for LibCST / apply_fixes."""

    description: str
    context: Dict[str, Any] = field(default_factory=dict)
