"""Test coupling checks (W9101-W9103)."""

# AST checks often violate Demeter by design
# pylint: disable=law-of-demeter-violation
import astroid  # type: ignore[import-untyped]
from pylint.checkers import BaseChecker


class TestingChecker(BaseChecker):
    """Enforce loose test coupling following Uncle Bob's TDD principles."""

    name = "clean-arch-testing"
    msgs = {
        "W9101": (
            "Fragile Test: %d mocks exceed limit of 4. Inject single Protocol instead.",
            "fragile-test-mocks",
            "Tests with many mocks are tightly coupled to implementation.",
        ),
        "W9102": (
            "Testing private method: %s. Test the execute() behavior instead.",
            "private-method-test",
            "Tests should verify behavior, not implementation details.",
        ),
        "W9103": (
            "Leaky Mock: Patching %s directly. Mock the Protocol instead.",
            "leaky-library-mock",
            "Mock at the boundary (Repository), not inside the unit.",
        ),
    }

    # Libraries that should never be mocked directly in UseCase tests
    DEFAULT_FORBIDDEN_MOCKS = [
        "requests.",
        "sqlalchemy.",
        "os.path",
        "os.environ",
    ]

    def __init__(self, linter=None):
        super().__init__(linter)
        self._mock_count = 0
        self._current_function = None
        # Lazy load configuration if needed, or we rely on explicit config injection later
        # For now, we will rely on defaults + potential future config hook

    def visit_functiondef(self, node):
        """Track function entry and reset mock count."""
        # Only check test functions
        if not node.name.startswith("test_"):
            return

        self._current_function = node
        self._mock_count = 0

    def leave_functiondef(self, node):
        """Check mock count when leaving test function."""
        if node.name.startswith("test_") and self._mock_count > 4:
            self.add_message("fragile-test-mocks", node=node, args=(self._mock_count,))
        self._current_function = None
        self._mock_count = 0

    def visit_call(self, node):
        """Detect mock.patch calls and private method calls."""
        call_name = self._get_full_call_name(node)
        if not call_name:
            return

        self._check_mock_usage(node, call_name)
        self._check_private_method_call(node, call_name)

    def _check_mock_usage(self, node, call_name):
        """W9101 & W9103: Check mock usage and forbidden patterns."""
        if "patch" in call_name or "Mock" in call_name:
            self._mock_count += 1
            self._check_forbidden_mocks(node)

    def _check_forbidden_mocks(self, node):
        """W9103: Check arguments for forbidden mock patterns."""
        if not node.args:
            return

        for arg in node.args:
            if not (isinstance(arg, astroid.nodes.Const) and isinstance(arg.value, str)):
                continue

            # Check against forbidden patterns
            if any(arg.value.startswith(p) for p in self.DEFAULT_FORBIDDEN_MOCKS):
                self.add_message("leaky-library-mock", node=node, args=(arg.value,))
                break

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
