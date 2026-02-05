import unittest
from unittest.mock import MagicMock, PropertyMock

import astroid.nodes

from clean_architecture_linter.domain.config import ConfigurationLoader
from clean_architecture_linter.domain.layer_registry import LayerRegistry
from clean_architecture_linter.use_cases.checks.dependencies import DependencyChecker
from tests.unit.checker_test_utils import CheckerTestCase, create_mock_node


class TestDependencyChecker(unittest.TestCase, CheckerTestCase):
    def setUp(self) -> None:
        self.linter = MagicMock()
        self.python_gateway = MagicMock()
        self.config_loader = ConfigurationLoader({}, {})
        self.checker = DependencyChecker(
            self.linter, self.python_gateway, self.config_loader, registry={}
        )

    def test_illegal_dependency_domain_imports_infra(self) -> None:
        # Setup: Domain -> Infrastructure (BANNED)
        self.python_gateway.get_node_layer.return_value = LayerRegistry.LAYER_DOMAIN

        # We need config_loader.resolve_layer to return Infrastructure for the imported module
        # But Checker uses config_loader which is instantiated inside __init__.
        # We need to mock the checker.config_loader
        self.checker.config_loader.resolve_layer = MagicMock(return_value=None)
        self.checker.config_loader.get_layer_for_module = MagicMock(
            return_value=LayerRegistry.LAYER_INFRASTRUCTURE)

        # Mock the read-only property using PropertyMock
        type(self.checker.config_loader).shared_kernel_modules = PropertyMock(
            return_value=[])

        node = create_mock_node(astroid.nodes.Import)
        node.names = [("requests", None)]

        self.checker.visit_import(node)

        self.assertAddsMessage(
            self.checker,
            "W9001",
            node,
            args=(LayerRegistry.LAYER_INFRASTRUCTURE,
                  LayerRegistry.LAYER_DOMAIN)
        )

    def test_legal_dependency_usecase_imports_domain(self) -> None:
        # Setup: UseCase -> Domain (ALLOWED)
        self.python_gateway.get_node_layer.return_value = LayerRegistry.LAYER_USE_CASE
        self.checker.config_loader.resolve_layer = MagicMock(return_value=None)
        self.checker.config_loader.get_layer_for_module = MagicMock(
            return_value=LayerRegistry.LAYER_DOMAIN)

        node = create_mock_node(astroid.nodes.Import)
        node.names = [("domain.models", None)]

        self.checker.visit_import(node)
        self.assertNoMessages(self.checker)

    def test_interface_imports_infrastructure_flagged(self) -> None:
        """Interface -> Infrastructure (e.g. cli importing adapters) must be flagged (W9001).
        Mirrors the violation we should catch in cli.py."""
        self.python_gateway.get_node_layer.return_value = LayerRegistry.LAYER_INTERFACE
        self.checker.config_loader.resolve_layer = MagicMock(return_value=None)
        self.checker.config_loader.get_layer_for_module = MagicMock(
            return_value=LayerRegistry.LAYER_INFRASTRUCTURE
        )
        type(self.checker.config_loader).shared_kernel_modules = PropertyMock(
            return_value=set())

        node = create_mock_node(astroid.nodes.ImportFrom)
        node.modname = "clean_architecture_linter.infrastructure.adapters.linter_adapters"

        self.checker.visit_importfrom(node)

        self.assertAddsMessage(
            self.checker,
            "W9001",
            node,
            args=(LayerRegistry.LAYER_INFRASTRUCTURE,
                  LayerRegistry.LAYER_INTERFACE),
        )
