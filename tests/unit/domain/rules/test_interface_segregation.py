"""Unit tests for InterfaceSegregationRule (W9033)."""

import unittest
from unittest.mock import MagicMock

import astroid

from excelsior_architect.domain.rules.interface_segregation import (
    InterfaceSegregationRule,
)


def _mock_protocol_class(name: str, method_count: int) -> MagicMock:
    """Create mock Protocol ClassDef with specified number of methods."""
    node = MagicMock(spec=astroid.nodes.ClassDef)
    node.name = name
    
    # Mock Protocol base
    protocol_base = MagicMock(spec=astroid.nodes.Name)
    protocol_base.name = "Protocol"
    node.bases = [protocol_base]
    
    # Create method nodes
    body = []
    for i in range(method_count):
        method = MagicMock(spec=astroid.nodes.FunctionDef)
        method.name = f"method_{i}"
        body.append(method)
    
    node.body = body
    node.lineno = 1
    node.col_offset = 0
    mock_root = MagicMock()
    mock_root.file = "test.py"
    node.root.return_value = mock_root
    
    # Mock ancestors
    node.ancestors = lambda: []
    
    return node


class TestInterfaceSegregationRule(unittest.TestCase):
    """Test InterfaceSegregationRule detection."""

    def setUp(self) -> None:
        self.rule = InterfaceSegregationRule()

    def test_check_returns_empty_for_non_class(self) -> None:
        """check() returns [] for non-ClassDef nodes."""
        module = MagicMock(spec=astroid.nodes.Module)
        result = self.rule.check(module)
        self.assertEqual(result, [])

    def test_check_returns_empty_for_non_protocol(self) -> None:
        """check() returns [] for classes that are not Protocols."""
        node = MagicMock(spec=astroid.nodes.ClassDef)
        node.name = "RegularClass"
        node.bases = []
        node.ancestors = lambda: []
        result = self.rule.check(node)
        self.assertEqual(result, [])

    def test_check_returns_empty_for_small_protocol(self) -> None:
        """check() returns [] for Protocol with <= 7 methods."""
        node = _mock_protocol_class("SmallProtocol", 5)
        result = self.rule.check(node)
        self.assertEqual(result, [])

    def test_check_detects_large_protocol(self) -> None:
        """check() detects Protocol with > 7 methods."""
        node = _mock_protocol_class("LargeProtocol", 10)
        violations = self.rule.check(node)
        
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].code, "W9033")
        self.assertIn("LargeProtocol", violations[0].message)
        self.assertIn("10", violations[0].message)
        self.assertIn("splitting", violations[0].message)

    def test_check_respects_custom_limit(self) -> None:
        """check() respects custom method_limit."""
        rule = InterfaceSegregationRule(method_limit=5)
        node = _mock_protocol_class("MediumProtocol", 7)
        violations = rule.check(node)
        
        self.assertEqual(len(violations), 1)
        self.assertIn("7", violations[0].message)
        self.assertIn("5", violations[0].message)

    def test_check_allows_protocol_at_limit(self) -> None:
        """check() allows Protocol with exactly method_limit methods."""
        node = _mock_protocol_class("AtLimitProtocol", 7)
        result = self.rule.check(node)
        self.assertEqual(result, [])

    def test_is_protocol_detects_protocol_base_name(self) -> None:
        """_is_protocol() detects Protocol in bases via Name node."""
        node = MagicMock(spec=astroid.nodes.ClassDef)
        protocol_base = MagicMock(spec=astroid.nodes.Name)
        protocol_base.name = "Protocol"
        node.bases = [protocol_base]
        node.ancestors = lambda: []
        
        result = self.rule._is_protocol(node)
        self.assertTrue(result)

    def test_is_protocol_detects_protocol_base_attribute(self) -> None:
        """_is_protocol() detects Protocol in bases via Attribute node."""
        node = MagicMock(spec=astroid.nodes.ClassDef)
        protocol_base = MagicMock(spec=astroid.nodes.Attribute)
        protocol_base.attrname = "Protocol"
        node.bases = [protocol_base]
        node.ancestors = lambda: []
        
        result = self.rule._is_protocol(node)
        self.assertTrue(result)

    def test_is_protocol_detects_protocol_ancestor(self) -> None:
        """_is_protocol() detects Protocol in ancestors."""
        node = MagicMock(spec=astroid.nodes.ClassDef)
        node.bases = []
        
        ancestor = MagicMock()
        ancestor.name = "Protocol"
        ancestor.qname = lambda: "typing.Protocol"
        node.ancestors = lambda: [ancestor]
        
        result = self.rule._is_protocol(node)
        self.assertTrue(result)

    def test_is_protocol_handles_inference_error(self) -> None:
        """_is_protocol() handles InferenceError gracefully."""
        node = MagicMock(spec=astroid.nodes.ClassDef)
        node.bases = []
        node.ancestors = MagicMock(side_effect=astroid.InferenceError())
        
        result = self.rule._is_protocol(node)
        self.assertFalse(result)

    def test_is_protocol_returns_false_for_non_protocol(self) -> None:
        """_is_protocol() returns False for non-Protocol classes."""
        node = MagicMock(spec=astroid.nodes.ClassDef)
        base = MagicMock(spec=astroid.nodes.Name)
        base.name = "BaseClass"
        node.bases = [base]
        node.ancestors = lambda: []
        
        result = self.rule._is_protocol(node)
        self.assertFalse(result)

    def test_count_protocol_methods_excludes_dunder(self) -> None:
        """_count_protocol_methods() excludes dunder methods except special ones."""
        node = MagicMock(spec=astroid.nodes.ClassDef)
        
        regular_method = MagicMock(spec=astroid.nodes.FunctionDef)
        regular_method.name = "regular_method"
        
        dunder_method = MagicMock(spec=astroid.nodes.FunctionDef)
        dunder_method.name = "__str__"
        
        init_subclass = MagicMock(spec=astroid.nodes.FunctionDef)
        init_subclass.name = "__init_subclass__"
        
        node.body = [regular_method, dunder_method, init_subclass]
        
        count = self.rule._count_protocol_methods(node)
        # Should count: regular_method + __init_subclass__
        self.assertEqual(count, 2)

    def test_count_protocol_methods_includes_protocol_attrs(self) -> None:
        """_count_protocol_methods() includes __protocol_attrs__."""
        node = MagicMock(spec=astroid.nodes.ClassDef)
        
        protocol_attrs = MagicMock(spec=astroid.nodes.FunctionDef)
        protocol_attrs.name = "__protocol_attrs__"
        
        node.body = [protocol_attrs]
        
        count = self.rule._count_protocol_methods(node)
        self.assertEqual(count, 1)

    def test_count_protocol_methods_handles_empty_body(self) -> None:
        """_count_protocol_methods() handles empty body."""
        node = MagicMock(spec=astroid.nodes.ClassDef)
        node.body = []
        
        count = self.rule._count_protocol_methods(node)
        self.assertEqual(count, 0)

    def test_count_protocol_methods_handles_no_body_attribute(self) -> None:
        """_count_protocol_methods() handles missing body attribute."""
        node = MagicMock(spec=astroid.nodes.ClassDef)
        del node.body
        
        count = self.rule._count_protocol_methods(node)
        self.assertEqual(count, 0)

    def test_count_protocol_methods_ignores_non_functions(self) -> None:
        """_count_protocol_methods() ignores non-FunctionDef nodes in body."""
        node = MagicMock(spec=astroid.nodes.ClassDef)
        
        method = MagicMock(spec=astroid.nodes.FunctionDef)
        method.name = "method"
        
        attr = MagicMock(spec=astroid.nodes.Assign)
        
        node.body = [method, attr]
        
        count = self.rule._count_protocol_methods(node)
        self.assertEqual(count, 1)

    def test_check_handles_node_without_bases(self) -> None:
        """check() handles nodes without bases attribute."""
        node = MagicMock()
        delattr(node, "bases")
        
        result = self.rule.check(node)
        self.assertEqual(result, [])

    def test_check_handles_node_without_name(self) -> None:
        """check() handles nodes without name attribute."""
        node = MagicMock()
        node.bases = []
        delattr(node, "name")
        
        result = self.rule.check(node)
        self.assertEqual(result, [])

    def test_default_method_limit(self) -> None:
        """Rule uses default method limit of 7."""
        rule = InterfaceSegregationRule()
        self.assertEqual(rule._method_limit, 7)

    def test_custom_method_limit(self) -> None:
        """Rule uses custom method limit when provided."""
        rule = InterfaceSegregationRule(method_limit=10)
        self.assertEqual(rule._method_limit, 10)

    def test_is_protocol_via_qname(self) -> None:
        """_is_protocol() detects Protocol via qname containing 'Protocol'."""
        node = MagicMock(spec=astroid.nodes.ClassDef)
        node.bases = []
        
        ancestor = MagicMock()
        ancestor.name = "SomeBase"
        ancestor.qname = lambda: "typing_extensions.Protocol"
        node.ancestors = lambda: [ancestor]
        
        result = self.rule._is_protocol(node)
        self.assertTrue(result)
