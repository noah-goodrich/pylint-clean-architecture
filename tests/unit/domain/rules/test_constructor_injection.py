"""Unit tests for ConstructorInjectionRule (W9034)."""

import unittest
from unittest.mock import MagicMock

import astroid

from excelsior_architect.domain.rules.constructor_injection import (
    ConstructorInjectionRule,
)


def _mock_init_method(annotations: list[tuple[str, str]]) -> MagicMock:
    """Create mock __init__ FunctionDef with annotations.
    
    Args:
        annotations: List of (arg_name, type_name) tuples
    """
    node = MagicMock(spec=astroid.nodes.FunctionDef)
    node.name = "__init__"
    
    args_node = MagicMock()
    args_list = []
    ann_list = []
    
    # Add self parameter
    self_arg = MagicMock()
    self_arg.name = "self"
    args_list.append(self_arg)
    ann_list.append(None)
    
    # Add annotated parameters
    for arg_name, type_name in annotations:
        arg = MagicMock()
        arg.name = arg_name
        args_list.append(arg)
        
        # Create annotation node
        ann = MagicMock(spec=astroid.nodes.Name)
        ann.name = type_name
        ann_list.append(ann)
    
    args_node.args = args_list
    args_node.annotations = ann_list
    node.args = args_node
    
    parent = MagicMock(spec=astroid.nodes.ClassDef)
    parent.name = "TestClass"
    node.parent = parent
    
    node.lineno = 1
    node.col_offset = 0
    mock_root = MagicMock()
    mock_root.file = "test.py"
    node.root.return_value = mock_root
    
    return node


