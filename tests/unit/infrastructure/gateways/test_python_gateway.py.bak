import unittest
from unittest.mock import MagicMock

import astroid

from clean_architecture_linter.infrastructure.gateways.python_gateway import PythonGateway


class TestPythonGateway(unittest.TestCase):
    def setUp(self):
        self.gateway = PythonGateway()

    def test_is_stdlib_module(self):
        self.assertTrue(self.gateway.is_stdlib_module("os"))
        self.assertTrue(self.gateway.is_stdlib_module("typing"))
        # External packages should be False
        # But caution: if running in venv, detection depends on sys.stdlib_module_names
        # pandas is likely not installed in this env, but clean_architecture_linter IS.
        self.assertFalse(self.gateway.is_stdlib_module("clean_architecture_linter"))

    def test_is_external_dependency_heuristic(self):
        # file_path in .venv or site-packages -> True
        self.assertTrue(self.gateway.is_external_dependency("/usr/lib/python3.11/site-packages/libcst/__init__.py"))
        self.assertTrue(self.gateway.is_external_dependency(".venv/lib/requests/__init__.py"))

        # internal code -> False
        self.assertFalse(self.gateway.is_external_dependency("/development/project/src/main.py"))

    def test_get_node_layer_with_config(self):
        node = MagicMock()
        mock_root = MagicMock(spec=astroid.nodes.Module)
        mock_root.file = "/src/domain/entities.py"
        mock_root.name = "src.domain.entities"
        node.root.return_value = mock_root

        config = MagicMock()
        config.get_layer_for_module.return_value = "Domain"

        layer = self.gateway.get_node_layer(node, config)
        self.assertEqual(layer, "Domain")

    def test_get_node_layer_fallback(self):
        node = MagicMock()
        mock_root = MagicMock(spec=astroid.nodes.Module)
        mock_root.file = "/src/unknown.py"
        mock_root.name = "src.unknown"
        node.root.return_value = mock_root

        config = MagicMock()
        # Fallback in PythonGateway just returns config_loader.get_layer_for_module result
        # It DOES NOT call resolve_layer itself.
        # So we expect None if config returns None
        config.get_layer_for_module.return_value = None

        layer = self.gateway.get_node_layer(node, config)
        self.assertIsNone(layer)
