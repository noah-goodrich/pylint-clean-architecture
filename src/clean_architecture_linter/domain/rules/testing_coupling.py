"""Test coupling rules (W9101, W9102)."""

from __future__ import annotations

import astroid  # type: ignore[import-untyped]

from clean_architecture_linter.domain.rules import StatefulRule, Violation

_MOCK_LIMIT: int = 4


class TestingCouplingRule(StatefulRule):
    """Rule for W9101 (fragile-test-mocks), W9102 (private method testing).

    Implements StatefulRule: stateless; checker holds state and passes context in.
    """

    code_mocks: str = "W9101"
    code_private: str = "W9102"
    description: str = "Test coupling: limit mocks; avoid testing private methods."
    fix_type: str = "code"

    def record_functiondef(
        self, node: astroid.nodes.NodeNG
    ) -> astroid.nodes.FunctionDef | None:
        """Return node if this is a test_* function (caller sets current_function and resets mock_count), else None."""
        if not hasattr(node, "name") or not getattr(node, "name", "").startswith("test_"):
            return None
        return node

    def record_call(
        self,
        node: astroid.nodes.NodeNG,
        current_function: astroid.nodes.FunctionDef | None,
    ) -> list[Violation]:
        """Call for each Call in a test function. Returns W9102 violations (private method)."""
        violations: list[Violation] = []
        if not current_function:
            return violations
        call_name = ""
        func = getattr(node, "func", None)
        if func and hasattr(func, "attrname"):
            call_name = getattr(func, "attrname", "") or ""
        elif func and hasattr(func, "name"):
            call_name = getattr(func, "name", "") or ""
        if call_name and call_name.startswith("_") and not call_name.startswith("__"):
            if func and hasattr(func, "expr"):
                expr = getattr(func, "expr", None)
                if expr and getattr(expr, "name", None) in ("self", "cls"):
                    return violations
            violations.append(
                Violation.from_node(
                    code=self.code_private,
                    message=f"Private method testing: {call_name}.",
                    node=node,
                    message_args=(call_name,),
                )
            )
        return violations

    def record_mock_only(
        self,
        node: astroid.nodes.NodeNG,
        current_function: astroid.nodes.FunctionDef | None,
    ) -> bool:
        """Return True if call is Mock/MagicMock/patch (caller increments mock_count)."""
        if not current_function:
            return False
        call_str = getattr(node, "as_string", lambda: "")()
        if call_str and ("Mock(" in call_str or "MagicMock(" in call_str or "patch(" in call_str):
            return True
        return False

    def check_private_method(
        self,
        node: astroid.nodes.NodeNG,
        call_name: str,
        current_function: astroid.nodes.FunctionDef | None,
    ) -> list[Violation]:
        """Check for W9102 (private method call) only. Used by tests."""
        if not current_function:
            return []
        if not call_name or not call_name.startswith("_") or call_name.startswith("__"):
            return []
        func = getattr(node, "func", None)
        if func and hasattr(func, "expr"):
            expr = getattr(func, "expr", None)
            if expr and getattr(expr, "name", None) in ("self", "cls"):
                return []
        return [
            Violation.from_node(
                code=self.code_private,
                message=f"Private method testing: {call_name}.",
                node=node,
                message_args=(call_name,),
            )
        ]

    def leave_functiondef(
        self,
        current_function: astroid.nodes.FunctionDef | None,
        mock_count: int,
    ) -> list[Violation]:
        """Call when leaving a test function. Returns W9101 violations if mock count > limit. Caller sets current_function=None after."""
        violations: list[Violation] = []
        if current_function and mock_count > _MOCK_LIMIT:
            violations.append(
                Violation.from_node(
                    code=self.code_mocks,
                    message=f"Fragile test: {mock_count} mocks (limit {_MOCK_LIMIT}).",
                    node=current_function,
                    message_args=(mock_count,),
                )
            )
        return violations