class TestConstructorInjectionRule(unittest.TestCase):
    """Test ConstructorInjectionRule detection."""

    def setUp(self) -> None:
        self.rule = ConstructorInjectionRule()

    def test_check_returns_empty_for_non_function(self) -> None:
        """check() returns [] for non-FunctionDef nodes."""
        module = MagicMock(spec=astroid.nodes.Module)
        result = self.rule.check(module)
        self.assertEqual(result, [])

    def test_check_returns_empty_for_non_init(self) -> None:
        """check() returns [] for functions that aren't __init__."""
        node = MagicMock(spec=astroid.nodes.FunctionDef)
        node.name = "regular_method"
        result = self.rule.check(node)
        self.assertEqual(result, [])

    def test_check_returns_empty_for_non_class_parent(self) -> None:
        """check() returns [] when parent is not a ClassDef."""
        node = MagicMock(spec=astroid.nodes.FunctionDef)
        node.name = "__init__"
        node.parent = MagicMock(spec=astroid.nodes.Module)
        result = self.rule.check(node)
        self.assertEqual(result, [])

    def test_check_returns_empty_for_no_annotations(self) -> None:
        """check() returns [] when __init__ has no annotations."""
        node = MagicMock(spec=astroid.nodes.FunctionDef)
        node.name = "__init__"
        parent = MagicMock(spec=astroid.nodes.ClassDef)
        parent.name = "TestClass"
        node.parent = parent
        node.args = None
        result = self.rule.check(node)
        self.assertEqual(result, [])

    def test_check_detects_gateway_suffix(self) -> None:
        """check() detects parameters typed to concrete classes with Gateway suffix."""
        node = _mock_init_method([("db", "DatabaseGateway")])
        violations = self.rule.check(node)
        
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].code, "W9034")
        self.assertIn("db", violations[0].message)
        self.assertIn("DatabaseGateway", violations[0].message)
        self.assertIn("Protocol", violations[0].message)

    def test_check_detects_repository_suffix(self) -> None:
        """check() detects parameters typed to Repository."""
        node = _mock_init_method([("repo", "UserRepository")])
        violations = self.rule.check(node)
        
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].code, "W9034")
        self.assertIn("repo", violations[0].message)
        self.assertIn("UserRepository", violations[0].message)

    def test_check_detects_client_suffix(self) -> None:
        """check() detects parameters typed to Client."""
        node = _mock_init_method([("client", "APIClient")])
        violations = self.rule.check(node)
        
        self.assertEqual(len(violations), 1)
        self.assertIn("APIClient", violations[0].message)

    def test_check_detects_adapter_suffix(self) -> None:
        """check() detects parameters typed to Adapter."""
        node = _mock_init_method([("adapter", "ExternalAdapter")])
        violations = self.rule.check(node)
        
        self.assertEqual(len(violations), 1)
        self.assertIn("ExternalAdapter", violations[0].message)

    def test_check_detects_service_suffix(self) -> None:
        """check() detects parameters typed to Service."""
        node = _mock_init_method([("service", "EmailService")])
        violations = self.rule.check(node)
        
        self.assertEqual(len(violations), 1)
        self.assertIn("EmailService", violations[0].message)

    def test_check_detects_reporter_suffix(self) -> None:
        """check() detects parameters typed to Reporter."""
        node = _mock_init_method([("reporter", "ConsoleReporter")])
        violations = self.rule.check(node)
        
        self.assertEqual(len(violations), 1)
        self.assertIn("ConsoleReporter", violations[0].message)

    def test_check_detects_storage_suffix(self) -> None:
        """check() detects parameters typed to Storage."""
        node = _mock_init_method([("storage", "FileStorage")])
        violations = self.rule.check(node)
        
        self.assertEqual(len(violations), 1)
        self.assertIn("FileStorage", violations[0].message)

    def test_check_detects_checker_suffix(self) -> None:
        """check() detects parameters typed to Checker."""
        node = _mock_init_method([("checker", "RuleChecker")])
        violations = self.rule.check(node)
        
        self.assertEqual(len(violations), 1)
        self.assertIn("RuleChecker", violations[0].message)

    def test_check_detects_scaffolder_suffix(self) -> None:
        """check() detects parameters typed to Scaffolder."""
        node = _mock_init_method([("scaffolder", "ProjectScaffolder")])
        violations = self.rule.check(node)
        
        self.assertEqual(len(violations), 1)
        self.assertIn("ProjectScaffolder", violations[0].message)

    def test_check_detects_renderer_suffix(self) -> None:
        """check() detects parameters typed to Renderer."""
        node = _mock_init_method([("renderer", "HTMLRenderer")])
        violations = self.rule.check(node)
        
        self.assertEqual(len(violations), 1)
        self.assertIn("HTMLRenderer", violations[0].message)

    def test_check_allows_protocol_annotation(self) -> None:
        """check() allows parameters typed to Protocol."""
        node = _mock_init_method([("gateway", "DatabaseGatewayProtocol")])
        violations = self.rule.check(node)
        
        self.assertEqual(len(violations), 0)

    def test_check_allows_non_concrete_types(self) -> None:
        """check() allows parameters typed to non-concrete types."""
        node = _mock_init_method([
            ("name", "str"),
            ("count", "int"),
            ("config", "Dict"),
        ])
        violations = self.rule.check(node)
        
        self.assertEqual(len(violations), 0)

    def test_check_handles_multiple_violations(self) -> None:
        """check() detects multiple concrete type parameters."""
        node = _mock_init_method([
            ("gateway", "DatabaseGateway"),
            ("repo", "UserRepository"),
            ("client", "APIClient"),
        ])
        violations = self.rule.check(node)
        
        self.assertEqual(len(violations), 3)

    def test_check_skips_self_parameter(self) -> None:
        """check() skips self parameter."""
        node = _mock_init_method([])
        violations = self.rule.check(node)
        
        self.assertEqual(len(violations), 0)

    def test_check_skips_cls_parameter(self) -> None:
        """check() skips cls parameter."""
        node = _mock_init_method([])
        # Replace self with cls
        node.args.args[0].name = "cls"
        violations = self.rule.check(node)
        
        self.assertEqual(len(violations), 0)

    def test_annotation_to_name_handles_name_node(self) -> None:
        """_annotation_to_name() extracts name from Name node."""
        ann = MagicMock(spec=astroid.nodes.Name)
        ann.name = "SomeType"
        
        name = self.rule._annotation_to_name(ann)
        self.assertEqual(name, "SomeType")

    def test_annotation_to_name_handles_attribute_node(self) -> None:
        """_annotation_to_name() extracts name from Attribute node."""
        ann = MagicMock(spec=astroid.nodes.Attribute)
        ann.as_string = lambda: "module.SomeType"
        
        name = self.rule._annotation_to_name(ann)
        self.assertEqual(name, "module.SomeType")

    def test_annotation_to_name_handles_subscript_node(self) -> None:
        """_annotation_to_name() extracts name from Subscript node (e.g., List[SomeType])."""
        value_node = MagicMock(spec=astroid.nodes.Name)
        value_node.name = "List"
        
        ann = MagicMock(spec=astroid.nodes.Subscript)
        ann.value = value_node
        
        name = self.rule._annotation_to_name(ann)
        self.assertEqual(name, "List")

    def test_annotation_to_name_handles_unknown_node(self) -> None:
        """_annotation_to_name() returns empty string for unknown nodes."""
        ann = MagicMock(spec=astroid.nodes.Const)
        
        name = self.rule._annotation_to_name(ann)
        self.assertEqual(name, "")

    def test_is_protocol_annotation_detects_protocol_in_name(self) -> None:
        """_is_protocol_annotation() detects 'Protocol' in type name."""
        ann = MagicMock(spec=astroid.nodes.Name)
        ann.name = "SomeProtocol"
        
        result = self.rule._is_protocol_annotation(ann)
        self.assertTrue(result)

    def test_is_protocol_annotation_detects_protocol_suffix(self) -> None:
        """_is_protocol_annotation() detects types ending with 'Protocol'."""
        ann = MagicMock(spec=astroid.nodes.Name)
        ann.name = "DatabaseProtocol"
        
        result = self.rule._is_protocol_annotation(ann)
        self.assertTrue(result)

    def test_is_protocol_annotation_returns_false_for_non_protocol(self) -> None:
        """_is_protocol_annotation() returns False for non-Protocol types."""
        ann = MagicMock(spec=astroid.nodes.Name)
        ann.name = "DatabaseGateway"
        
        result = self.rule._is_protocol_annotation(ann)
        self.assertFalse(result)

    def test_check_handles_missing_annotation(self) -> None:
        """check() handles missing annotations gracefully."""
        node = MagicMock(spec=astroid.nodes.FunctionDef)
        node.name = "__init__"
        parent = MagicMock(spec=astroid.nodes.ClassDef)
        parent.name = "TestClass"
        node.parent = parent
        
        args_node = MagicMock()
        args_node.args = [MagicMock(), MagicMock()]  # self + one param
        args_node.annotations = [None, None]  # No annotations
        node.args = args_node
        
        violations = self.rule.check(node)
        self.assertEqual(len(violations), 0)

    def test_check_detects_qualified_name(self) -> None:
        """check() detects concrete classes with qualified names."""
        node = MagicMock(spec=astroid.nodes.FunctionDef)
        node.name = "__init__"
        parent = MagicMock(spec=astroid.nodes.ClassDef)
        parent.name = "TestClass"
        node.parent = parent
        
        args_node = MagicMock()
        self_arg = MagicMock()
        self_arg.name = "self"
        param_arg = MagicMock()
        param_arg.name = "gateway"
        args_node.args = [self_arg, param_arg]
        
        # Qualified name like "infra.gateways.DatabaseGateway"
        ann = MagicMock(spec=astroid.nodes.Attribute)
        ann.as_string = lambda: "infra.gateways.DatabaseGateway"
        args_node.annotations = [None, ann]
        node.args = args_node
        
        node.lineno = 1
        node.col_offset = 0
        mock_root = MagicMock()
        mock_root.file = "test.py"
        node.root.return_value = mock_root
        
        violations = self.rule.check(node)
        self.assertEqual(len(violations), 1)
        self.assertIn("DatabaseGateway", violations[0].message)
