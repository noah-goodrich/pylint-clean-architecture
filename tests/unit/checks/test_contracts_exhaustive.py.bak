import unittest
from unittest.mock import MagicMock

import astroid.nodes

from clean_architecture_linter.checks.contracts import ContractChecker
from clean_architecture_linter.layer_registry import LayerRegistry
from tests.unit.checker_test_utils import CheckerTestCase


class TestContractCheckerExhaustive(unittest.TestCase, CheckerTestCase):
    def setUp(self):
        self.linter = MagicMock()
        self.python_gateway = MagicMock()
        self.checker = ContractChecker(self.linter, python_gateway=self.python_gateway)
        self.checker.open() # Load config

    def test_visit_classdef_infrastructure_missing_domain_base(self):
        """W9201: Infrastructure class must inherit from Domain Protocol."""
        node = create_strict_mock(astroid.nodes.ClassDef)
        node.name = "SqlUserRepo"
        node.bases = [] # No base class
        node.ancestors.return_value = [] # No ancestors

        # Mock layer resolution -> Infrastructure
        self.python_gateway.get_node_layer.return_value = LayerRegistry.LAYER_INFRASTRUCTURE
        self.python_gateway.is_exception_node.return_value = False

        self.checker.visit_classdef(node)
        self.assertAddsMessage(self.checker, "contract-integrity-violation", node=node, args=("SqlUserRepo",))

    def test_visit_classdef_infrastructure_has_domain_base_passes(self):
        """W9201: Passes if Domain base exists."""
        node = create_strict_mock(astroid.nodes.ClassDef)
        node.name = "SqlUserRepo"
        node.bases = [MagicMock()] # Has base

        # Mock ancestors
        domain_proto = create_strict_mock(astroid.nodes.ClassDef)
        mock_root = MagicMock()
        mock_root.name = "domain.interfaces" # Config loader will see "domain"
        domain_proto.root.return_value = mock_root

        node.ancestors.return_value = [domain_proto]

        self.python_gateway.get_node_layer.return_value = LayerRegistry.LAYER_INFRASTRUCTURE
        self.python_gateway.is_exception_node.return_value = False

        # Mock config loader manual layer check in loop
        self.checker.config_loader.get_layer_for_module = MagicMock(return_value=LayerRegistry.LAYER_DOMAIN)

        self.checker.visit_classdef(node)
        self.assertNoMessages(self.checker)

    def test_extra_methods_check(self):
        """W9201: Extra public methods not in protocol."""
        # Setup: Infra class with base
        node = create_strict_mock(astroid.nodes.ClassDef)
        node.name = "SqlUserRepo"
        node.bases = [MagicMock()]

        domain_proto = create_strict_mock(astroid.nodes.ClassDef)
        domain_proto.methods.return_value = [create_strict_mock(astroid.nodes.FunctionDef, name="save")]
        mock_root = MagicMock()
        mock_root.name = "domain.interfaces"
        domain_proto.root.return_value = mock_root

        node.ancestors.return_value = [domain_proto]

        self.python_gateway.get_node_layer.return_value = LayerRegistry.LAYER_INFRASTRUCTURE
        self.python_gateway.is_exception_node.return_value = False
        self.checker.config_loader.get_layer_for_module = MagicMock(return_value=LayerRegistry.LAYER_DOMAIN)

        # Node has 'save' (ok) and 'delete' (extra!)
        method_save = create_strict_mock(astroid.nodes.FunctionDef, name="save")
        method_delete = create_strict_mock(astroid.nodes.FunctionDef, name="delete")
        node.methods.return_value = [method_save, method_delete]

        self.checker.visit_classdef(node)
        self.assertAddsMessage(self.checker, "contract-integrity-violation", node=method_delete, args=("SqlUserRepo",))

    def test_concrete_method_stub(self):
        """W9202: Concrete method stub detected."""
        node = create_strict_mock(astroid.nodes.FunctionDef)
        node.name = "do_something"
        node.decorators = None
        node.is_generator.return_value = False
        node.parent = create_strict_mock(astroid.nodes.Module) # Not a protocol parent

        # Body: pass
        node.body = [create_strict_mock(astroid.nodes.Pass)]

        self.checker.visit_functiondef(node)
        self.assertAddsMessage(self.checker, "concrete-method-stub", node=node, args=("do_something",))

    def test_concrete_method_stub_exemptions(self):
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

def create_strict_mock(spec_cls, **attrs):
    """Helper duplicate."""
    m = MagicMock(spec=spec_cls)
    for k, v in attrs.items():
        setattr(m, k, v)
    return m
