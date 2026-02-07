"""Method complexity rule (W9032): per-method cyclomatic complexity threshold."""

from typing import ClassVar

import astroid

from excelsior_architect.domain.rules import Checkable, Violation


class MethodComplexityRule(Checkable):
    """Rule for W9032: Per-method cyclomatic complexity exceeds threshold (complements W9010 God File)."""

    code: str = "W9032"
    description: str = "Method complexity: cyclomatic complexity exceeds threshold."
    fix_type: str = "code"

    DEFAULT_THRESHOLD: ClassVar[int] = 10

    def __init__(self, threshold: int | None = None) -> None:
        self._threshold = threshold if threshold is not None else self.DEFAULT_THRESHOLD

    def check(self, node: astroid.nodes.NodeNG) -> list[Violation]:
        """Check a FunctionDef for cyclomatic complexity. Returns violations if over threshold."""
        if not isinstance(node, astroid.nodes.FunctionDef):
            return []
        complexity = self._cyclomatic_complexity(node)
        if complexity <= self._threshold:
            return []
        name = getattr(node, "name", "?")
        return [
            Violation.from_node(
                code=self.code,
                message=f"Method '{name}' has cyclomatic complexity {complexity} (threshold {self._threshold}). Extract logic into smaller functions.",
                node=node,
                message_args=(name, str(complexity), str(self._threshold)),
            )
        ]

    def _cyclomatic_complexity(self, node: astroid.nodes.FunctionDef) -> int:
        """Count decision points: if/elif/else, for, while, except, and/or in conditions, ternary (IfExp)."""
        count = 1  # base
        for child in node.nodes_of_class(
            (
                astroid.nodes.If,
                astroid.nodes.For,
                astroid.nodes.While,
                astroid.nodes.ExceptHandler,
                astroid.nodes.With,
                astroid.nodes.Assert,
                astroid.nodes.Comprehension,
            )
        ):
            count += 1
        # BoolOp (and/or) adds (n - 1) to complexity
        for bool_op in node.nodes_of_class(astroid.nodes.BoolOp):
            count += max(0, len(getattr(bool_op, "values", [])) - 1)
        # IfExp (ternary) adds 1
        for _ in node.nodes_of_class(astroid.nodes.IfExp):
            count += 1
        return count
