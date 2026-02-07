"""Domain models for rules and violations."""

from dataclasses import dataclass, field

__all__ = [
    "BaseRule",
    "Checkable",
    "FixSuggestion",
    "Fixable",
    "StatefulRule",
    "Violation",
]

from typing import TYPE_CHECKING, Any, Literal, Optional, Protocol

import astroid

if TYPE_CHECKING:
    from excelsior_architect.domain.entities import TransformationPlan


@dataclass(frozen=True)
class Violation:
    """A rule violation with code, message, location, and fixability."""

    code: str
    message: str
    location: str
    node: astroid.nodes.NodeNG
    fixable: bool = False
    fix_failure_reason: str | None = None
    """Reason why an auto-fix wasn't possible (e.g., 'Inference failed', 'Banned Any type')."""
    is_comment_only: bool = False
    """True if fix injects governance comments only (not structural changes)."""
    message_args: tuple[str, ...] | None = None
    """Optional args for Pylint add_message (e.g. (class_name,)) when checker is thin."""

    @staticmethod
    def _location_from_node(node: astroid.nodes.NodeNG) -> str:
        """Compute path:lineno:col_offset from an astroid node. Used by from_node."""
        root = node.root()
        path = getattr(root, "file", "") or ""
        lineno = getattr(node, "lineno", 0)
        col_offset = getattr(node, "col_offset", 0)
        return f"{path}:{lineno}:{col_offset}"

    @classmethod
    def from_node(
        cls,
        *,
        code: str,
        message: str,
        node: astroid.nodes.NodeNG,
        fixable: bool = False,
        fix_failure_reason: str | None = None,
        is_comment_only: bool = False,
        message_args: tuple[str, ...] | None = None,
    ) -> "Violation":
        """Build a Violation with location derived from node. Prefer over manual location=."""
        location = cls._location_from_node(node)
        return cls(
            code=code,
            message=message,
            location=location,
            node=node,
            fixable=fixable,
            fix_failure_reason=fix_failure_reason,
            is_comment_only=is_comment_only,
            message_args=message_args,
        )


# -----------------------------------------------------------------------------
# Rule protocols: Checkable (one-and-done), Fixable (optional), StatefulRule
# (multi-step). Rules implement one or more; no rule is required to implement
# all. BaseRule = Checkable + Fixable for one-shot fixable rules (backward compat).
# -----------------------------------------------------------------------------


class Checkable(Protocol):
    """One-and-done check: given a node, return violations. No fix required."""

    code: str
    description: str

    def check(self, node: astroid.nodes.NodeNG) -> list[Violation]:
        """Interrogate a node for architectural breaches."""
        ...


class Fixable(Protocol):
    """Optional capability: rule can produce a fix or human fix instructions."""

    fix_type: Literal["code", "comment"]
    """Type of fix: 'code' for structural changes, 'comment' for governance comments only."""

    def fix(
        self, violation: Violation
    ) -> "TransformationPlan | list[TransformationPlan] | None":
        """
        Return a transformation plan (or list of plans) if the resolution is deterministic.

        If inference fails or would require banned types (e.g., Any), return None
        and ensure the Violation object captures the reason in fix_failure_reason.

        Returns:
            - TransformationPlan: Single transformation to apply
            - list[TransformationPlan]: Multiple transformations to apply in order
            - None: No deterministic fix available
        """
        ...

    def get_fix_instructions(self, violation: Violation) -> str:
        """Provide human/AI instructions for a manual fix."""
        ...


class StatefulRule(Protocol):
    """
    Multi-step rule driven by the checker across visit/leave callbacks.

    Checker holds state; rule receives context as arguments and remains stateless.
    This protocol describes the testing-coupling style API (record_*, leave_*).
    Other stateful rules (e.g. module structure, Demeter) may use different
    method sets and can have their own protocols or variants.
    """

    code_mocks: str
    code_private: str
    description: str

    def record_functiondef(
        self, node: astroid.nodes.NodeNG
    ) -> astroid.nodes.FunctionDef | None:
        """Return node if this starts a tracked scope (e.g. test_*); else None."""
        ...

    def record_call(
        self,
        node: astroid.nodes.NodeNG,
        current_function: astroid.nodes.FunctionDef | None,
    ) -> list[Violation]:
        """Called for each Call inside the scope. Return violations (e.g. W9102)."""
        ...

    def record_mock_only(
        self,
        node: astroid.nodes.NodeNG,
        current_function: astroid.nodes.FunctionDef | None,
    ) -> bool:
        """Return True if this call counts as a mock (caller increments count)."""
        ...

    def check_private_method(
        self,
        node: astroid.nodes.NodeNG,
        call_name: str,
        current_function: astroid.nodes.FunctionDef | None,
    ) -> list[Violation]:
        """Check for private method call violation (e.g. W9102). Used by checker/tests."""
        ...

    def leave_functiondef(
        self,
        current_function: astroid.nodes.FunctionDef | None,
        mock_count: int,
    ) -> list[Violation]:
        """Called when leaving the scope. Return violations (e.g. W9101)."""
        ...


class BaseRule(Checkable, Fixable, Protocol):
    """
    One-shot check + fix: Checkable + Fixable combined.

    Use for rules that have a single check(node) entrypoint and support
    fix / get_fix_instructions. Prefer implementing Checkable and Fixable
    separately when a rule is only checkable or only fixable.
    """

    code: str
    description: str
    fix_type: Literal["code", "comment"]

    def check(self, node: astroid.nodes.NodeNG) -> list[Violation]:
        """Interrogate a node for a specific architectural breach."""
        ...

    def fix(
        self, violation: Violation
    ) -> "TransformationPlan | list[TransformationPlan] | None":
        """
        Return a transformation plan (or list of plans) if the resolution is deterministic.

        Returns:
            - TransformationPlan: Single transformation to apply
            - list[TransformationPlan]: Multiple transformations to apply in order
            - None: No deterministic fix available
        """
        ...

    def get_fix_instructions(self, violation: Violation) -> str:
        """Provide human/AI instructions for a manual fix."""
        ...


@dataclass(frozen=True)
class FixSuggestion:
    """A suggested fix for a code issue. Retained for LibCST / apply_fixes."""

    description: str
    context: dict[str, Any] = field(default_factory=dict)
