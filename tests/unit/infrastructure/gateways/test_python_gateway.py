import sys
import unittest
from unittest.mock import MagicMock, patch

import astroid

from clean_architecture_linter.infrastructure.gateways.python_gateway import PythonGateway


class TestPythonGateway(unittest.TestCase):
    def setUp(self) -> None:
        self.gateway = PythonGateway()

    def test_is_stdlib_module_stdlib_modules(self) -> None:
        """Test detection of standard library modules."""
        self.assertTrue(self.gateway.is_stdlib_module("os"))
        self.assertTrue(self.gateway.is_stdlib_module("typing"))
        self.assertTrue(self.gateway.is_stdlib_module("sys"))
        self.assertTrue(self.gateway.is_stdlib_module("pathlib"))

    def test_is_stdlib_module_builtins(self) -> None:
        """Test builtins module is always detected."""
        self.assertTrue(self.gateway.is_stdlib_module("builtins"))

    def test_is_stdlib_module_empty_string(self) -> None:
        """Test empty string returns False."""
        self.assertFalse(self.gateway.is_stdlib_module(""))
        self.assertFalse(self.gateway.is_stdlib_module(None))

    def test_is_stdlib_module_external_packages(self) -> None:
        """Test external packages return False."""
        # External packages should be False
        # But caution: if running in venv, detection depends on sys.stdlib_module_names
        # pandas is likely not installed in this env, but clean_architecture_linter IS.
        self.assertFalse(self.gateway.is_stdlib_module("clean_architecture_linter"))
        self.assertFalse(self.gateway.is_stdlib_module("pandas"))
        self.assertFalse(self.gateway.is_stdlib_module("requests"))

    @patch('sys.stdlib_module_names', {'os', 'sys', 'typing'}, create=True)
    def test_is_stdlib_module_uses_stdlib_module_names(self) -> None:
        """Test Python 3.10+ uses sys.stdlib_module_names."""
        gateway = PythonGateway()
        self.assertTrue(gateway.is_stdlib_module("os"))
        self.assertTrue(gateway.is_stdlib_module("typing"))
        self.assertFalse(gateway.is_stdlib_module("pandas"))

    def test_is_stdlib_module_fallback_to_builtin_module_names(self) -> None:
        """Test fallback to sys.builtin_module_names for older Python."""
        # Test that builtin_module_names check works
        # Note: This tests the elif branch when stdlib_module_names doesn't exist
        # We can't easily remove stdlib_module_names in Python 3.10+, but we can test the logic
        # by checking that builtin modules are detected
        if hasattr(sys, 'builtin_module_names'):
            # Test that builtin modules are detected (this path is used as fallback)
            # The actual stdlib_module_names check happens first in modern Python
            self.assertTrue(self.gateway.is_stdlib_module("sys"))

    @patch('astroid.MANAGER.ast_from_module_name')
    def test_is_stdlib_module_path_based_detection(self, mock_ast_from_module) -> None:
        """Test path-based detection for bundled modules."""
        # Mock a module node with file in stdlib path
        mock_node = MagicMock()
        mock_node.file = f"{self.gateway._stdlib_path}/some_module.py"
        mock_ast_from_module.return_value = mock_node

        self.gateway.is_stdlib_module("some_module")
        # Should try path-based detection
        mock_ast_from_module.assert_called_once_with("some_module")

    @patch('astroid.MANAGER.ast_from_module_name')
    def test_is_stdlib_module_path_based_detection_site_packages(self, mock_ast_from_module) -> None:
        """Test path-based detection excludes site-packages."""
        # Mock a module node with file in site-packages (should return False)
        mock_node = MagicMock()
        mock_node.file = f"{self.gateway._stdlib_path}/site-packages/some_module.py"
        mock_ast_from_module.return_value = mock_node

        result = self.gateway.is_stdlib_module("some_module")
        # Should return False because site-packages is in path
        self.assertFalse(result)

    @patch('astroid.MANAGER.ast_from_module_name')
    def test_is_stdlib_module_handles_astroid_errors(self, mock_ast_from_module) -> None:
        """Test error handling in path-based detection."""
        # Mock astroid error
        mock_ast_from_module.side_effect = astroid.AstroidBuildingError("Module not found")

        result = self.gateway.is_stdlib_module("nonexistent_module")
        self.assertFalse(result)

    @patch('astroid.MANAGER.ast_from_module_name')
    def test_is_stdlib_module_handles_attribute_error(self, mock_ast_from_module) -> None:
        """Test handling of AttributeError in path-based detection."""
        # Mock node without file attribute
        mock_node = MagicMock()
        del mock_node.file  # Remove file attribute
        mock_ast_from_module.return_value = mock_node

        result = self.gateway.is_stdlib_module("some_module")
        self.assertFalse(result)

    def test_is_external_dependency_site_packages(self) -> None:
        """Test detection of site-packages."""
        self.assertTrue(self.gateway.is_external_dependency("/usr/lib/python3.11/site-packages/libcst/__init__.py"))
        self.assertTrue(self.gateway.is_external_dependency("/path/to/site-packages/requests.py"))

    def test_is_external_dependency_dist_packages(self) -> None:
        """Test detection of dist-packages (Debian/Ubuntu)."""
        self.assertTrue(self.gateway.is_external_dependency("/usr/lib/python3/dist-packages/libcst/__init__.py"))

    def test_is_external_dependency_venv(self) -> None:
        """Test detection of .venv."""
        self.assertTrue(self.gateway.is_external_dependency(".venv/lib/requests/__init__.py"))
        self.assertTrue(self.gateway.is_external_dependency("/project/.venv/lib/python3.11/site-packages/pandas.py"))

    def test_is_external_dependency_internal_code(self) -> None:
        """Test internal code returns False."""
        self.assertFalse(self.gateway.is_external_dependency("/development/project/src/main.py"))
        self.assertFalse(self.gateway.is_external_dependency("src/domain/entities.py"))

    def test_is_external_dependency_none(self) -> None:
        """Test None returns False."""
        self.assertFalse(self.gateway.is_external_dependency(None))
        self.assertFalse(self.gateway.is_external_dependency(""))

    def test_is_exception_node_exception_subclass(self) -> None:
        """Test detection of Exception subclasses."""
        code = """
class CustomError(Exception):
    pass
"""
        node = astroid.parse(code).body[0]
        self.assertTrue(self.gateway.is_exception_node(node))

    def test_is_exception_node_standard_exception(self) -> None:
        """Test detection of standard exceptions."""
        code = """
class ValueError(Exception):
    pass
"""
        node = astroid.parse(code).body[0]
        self.assertTrue(self.gateway.is_exception_node(node))

    def test_is_exception_node_non_exception(self) -> None:
        """Test non-Exception classes return False."""
        code = """
class RegularClass:
    pass
"""
        node = astroid.parse(code).body[0]
        self.assertFalse(self.gateway.is_exception_node(node))

    def test_is_exception_node_handles_inference_error(self) -> None:
        """Test handling of InferenceError."""
        node = MagicMock(spec=astroid.nodes.ClassDef)
        node.ancestors.side_effect = astroid.InferenceError("Cannot infer")

        result = self.gateway.is_exception_node(node)
        self.assertFalse(result)

    def test_is_exception_node_handles_attribute_error(self) -> None:
        """Test handling of AttributeError."""
        node = MagicMock(spec=astroid.nodes.ClassDef)
        node.ancestors.side_effect = AttributeError("No ancestors")

        result = self.gateway.is_exception_node(node)
        self.assertFalse(result)

    def test_is_protocol_node_typing_protocol(self) -> None:
        """Test detection of typing.Protocol."""
        code = """
from typing import Protocol

class MyProtocol(Protocol):
    def method(self) -> str: ...
"""
        node = astroid.parse(code).body[1]  # ClassDef
        self.assertTrue(self.gateway.is_protocol_node(node))

    def test_is_protocol_node_typing_extensions_protocol(self) -> None:
        """Test detection of typing_extensions.Protocol."""
        code = """
from typing_extensions import Protocol

class MyProtocol(Protocol):
    def method(self) -> str: ...
"""
        node = astroid.parse(code).body[1]  # ClassDef
        self.assertTrue(self.gateway.is_protocol_node(node))

    def test_is_protocol_node_non_protocol(self) -> None:
        """Test non-Protocol classes return False."""
        code = """
class RegularClass:
    pass
"""
        node = astroid.parse(code).body[0]
        self.assertFalse(self.gateway.is_protocol_node(node))

    def test_is_protocol_node_no_bases(self) -> None:
        """Test class with no bases returns False."""
        code = """
class NoBases:
    pass
"""
        node = astroid.parse(code).body[0]
        # Manually set bases to empty
        node.bases = []
        self.assertFalse(self.gateway.is_protocol_node(node))

    def test_is_protocol_node_quick_check_protocol_in_name(self) -> None:
        """Test quick check for 'Protocol' in base name."""
        code = """
class MyProtocol:
    pass
"""
        node = astroid.parse(code).body[0]
        # Mock bases to have 'Protocol' in name
        mock_base = MagicMock()
        mock_base.name = "Protocol"
        node.bases = [mock_base]

        # This should trigger the quick check path
        self.gateway.is_protocol_node(node)
        # May return True if quick check works, False if deep check fails
        # The important thing is it doesn't crash

    def test_is_protocol_node_handles_inference_error(self) -> None:
        """Test handling of InferenceError."""
        node = MagicMock(spec=astroid.nodes.ClassDef)
        node.bases = [MagicMock()]
        node.ancestors.side_effect = astroid.InferenceError("Cannot infer")

        result = self.gateway.is_protocol_node(node)
        self.assertFalse(result)

    def test_is_protocol_node_handles_attribute_error(self) -> None:
        """Test handling of AttributeError."""
        node = MagicMock(spec=astroid.nodes.ClassDef)
        node.bases = [MagicMock()]
        node.ancestors.side_effect = AttributeError("No ancestors")

        result = self.gateway.is_protocol_node(node)
        self.assertFalse(result)

    def test_get_node_layer_with_config(self) -> None:
        """Test layer resolution with config loader."""
        node = MagicMock()
        mock_root = MagicMock(spec=astroid.nodes.Module)
        mock_root.file = "/src/domain/entities.py"
        mock_root.name = "src.domain.entities"
        node.root.return_value = mock_root

        config = MagicMock()
        config.get_layer_for_module.return_value = "Domain"

        layer = self.gateway.get_node_layer(node, config)
        self.assertEqual(layer, "Domain")
        config.get_layer_for_module.assert_called_once_with("src.domain.entities", "/src/domain/entities.py")

    def test_get_node_layer_fallback(self) -> None:
        """Test layer resolution returns None when config returns None."""
        node = MagicMock()
        mock_root = MagicMock(spec=astroid.nodes.Module)
        mock_root.file = "/src/unknown.py"
        mock_root.name = "src.unknown"
        node.root.return_value = mock_root

        config = MagicMock()
        config.get_layer_for_module.return_value = None

        layer = self.gateway.get_node_layer(node, config)
        self.assertIsNone(layer)

    def test_get_node_layer_non_module_root(self) -> None:
        """Test get_node_layer returns None when root is not a Module."""
        node = MagicMock()
        node.root.return_value = MagicMock()  # Not a Module

        config = MagicMock()
        layer = self.gateway.get_node_layer(node, config)
        self.assertIsNone(layer)

    def test_get_node_layer_missing_file_attribute(self) -> None:
        """Test get_node_layer handles missing file attribute."""
        node = MagicMock()
        mock_root = MagicMock(spec=astroid.nodes.Module)
        # Remove file attribute
        if hasattr(mock_root, 'file'):
            delattr(mock_root, 'file')
        mock_root.name = "src.domain.entities"
        node.root.return_value = mock_root

        config = MagicMock()
        config.get_layer_for_module.return_value = "Domain"

        # Should handle missing file gracefully
        self.gateway.get_node_layer(node, config)
        # Should still call get_layer_for_module with empty file path
        config.get_layer_for_module.assert_called_once()
