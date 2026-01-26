"""Domain models for rules and violations."""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Protocol

import astroid  # type: ignore[import-untyped]

if TYPE_CHECKING:
    import libcst as cst


@dataclass(frozen=True)
class Violation:
    """A rule violation with code, message, location, and fixability."""

    code: str
    message: str
    location: str
    node: astroid.nodes.NodeNG
    fixable: bool = False
    fix_failure_reason: Optional[str] = None
    """Reason why an auto-fix wasn't possible (e.g., 'Inference failed', 'Banned Any type')."""


class BaseRule(Protocol):
    """The fundamental unit of architectural governance."""

    code: str
    description: str

    def check(self, node: astroid.nodes.NodeNG) -> List[Violation]:
        """Interrogate a node for a specific architectural breach."""
        ...

    def fix(self, violation: Violation) -> Optional["cst.CSTTransformer"]:
        """
        Return a transformer ONLY if the resolution is deterministic.
        
        If inference fails or would require banned types (e.g., Any), return None
        and ensure the Violation object captures the reason in fix_failure_reason.
        
        Returns:
            CSTTransformer if fix is deterministic and safe, None otherwise.
        """
        ...

    def get_fix_instructions(self, violation: Violation) -> str:
        """Provide human/AI instructions for a manual fix."""
        ...


@dataclass(frozen=True)
class FixSuggestion:
    """A suggested fix for a code issue. Retained for LibCST / apply_fixes."""

    description: str
    context: Dict[str, Any] = field(default_factory=dict)
