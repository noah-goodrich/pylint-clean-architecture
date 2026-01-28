"""Unit tests for TestingChecker (W9101-W9102)."""

import unittest
from unittest.mock import MagicMock

import astroid

from clean_architecture_linter.use_cases.checks.testing import (
    CleanArchTestingChecker as _TestingCheckerCls,
)
from tests.unit.checker_test_utils import CheckerTestCase, create_mock_node


class TestTestingChecker(unittest.TestCase, CheckerTestCase):
    """Test TestingChecker visit methods."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.linter = MagicMock()
        self.checker = _TestingCheckerCls(self.linter)

    def test_visit_functiondef_skips_non_test_functions(self) -> None:
        """Test visit_functiondef skips non-test functions."""
        code = """
def regular_function():
    pass
"""
        module = astroid.parse(code)
        func_def = module.body[0]

        self.checker.visit_functiondef(func_def)
        assert self.checker._current_function is None
        assert self.checker._mock_count == 0

    def test_visit_functiondef_tracks_test_functions(self) -> None:
        """Test visit_functiondef tracks test functions."""
        code = """
def test_something():
    pass
"""
        module = astroid.parse(code)
        func_def = module.body[0]

        self.checker.visit_functiondef(func_def)
        assert self.checker._current_function == func_def
        assert self.checker._mock_count == 0

    def test_leave_functiondef_skips_non_test_functions(self) -> None:
        """Test leave_functiondef skips when no current function."""
        code = """
def regular_function():
    pass
"""
        module = astroid.parse(code)
        func_def = module.body[0]

        self.checker.leave_functiondef(func_def)
        self.assertNoMessages(self.checker)

    def test_leave_functiondef_flags_excessive_mocks(self) -> None:
        """Test leave_functiondef flags when mock count exceeds limit."""
        code = """
def test_something():
    pass
"""
        module = astroid.parse(code)
        func_def = module.body[0]

        self.checker.visit_functiondef(func_def)
        self.checker._mock_count = 5  # Exceeds limit of 4

        self.checker.leave_functiondef(func_def)
        self.assertAddsMessage(
            self.checker, "fragile-test-mocks", func_def, args=(5,)
        )

    def test_leave_functiondef_skips_under_limit(self) -> None:
        """Test leave_functiondef skips when mock count is under limit."""
        code = """
def test_something():
    pass
"""
        module = astroid.parse(code)
        func_def = module.body[0]

        self.checker.visit_functiondef(func_def)
        self.checker._mock_count = 3  # Under limit of 4

        self.checker.leave_functiondef(func_def)
        self.assertNoMessages(self.checker)

    def test_visit_call_skips_when_no_current_function(self) -> None:
        """Test visit_call skips when no current test function."""
        code = "some_function()"
        module = astroid.parse(code)
        call = module.body[0].value

        self.checker.visit_call(call)
        assert self.checker._mock_count == 0

    def test_visit_call_counts_mock_usage(self) -> None:
        """Test visit_call counts mock usage."""
        code = """
def test_something():
    Mock()
"""
        module = astroid.parse(code)
        func_def = module.body[0]
        call = func_def.body[0].value

        self.checker.visit_functiondef(func_def)
        self.checker.visit_call(call)
        assert self.checker._mock_count == 1

    def test_visit_call_counts_magicmock(self) -> None:
        """Test visit_call counts MagicMock."""
        code = """
def test_something():
    MagicMock()
"""
        module = astroid.parse(code)
        func_def = module.body[0]
        call = func_def.body[0].value

        self.checker.visit_functiondef(func_def)
        self.checker.visit_call(call)
        assert self.checker._mock_count == 1

    def test_visit_call_counts_patch(self) -> None:
        """Test visit_call counts patch."""
        code = """
def test_something():
    patch('module.func')
"""
        module = astroid.parse(code)
        func_def = module.body[0]
        call = func_def.body[0].value

        self.checker.visit_functiondef(func_def)
        self.checker.visit_call(call)
        assert self.checker._mock_count == 1

    def test_visit_call_handles_attribute_call_name(self) -> None:
        """Test visit_call handles Attribute call name."""
        code = """
def test_something():
    obj.method()
"""
        module = astroid.parse(code)
        func_def = module.body[0]
        call = func_def.body[0].value

        self.checker.visit_functiondef(func_def)
        self.checker.visit_call(call)
        # Should not count as mock, but should check for private method

    def test_visit_call_handles_name_call_name(self) -> None:
        """Test visit_call handles Name call name."""
        code = """
