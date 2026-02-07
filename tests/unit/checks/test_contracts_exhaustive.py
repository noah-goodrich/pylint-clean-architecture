import unittest
from unittest.mock import MagicMock

import astroid.nodes

from excelsior_architect.domain.config import ConfigurationLoader
from excelsior_architect.domain.layer_registry import LayerRegistry
from excelsior_architect.use_cases.checks.contracts import ContractChecker
from tests.unit.checker_test_utils import CheckerTestCase


class TestContractCheckerExhaustive(unittest.TestCase, CheckerTestCase):
    def setUp(self) -> None:
        self.linter = MagicMock()
        self.python_gateway = MagicMock()
        self.config_loader = ConfigurationLoader({}, {})
        self.checker = ContractChecker(
            self.linter,
            python_gateway=self.python_gateway,
            config_loader=self.config_loader,
            registry={},
        )

    def test_visit_classdef_infrastructure_missing_domain_base(self) -> None:
        """W9201: Infrastructure class must inherit from Domain Protocol."""
        node = create_strict_mock(astroid.nodes.ClassDef)
        node.name = "SqlUserRepo"
        node.bases = []  # No base class
        node.ancestors.return_value = []  # No ancestors

        # Mock layer resolution -> Infrastructure
        self.python_gateway.get_node_layer.return_value = LayerRegistry.LAYER_INFRASTRUCTURE
        self.python_gateway.is_exception_node.return_value = False

        self.checker.visit_classdef(node)
        self.assertAddsMessage(
            self.checker, "W9201", node=node, args=("SqlUserRepo",))

    def test_visit_classdef_infrastructure_has_domain_base_passes(self) -> None:
        """W9201: Passes if Domain base exists."""
        node = create_strict_mock(astroid.nodes.ClassDef)
        node.name = "SqlUserRepo"
        node.bases = [MagicMock()]  # Has base

        # Mock ancestors
        domain_proto = create_strict_mock(astroid.nodes.ClassDef)
        mock_root = MagicMock()
        mock_root.name = "domain.interfaces"  # Config loader will see "domain"
        domain_proto.root.return_value = mock_root

        node.ancestors.return_value = [domain_proto]

        self.python_gateway.get_node_layer.return_value = LayerRegistry.LAYER_INFRASTRUCTURE
        self.python_gateway.is_exception_node.return_value = False

        # Mock config loader manual layer check in loop
        self.checker.config_loader.get_layer_for_module = MagicMock(
            return_value=LayerRegistry.LAYER_DOMAIN)

        self.checker.visit_classdef(node)
        self.assertNoMessages(self.checker)

    def test_extra_methods_check(self) -> None:
        """W9201: Extra public methods not in protocol."""
        # Setup: Infra class with base
        node = create_strict_mock(astroid.nodes.ClassDef)
        node.name = "SqlUserRepo"
        node.bases = [MagicMock()]

        domain_proto = create_strict_mock(astroid.nodes.ClassDef)
        domain_proto.mymethods.return_value = [
            create_strict_mock(astroid.nodes.FunctionDef, name="save")]
        mock_root = MagicMock()
        mock_root.name = "domain.interfaces"
        domain_proto.root.return_value = mock_root

        node.ancestors.return_value = [domain_proto]

        self.python_gateway.get_node_layer.return_value = LayerRegistry.LAYER_INFRASTRUCTURE
        self.python_gateway.is_exception_node.return_value = False
        self.checker.config_loader.get_layer_for_module = MagicMock(
            return_value=LayerRegistry.LAYER_DOMAIN)

        # Node has 'save' (ok) and 'delete' (extra!)
        method_save = create_strict_mock(
            astroid.nodes.FunctionDef, name="save")
        method_delete = create_strict_mock(
            astroid.nodes.FunctionDef, name="delete")
        node.mymethods.return_value = [method_save, method_delete]

        self.checker.visit_classdef(node)
        self.assertAddsMessage(self.checker, "W9201",
                               node=method_delete, args=("SqlUserRepo",))

    def test_concrete_method_stub(self) -> None:
        """W9202: Concrete method stub detected (normal file)."""
        node = create_strict_mock(astroid.nodes.FunctionDef)
        node.name = "do_something"
        node.decorators = None
        node.is_generator.return_value = False
        node.parent = create_strict_mock(
            astroid.nodes.Module)  # Not a protocol parent
        # Normal source file (not a stub) so W9202 is reported
        node.root.return_value = MagicMock(file="src/foo/bar.py")

        # Body: pass
        node.body = [create_strict_mock(astroid.nodes.Pass)]

        self.checker.visit_functiondef(node)
        self.assertAddsMessage(
            self.checker, "W9202", node=node, args=("do_something",))

    def test_concrete_method_stub_skipped_for_pyi_file(self) -> None:
        """W9202: No message when file is a .pyi stub (by design stubs are empty)."""
        node = create_strict_mock(astroid.nodes.FunctionDef)
        node.name = "col_offset"
        node.decorators = None
        node.is_generator.return_value = False
        node.parent = create_strict_mock(astroid.nodes.ClassDef)
        node.root.return_value = MagicMock(
            file="src/excelsior_architect/stubs/astroid/nodes.pyi")
        node.body = [create_strict_mock(astroid.nodes.Pass)]

        self.python_gateway.is_protocol_node.return_value = False
        self.python_gateway.get_node_layer.return_value = LayerRegistry.LAYER_INFRASTRUCTURE

        self.checker.visit_functiondef(node)
        self.assertNoMessages(self.checker)

    def test_concrete_method_stub_skipped_for_stubs_directory(self) -> None:
        """W9202: No message when file path contains /stubs/ (stub directory)."""
        node = create_strict_mock(astroid.nodes.FunctionDef)
        node.name = "some_method"
        node.decorators = None
        node.is_generator.return_value = False
        node.parent = create_strict_mock(astroid.nodes.ClassDef)
        node.root.return_value = MagicMock(
            file="/project/stubs/third_party/some_lib.pyi")
        node.body = [create_strict_mock(astroid.nodes.Pass)]

        self.python_gateway.is_protocol_node.return_value = False
        self.python_gateway.get_node_layer.return_value = LayerRegistry.LAYER_INFRASTRUCTURE

        self.checker.visit_functiondef(node)
        self.assertNoMessages(self.checker)

    def test_concrete_method_stub_exemptions(self) -> None:
        """W9202: Exemptions (abstract, generator, protocol)."""
        # 1. Abstract
        node = create_strict_mock(astroid.nodes.FunctionDef)
        node.name = "abs_method"
        # Note: astroid.nodes.Decorators (with 's'), not Decorator
        decorators_node = create_strict_mock(astroid.nodes.Decorators)
        dec = MagicMock()
        dec.as_string.return_value = "@abstractmethod"
        decorators_node.nodes = [dec]
        node.decorators = decorators_node

        self.checker.visit_functiondef(node)
        self.assertNoMessages(self.checker)

        # 2. Generator
        node2 = create_strict_mock(astroid.nodes.FunctionDef)
        node2.name = "gen"
        node2.decorators = None
        node2.is_generator.return_value = True
        self.checker.visit_functiondef(node2)
        self.assertNoMessages(self.checker)


def create_strict_mock(spec_cls, **attrs) -> MagicMock:
    """Helper duplicate."""
    m = MagicMock(spec=spec_cls)
    for k, v in attrs.items():
        setattr(m, k, v)
    return m
