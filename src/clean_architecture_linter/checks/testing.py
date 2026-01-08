"""Test coupling checks (W9101-W9103)."""

# AST checks often violate Demeter by design
import astroid  # type: ignore[import-untyped]
from pylint.checkers import BaseChecker


class TestingChecker(BaseChecker):
    """Enforce loose test coupling following Uncle Bob's TDD principles."""

    name = "clean-arch-testing"
    msgs = {
        "W9101": (
            "Fragile Test: %d mocks exceed limit of 4. Inject single Protocol instead. Clean Fix: Use a single Fake "
            "or Stub implementation of a Protocol rather than mocking many individual methods.",
            "fragile-test-mocks",
            "Tests with many mocks are tightly coupled to implementation.",
        ),
        "W9102": (
            "Testing private method: %s. Test the execute() behavior instead. Clean Fix: Test the public API method "
            "that calls this private method.",
            "private-method-test",
            "Tests should verify behavior, not implementation details.",
        ),
    }

    def __init__(self, linter=None):
        super().__init__(linter)
        self._mock_count = 0
        self._current_function = None

    def visit_functiondef(self, node):
        """Track function entry and reset mock count."""
        # Only check test functions
        if not node.name.startswith("test_"):
            return

        self._current_function = node
        self._mock_count = 0

    def leave_functiondef(self, _):
        """Check mock count when leaving test function."""
        if self._current_function and self._current_function.name.startswith("test_"):
            if self._mock_count > 4:
                self.add_message(
                    "fragile-test-mocks",
                    node=self._current_function,
                    args=(self._mock_count,),
                )
        self._current_function = None
        self._mock_count = 0

    def visit_call(self, node):
        """Detect mock.patch calls and private method calls."""
        call_name = self._get_full_call_name(node)
        if not call_name:
            return

        self._check_mock_usage(node, call_name)
        self._check_private_method_call(node, call_name)

    def _check_mock_usage(self, _, call_name):
        """W9101: Check mock usage."""
        if "patch" in call_name or "Mock" in call_name:
            self._mock_count += 1

    def _check_private_method_call(self, node, call_name):
        """W9102: Detect private method calls on SUT."""
        if not self._current_function:
            return

        if call_name.startswith("_") and not call_name.startswith("__"):
            # Check if this is a method call (has receiver)
            if isinstance(node.func, astroid.nodes.Attribute):
                self.add_message("private-method-test", node=node, args=(call_name,))

    def _get_full_call_name(self, node):
        """Get the full name of a call."""
        if hasattr(node.func, "attrname"):
            return node.func.attrname
        if hasattr(node.func, "name"):
            return node.func.name
        return None
