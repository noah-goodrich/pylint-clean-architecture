"""Unit tests for ExceptionHygieneRule (W9035)."""

import unittest
from unittest.mock import MagicMock

import astroid

from excelsior_architect.domain.rules.exception_hygiene import ExceptionHygieneRule


def _mock_except_handler(type_node=None, body=None) -> MagicMock:
    """Create a mock ExceptHandler node."""
    node = MagicMock(spec=astroid.nodes.ExceptHandler)
    node.type = type_node
    node.body = body or []
    node.lineno = 1
    node.col_offset = 0
    mock_root = MagicMock()
    mock_root.file = "test.py"
    node.root.return_value = mock_root
    return node


class TestExceptionHygieneRule(unittest.TestCase):
    """Test ExceptionHygieneRule detection."""

    def setUp(self) -> None:
        self.rule = ExceptionHygieneRule()

    def test_check_returns_empty_for_non_except_handler(self) -> None:
        """check() returns [] when node is not ExceptHandler."""
        module = MagicMock(spec=astroid.nodes.Module)
        result = self.rule.check(module)
        self.assertEqual(result, [])

    def test_check_detects_bare_except(self) -> None:
        """check() detects bare except: (type=None)."""
        node = _mock_except_handler(type_node=None, body=[MagicMock()])
        violations = self.rule.check(node)

        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].code, "W9035")
        self.assertIn("Bare 'except:'", violations[0].message)

    def test_check_detects_except_exception_without_reraise(self) -> None:
        """check() detects 'except Exception:' without re-raise."""
        type_node = MagicMock(spec=astroid.nodes.Name)
        type_node.name = "Exception"
        # Non-empty body without raise
        body_stmt = MagicMock(spec=astroid.nodes.Expr)
        body_stmt.body = []
        node = _mock_except_handler(type_node=type_node, body=[body_stmt])

        violations = self.rule.check(node)

        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].code, "W9035")
        self.assertIn("except Exception:", violations[0].message)
        self.assertIn("without re-raise", violations[0].message)

    def test_check_detects_except_base_exception_without_reraise(self) -> None:
        """check() detects 'except BaseException:' without re-raise."""
        type_node = MagicMock(spec=astroid.nodes.Name)
        type_node.name = "BaseException"
        body_stmt = MagicMock(spec=astroid.nodes.Expr)
        body_stmt.body = []
        node = _mock_except_handler(type_node=type_node, body=[body_stmt])

        violations = self.rule.check(node)

        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].code, "W9035")

    def test_check_detects_empty_except_body(self) -> None:
        """check() detects empty except body."""
        type_node = MagicMock(spec=astroid.nodes.Name)
        type_node.name = "ValueError"
        node = _mock_except_handler(type_node=type_node, body=[])

        violations = self.rule.check(node)

        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].code, "W9035")
        self.assertIn("Empty except body", violations[0].message)

    def test_check_detects_except_body_with_only_pass(self) -> None:
        """check() detects except body containing only pass statement."""
        type_node = MagicMock(spec=astroid.nodes.Name)
        type_node.name = "ValueError"
        pass_stmt = MagicMock(spec=astroid.nodes.Pass)
        node = _mock_except_handler(type_node=type_node, body=[pass_stmt])

        violations = self.rule.check(node)

        self.assertEqual(len(violations), 1)
        self.assertIn("Empty except body", violations[0].message)

    def test_check_allows_specific_exception_with_handling(self) -> None:
        """check() allows specific exception types with proper handling."""
        type_node = MagicMock(spec=astroid.nodes.Name)
        type_node.name = "ValueError"
        # Non-pass statement
        body_stmt = MagicMock(spec=astroid.nodes.Expr)
        body_stmt.body = []
        node = _mock_except_handler(type_node=type_node, body=[body_stmt])

        violations = self.rule.check(node)

        self.assertEqual(len(violations), 0)

    def test_check_allows_except_exception_with_reraise(self) -> None:
        """check() allows 'except Exception:' with re-raise statement."""
        type_node = MagicMock(spec=astroid.nodes.Name)
        type_node.name = "Exception"
        raise_stmt = MagicMock(spec=astroid.nodes.Raise)
        node = _mock_except_handler(type_node=type_node, body=[raise_stmt])

        violations = self.rule.check(node)

        self.assertEqual(len(violations), 0)

    def test_check_allows_except_exception_with_nested_reraise(self) -> None:
        """check() allows 'except Exception:' with nested re-raise in if block."""
        type_node = MagicMock(spec=astroid.nodes.Name)
        type_node.name = "Exception"
        # If statement containing raise
        raise_stmt = MagicMock(spec=astroid.nodes.Raise)
        if_stmt = MagicMock(spec=astroid.nodes.If)
        if_stmt.body = [raise_stmt]
        node = _mock_except_handler(type_node=type_node, body=[if_stmt])

        violations = self.rule.check(node)

        self.assertEqual(len(violations), 0)

    def test_check_handles_tuple_of_exceptions(self) -> None:
        """check() handles tuple of exception types."""
        # except (ValueError, TypeError): ...
        name1 = MagicMock(spec=astroid.nodes.Name)
        name1.name = "ValueError"
        name2 = MagicMock(spec=astroid.nodes.Name)
        name2.name = "Exception"
        tuple_node = MagicMock(spec=astroid.nodes.Tuple)
        tuple_node.elts = [name1, name2]

        body_stmt = MagicMock(spec=astroid.nodes.Expr)
        body_stmt.body = []
        node = _mock_except_handler(type_node=tuple_node, body=[body_stmt])

        violations = self.rule.check(node)

        # Should detect Exception in tuple without re-raise
        self.assertEqual(len(violations), 1)

    def test_check_handles_tuple_without_exception(self) -> None:
        """check() handles tuple of specific exceptions (no Exception/BaseException)."""
        name1 = MagicMock(spec=astroid.nodes.Name)
        name1.name = "ValueError"
        name2 = MagicMock(spec=astroid.nodes.Name)
        name2.name = "TypeError"
        tuple_node = MagicMock(spec=astroid.nodes.Tuple)
        tuple_node.elts = [name1, name2]

        body_stmt = MagicMock(spec=astroid.nodes.Expr)
        body_stmt.body = []
        node = _mock_except_handler(type_node=tuple_node, body=[body_stmt])

        violations = self.rule.check(node)

        # Should not flag - specific exceptions only
        self.assertEqual(len(violations), 0)

    def test_check_handles_non_name_type(self) -> None:
        """check() handles non-Name exception types gracefully."""
        type_node = MagicMock(spec=astroid.nodes.Attribute)
        # Not a Name node, should not match Exception/BaseException
        body_stmt = MagicMock(spec=astroid.nodes.Expr)
        body_stmt.body = []
        node = _mock_except_handler(type_node=type_node, body=[body_stmt])

        violations = self.rule.check(node)

        # Should not flag - can't determine if it's Exception
        self.assertEqual(len(violations), 0)

    def test_check_handles_body_with_multiple_statements(self) -> None:
        """check() checks for raise in body with multiple statements."""
        type_node = MagicMock(spec=astroid.nodes.Name)
        type_node.name = "Exception"
        stmt1 = MagicMock(spec=astroid.nodes.Expr)
        stmt1.body = []
        stmt2 = MagicMock(spec=astroid.nodes.Raise)  # Re-raise present
        node = _mock_except_handler(type_node=type_node, body=[stmt1, stmt2])

        violations = self.rule.check(node)

        # Should not flag - has re-raise
        self.assertEqual(len(violations), 0)

    def test_check_bare_except_returns_immediately(self) -> None:
        """check() returns immediately for bare except without checking body."""
        # Bare except with body - should only report bare except, not empty body
        node = _mock_except_handler(type_node=None, body=[MagicMock()])
        violations = self.rule.check(node)

        self.assertEqual(len(violations), 1)
        self.assertIn("Bare 'except:'", violations[0].message)

    def test_check_code_attribute(self) -> None:
        """Rule has correct code attribute."""
        self.assertEqual(self.rule.code, "W9035")

    def test_check_description_attribute(self) -> None:
        """Rule has description attribute."""
        self.assertIsInstance(self.rule.description, str)
        self.assertIn("Exception hygiene", self.rule.description)

    def test_check_fix_type_attribute(self) -> None:
        """Rule has fix_type attribute."""
        self.assertEqual(self.rule.fix_type, "code")

    def test_check_handles_except_with_no_body_attribute(self) -> None:
        """check() handles ExceptHandler with missing body attribute."""
        node = MagicMock(spec=astroid.nodes.ExceptHandler)
        node.type = None
        del node.body  # Remove body attribute
        node.lineno = 1
        node.col_offset = 0
        mock_root = MagicMock()
        mock_root.file = "test.py"
        node.root.return_value = mock_root

        # Use getattr with default in the actual implementation
        violations = self.rule.check(node)

        # Should still detect bare except
        self.assertEqual(len(violations), 1)

    def test_check_violation_includes_node_reference(self) -> None:
        """check() violations include reference to the original node."""
        node = _mock_except_handler(type_node=None, body=[])
        violations = self.rule.check(node)

        self.assertEqual(violations[0].node, node)

    def test_check_multiple_pass_statements(self) -> None:
        """check() treats multiple pass statements as empty body."""
        type_node = MagicMock(spec=astroid.nodes.Name)
        type_node.name = "ValueError"
        pass1 = MagicMock(spec=astroid.nodes.Pass)
        pass2 = MagicMock(spec=astroid.nodes.Pass)
        node = _mock_except_handler(type_node=type_node, body=[pass1, pass2])

        violations = self.rule.check(node)

        self.assertEqual(len(violations), 1)
        self.assertIn("Empty except body", violations[0].message)

    def test_check_deep_nested_reraise(self) -> None:
        """check() finds re-raise in deeply nested blocks."""
        type_node = MagicMock(spec=astroid.nodes.Name)
        type_node.name = "Exception"

        # Create nested structure: if -> try -> raise
        raise_stmt = MagicMock(spec=astroid.nodes.Raise)
        try_stmt = MagicMock(spec=astroid.nodes.Try)
        try_stmt.body = [raise_stmt]
        if_stmt = MagicMock(spec=astroid.nodes.If)
        if_stmt.body = [try_stmt]

        node = _mock_except_handler(type_node=type_node, body=[if_stmt])

        violations = self.rule.check(node)

        # Current implementation only checks one level deep
        # This test documents current behavior - may want to enhance
        # Does not find deeply nested raise
        self.assertEqual(len(violations), 1)
