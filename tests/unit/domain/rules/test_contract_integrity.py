"""Unit tests for ContractIntegrityRule (W9201)."""

import unittest
from unittest.mock import MagicMock

import astroid.nodes

from excelsior_architect.domain.layer_registry import LayerRegistry
from excelsior_architect.domain.rules.contract_integrity import ContractIntegrityRule


def _mock_class_def(name: str, bases: list | None = None) -> MagicMock:
    node = MagicMock(spec=astroid.nodes.ClassDef)
    node.name = name
    node.bases = bases or []
    node.ancestors.return_value = []
    node.root.return_value = MagicMock(file="")
    node.lineno = 1
    node.col_offset = 0
    return node


class TestContractIntegrityRuleCheck(unittest.TestCase):
    """Test ContractIntegrityRule.check() detection."""

    def setUp(self) -> None:
        self.python_gateway = MagicMock()
        self.config_loader = MagicMock()
        self.rule = ContractIntegrityRule(
            python_gateway=self.python_gateway,
            config_loader=self.config_loader,
        )

    def test_check_returns_empty_for_non_classdef(self) -> None:
        """check() returns [] when node is not ClassDef."""
        module = MagicMock(spec=astroid.nodes.Module)
        result = self.rule.check(module)
        self.assertEqual(result, [])

    def test_check_returns_empty_for_non_infrastructure_layer(self) -> None:
        """check() returns [] when class is not in infrastructure layer."""
        node = _mock_class_def("SomeClass", [MagicMock()])
        self.python_gateway.get_node_layer.return_value = LayerRegistry.LAYER_DOMAIN
        result = self.rule.check(node)
        self.assertEqual(result, [])

    def test_check_returns_violation_when_no_bases(self) -> None:
        """check() returns one W9201 violation when infrastructure class has no bases."""
        node = _mock_class_def("SqlUserRepo", [])
        self.python_gateway.get_node_layer.return_value = LayerRegistry.LAYER_INFRASTRUCTURE
        self.python_gateway.is_exception_node.return_value = False

        result = self.rule.check(node)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].code, "W9201")
        self.assertEqual(result[0].message_args, ("SqlUserRepo",))
        self.assertEqual(result[0].node, node)

    def test_check_returns_violation_when_no_domain_base(self) -> None:
        """check() returns one W9201 violation when infrastructure class has no domain base."""
        node = _mock_class_def("SqlUserRepo", [MagicMock()])
        node.ancestors.return_value = []
        self.python_gateway.get_node_layer.return_value = LayerRegistry.LAYER_INFRASTRUCTURE
        self.python_gateway.is_exception_node.return_value = False

        result = self.rule.check(node)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].code, "W9201")
        self.assertEqual(result[0].message_args, ("SqlUserRepo",))

    def test_check_returns_violations_for_extra_methods(self) -> None:
        """check() returns W9201 violations for public methods not in protocol."""
        node = _mock_class_def("SqlUserRepo", [MagicMock()])
        domain_proto = MagicMock(spec=astroid.nodes.ClassDef)
        proto_save = MagicMock(spec=astroid.nodes.FunctionDef)
        proto_save.name = "save"
        domain_proto.mymethods.return_value = [proto_save]
        mock_root = MagicMock()
        mock_root.name = "domain.interfaces"
        domain_proto.root.return_value = mock_root
        node.ancestors.return_value = [domain_proto]
        self.config_loader.get_layer_for_module.return_value = LayerRegistry.LAYER_DOMAIN
        self.python_gateway.get_node_layer.return_value = LayerRegistry.LAYER_INFRASTRUCTURE
        self.python_gateway.is_exception_node.return_value = False

        method_save = MagicMock(spec=astroid.nodes.FunctionDef)
        method_save.name = "save"
        method_save.lineno = 5
        method_save.col_offset = 4
        method_save.root.return_value = MagicMock(file="")
        method_delete = MagicMock(spec=astroid.nodes.FunctionDef)
        method_delete.name = "delete"
        method_delete.lineno = 8
        method_delete.col_offset = 4
        method_delete.root.return_value = MagicMock(file="")
        node.mymethods.return_value = [method_save, method_delete]

        result = self.rule.check(node)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].code, "W9201")
        self.assertEqual(result[0].message_args, ("SqlUserRepo",))
        self.assertEqual(result[0].node, method_delete)
