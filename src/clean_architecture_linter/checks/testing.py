"""Test coupling checks (W9101-W9103)."""

# AST checks often violate Demeter by design

from typing import TYPE_CHECKING, Optional

import astroid  # type: ignore[import-untyped]

if TYPE_CHECKING:
    from pylint.lint import PyLinter
from pylint.checkers import BaseChecker

_MOCK_LIMIT: int = 4


class TestingChecker(BaseChecker):
    """Enforce loose test coupling following Uncle Bob's TDD principles."""

    name: str = "clean-arch-testing"

    def __init__(self, linter: "PyLinter") -> None:
        self.msgs = {
            "W9101": (
                "Fragile Test: %d mocks exceed limit of 4. Inject single Protocol instead. "
                "Clean Fix: Use a single Fake or Stub implementation of a Protocol rather than "
                "mocking many individual methods.",
                "fragile-test-mocks",
                "Tests with many mocks are tightly coupled to implementation.",
            ),
            "W9102": (
                "Testing private method: %s. Test the execute() behavior instead. "
                "Clean Fix: Test the public API method that calls this private method.",
                "private-method-test",
                "Tests should verify behavior, not implementation details.",
            ),
        }
        super().__init__(linter)
        self._mock_count: int = 0
        self._current_function: Optional[astroid.nodes.FunctionDef] = None

    def visit_functiondef(self, node: astroid.nodes.FunctionDef) -> None:
        """Track function entry and reset mock count."""
        # Only check test functions
        if not node.name.startswith("test_"):
            return

        self._current_function = node
        self._mock_count = 0

    def leave_functiondef(self, _: astroid.nodes.FunctionDef) -> None:
        """Check mock count when leaving test function."""
        if not self._current_function:
            return

        if self._mock_count > _MOCK_LIMIT:
            self.add_message(
                "fragile-test-mocks",
                node=self._current_function,
                args=(self._mock_count,),
            )

        self._current_function = None

    def visit_call(self, node: astroid.nodes.Call) -> None:
        """Identity mock usage and private method tests."""
        if not self._current_function:
            return

        # 1. Count mocks
        self._count_mocks(node)

        # 2. Check for private method testing
        call_name: str = ""
        if isinstance(node.func, astroid.nodes.Attribute):
            call_name = node.func.attrname
        elif isinstance(node.func, astroid.nodes.Name):
            call_name = node.func.name

        if call_name:
            self._check_private_method_call(node, call_name)

    def _count_mocks(self, node: astroid.nodes.Call) -> None:
        """Check if call is a mock instantiation or usage."""
        call_str = node.as_string()
        if "Mock(" in call_str or "MagicMock(" in call_str or "patch(" in call_str:
            self._mock_count += 1

    def _check_private_method_call(self, node: astroid.nodes.Call, call_name: str) -> None:
        """W9102: Detect private method calls on SUT."""
        if not self._current_function:
            return

        if (
            call_name.startswith("_")
            and not call_name.startswith("__")
            and isinstance(node.func, astroid.nodes.Attribute)
        ):
            # Exempt calls on 'self' or 'cls' within the same test class
            if isinstance(node.func.expr, astroid.nodes.Name) and node.func.expr.name in ("self", "cls"):
                return

            # Check if this is a method call (has receiver)
            self.add_message("private-method-test", node=node, args=(call_name,))