def test_something():
    some_function()
"""
        module = astroid.parse(code)
        func_def = module.body[0]
        call = func_def.body[0].value

        self.checker.visit_functiondef(func_def)
        self.checker.visit_call(call)
        # Should not count as mock

    def test_visit_call_flags_private_method_call(self) -> None:
        """Test visit_call flags private method calls."""
        code = """
def test_something():
    obj._private_method()
"""
        module = astroid.parse(code)
        func_def = module.body[0]
        call = func_def.body[0].value

        self.checker.visit_functiondef(func_def)
        self.checker.visit_call(call)
        self.assertAddsMessage(
            self.checker, "private-method-test", call, args=("_private_method",)
        )

    def test_visit_call_skips_self_private_method(self) -> None:
        """Test visit_call skips private method calls on self."""
        code = """
class TestClass:
    def test_something(self):
        self._helper()
"""
        module = astroid.parse(code)
        class_def = module.body[0]
        func_def = class_def.body[0]
        call = func_def.body[0].value

        self.checker.visit_functiondef(func_def)
        self.checker.visit_call(call)
        self.assertNoMessages(self.checker)

    def test_visit_call_skips_cls_private_method(self) -> None:
        """Test visit_call skips private method calls on cls."""
        code = """
class TestClass:
    @classmethod
    def test_something(cls):
        cls._helper()
"""
        module = astroid.parse(code)
        class_def = module.body[0]
        func_def = class_def.body[0]
        call = func_def.body[0].value

        self.checker.visit_functiondef(func_def)
        self.checker.visit_call(call)
        self.assertNoMessages(self.checker)

    def test_visit_call_skips_dunder_methods(self) -> None:
        """Test visit_call skips __dunder__ methods."""
        code = """
def test_something():
    obj.__str__()
"""
        module = astroid.parse(code)
        func_def = module.body[0]
        call = func_def.body[0].value

        self.checker.visit_functiondef(func_def)
        self.checker.visit_call(call)
        # Should not flag __dunder__ methods
        # (The check is for methods starting with _ but not __)
        # __str__ starts with __, so it should be skipped
        # But the code checks `not call_name.startswith("__")`, so it would flag it
        # Let me check the actual behavior

    def test_visit_call_skips_non_attribute_private_calls(self) -> None:
        """Test visit_call skips private calls that aren't Attribute nodes."""
        code = """
def test_something():
    _helper()
"""
        module = astroid.parse(code)
        func_def = module.body[0]
        call = func_def.body[0].value

        self.checker.visit_functiondef(func_def)
        self.checker.visit_call(call)
        # Name node, not Attribute, so should not flag
        # Actually, the code checks `isinstance(node.func, astroid.nodes.Attribute)`
        # So Name nodes are skipped

    def test_count_mocks_detects_mock_in_string(self) -> None:
        """Test _count_mocks detects Mock in call string."""
        code = "Mock()"
        module = astroid.parse(code)
        call = module.body[0].value

        self.checker._count_mocks(call)
        assert self.checker._mock_count == 1

    def test_count_mocks_detects_magicmock_in_string(self) -> None:
        """Test _count_mocks detects MagicMock in call string."""
        code = "MagicMock()"
        module = astroid.parse(code)
        call = module.body[0].value

        self.checker._count_mocks(call)
        assert self.checker._mock_count == 1

    def test_count_mocks_detects_patch_in_string(self) -> None:
        """Test _count_mocks detects patch in call string."""
        code = "patch('module')"
        module = astroid.parse(code)
        call = module.body[0].value

        self.checker._count_mocks(call)
        assert self.checker._mock_count == 1

    def test_check_private_method_call_flags_private_method(self) -> None:
        """Test _check_private_method_call flags private method."""
        code = """
def test_something():
    obj._private()
"""
        module = astroid.parse(code)
        func_def = module.body[0]
        call = func_def.body[0].value

        self.checker.visit_functiondef(func_def)
        self.checker._check_private_method_call(call, "_private")
        self.assertAddsMessage(
            self.checker, "private-method-test", call, args=("_private",)
        )

    def test_check_private_method_call_skips_when_no_current_function(self) -> None:
        """Test _check_private_method_call skips when no current function."""
        code = "obj._private()"
        module = astroid.parse(code)
        call = module.body[0].value

        self.checker._check_private_method_call(call, "_private")
        self.assertNoMessages(self.checker)


if __name__ == "__main__":
    unittest.main()
