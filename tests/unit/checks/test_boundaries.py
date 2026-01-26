import unittest
from unittest.mock import MagicMock

import astroid.nodes

from clean_architecture_linter.use_cases.checks.boundaries import ResourceChecker, VisibilityChecker
from tests.unit.checker_test_utils import CheckerTestCase, create_mock_node


class TestBoundaries(unittest.TestCase, CheckerTestCase):
    def setUp(self) -> None:
        self.linter = MagicMock()
        self.python_gateway = MagicMock()

    def test_visibility_protected_access(self) -> None:
        checker = VisibilityChecker(self.linter)
        # visibility_enforcement defaults to True in config, no need to set

        node = create_mock_node(
            astroid.nodes.Attribute,
            attrname="_internal",
            expr=create_mock_node(astroid.nodes.Name, name="obj")
        )

        checker.visit_attribute(node)
        self.assertAddsMessage(checker, "clean-arch-visibility", node, args=("_internal",))

    def test_resource_access_forbidden(self) -> None:
        checker = ResourceChecker(self.linter, self.python_gateway)

        # Configure layer to be Domain
        self.python_gateway.get_node_layer.return_value = "Domain"

        node = create_mock_node(astroid.nodes.Import)
        node.names = [("requests", None)]

        checker.visit_import(node)

        # requests is forbidden in Domain
        self.assertAddsMessage(checker, "clean-arch-resources", node, args=("import requests", "Domain"))

    def test_resource_access_allowed_stdlib(self) -> None:
        checker = ResourceChecker(self.linter, self.python_gateway)
        self.python_gateway.get_node_layer.return_value = "Domain"

        node = create_mock_node(astroid.nodes.Import)
        node.names = [("typing", None)]

        checker.visit_import(node)
        self.assertNoMessages(checker)
