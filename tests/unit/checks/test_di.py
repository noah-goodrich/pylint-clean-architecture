"""Unit tests for DIChecker (W9301)."""
import unittest
from unittest.mock import MagicMock

import astroid

from clean_architecture_linter.domain.config import ConfigurationLoader
from clean_architecture_linter.domain.layer_registry import LayerRegistry
from clean_architecture_linter.use_cases.checks.di import DIChecker
from tests.unit.checker_test_utils import CheckerTestCase, create_mock_node


class TestDIChecker(unittest.TestCase, CheckerTestCase):
    """Test DIChecker visit_call behavior."""

    def setUp(self) -> None:
        self.linter = MagicMock()
        self.ast_gateway = MagicMock()
        self.python_gateway = MagicMock()
        self.config_loader = ConfigurationLoader({}, {})
        self.checker = DIChecker(
            self.linter,
            ast_gateway=self.ast_gateway,
            python_gateway=self.python_gateway,
            config_loader=self.config_loader,
            registry={},
        )

    def test_visit_call_use_case_instantiates_gateway_adds_message(self) -> None:
        """UseCase layer instantiating *Gateway adds di-enforcement-violation."""
        self.python_gateway.get_node_layer.return_value = LayerRegistry.LAYER_USE_CASE
        self.ast_gateway.get_call_name.return_value = "FileSystemGateway"

        node = create_mock_node(astroid.nodes.Call)

        self.checker.visit_call(node)

        self.assertAddsMessage(
            self.checker,
            "W9301",
            node=node,
            args=("FileSystemGateway",),
        )

    def test_visit_call_domain_layer_no_message(self) -> None:
        """Domain layer call does not add message."""
        self.python_gateway.get_node_layer.return_value = LayerRegistry.LAYER_DOMAIN
        self.ast_gateway.get_call_name.return_value = "FileSystemGateway"

        node = create_mock_node(astroid.nodes.Call)

        self.checker.visit_call(node)

        self.checker.linter.add_message.assert_not_called()

    def test_visit_call_get_call_name_none_no_message(self) -> None:
        """When get_call_name returns None, no message."""
        self.python_gateway.get_node_layer.return_value = LayerRegistry.LAYER_USE_CASE
        self.ast_gateway.get_call_name.return_value = None

        node = create_mock_node(astroid.nodes.Call)

        self.checker.visit_call(node)

        self.checker.linter.add_message.assert_not_called()

    def test_visit_call_use_case_instantiates_repository_adds_message(self) -> None:
        """UseCase layer instantiating *Repository adds di-enforcement-violation."""
        self.python_gateway.get_node_layer.return_value = LayerRegistry.LAYER_USE_CASE
        self.ast_gateway.get_call_name.return_value = "UserRepository"
        node = create_mock_node(astroid.nodes.Call)
        self.checker.visit_call(node)
        self.assertAddsMessage(
            self.checker, "W9301", node=node, args=("UserRepository",)
        )

    def test_visit_call_use_case_instantiates_client_adds_message(self) -> None:
        """UseCase layer instantiating *Client adds di-enforcement-violation."""
        self.python_gateway.get_node_layer.return_value = LayerRegistry.LAYER_USE_CASE
        self.ast_gateway.get_call_name.return_value = "HttpClient"
        node = create_mock_node(astroid.nodes.Call)
        self.checker.visit_call(node)
        self.assertAddsMessage(
            self.checker, "W9301", node=node, args=("HttpClient",)
        )

    def test_visit_call_use_case_plain_class_no_message(self) -> None:
        """UseCase layer instantiating non-infrastructure class does not add message."""
        self.python_gateway.get_node_layer.return_value = LayerRegistry.LAYER_USE_CASE
        self.ast_gateway.get_call_name.return_value = "SomeService"
        node = create_mock_node(astroid.nodes.Call)
        self.checker.visit_call(node)
        self.checker.linter.add_message.assert_not_called()
