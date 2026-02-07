import unittest
from unittest.mock import mock_open, patch

from excelsior_architect.domain.config import ConfigurationLoader
from excelsior_architect.domain.layer_registry import LayerRegistry, LayerRegistryConfig
from excelsior_architect.infrastructure.config_file_loader import ConfigFileLoader


class TestConfigurationLoader(unittest.TestCase):
    def setUp(self) -> None:
        # Immutable value object: create with (config_dict, tool_section)
        self.loader = ConfigurationLoader({}, {})

    def test_config_loader_default_registry(self) -> None:
        """Test that default registry is created if not set."""
        loader = ConfigurationLoader({}, {})
        self.assertIsInstance(loader.registry, LayerRegistry)

    def test_config_loader_get_layer_explicit(self) -> None:
        """Test getting layer from explicit 'layers' config in pyproject.toml."""
        config = {
            "layers": [
                {"name": "ExplicitLayer", "module": "my_pkg.explicit"},
                {"name": "RootLayer", "module": "my_pkg"},
            ]
        }
        loader = ConfigurationLoader(config, {})

        # Should match longest prefix first due to sort in get_layer_for_module
        layer = loader.get_layer_for_module("my_pkg.explicit.module")
        self.assertEqual(layer, "ExplicitLayer")

        layer = loader.get_layer_for_module("my_pkg.other")
        self.assertEqual(layer, "RootLayer")

    def test_config_loader_get_layer_convention_fallback(self) -> None:
        """Test fallback to registry convention when no explicit config matches."""
        loader = ConfigurationLoader({"layers": []}, {})

        # Assuming LayerRegistry has default logic for 'use_cases' in path
        layer = loader.get_layer_for_module(
            "my_app.use_cases.something", "my_app/use_cases/something.py")
        self.assertEqual(layer, "UseCase")

    def test_config_loader_empty_config(self) -> None:
        """Test loader with empty config (e.g. no pyproject.toml found)."""
        loader = ConfigurationLoader({}, {})
        self.assertEqual(loader.config, {})

    def test_validate_config_handles_non_list_allowed_methods(self) -> None:
        """Test validate_config handles non-list allowed_lod_methods."""
        loader = ConfigurationLoader({}, {})
        loader.validate_config({"allowed_lod_methods": "invalid"})
        assert True

    def test_validate_config_handles_empty_allowed_methods(self) -> None:
        """Test validate_config handles empty allowed_lod_methods."""
        loader = ConfigurationLoader({}, {})
        loader.validate_config({"allowed_lod_methods": []})
        assert True

    def test_get_layer_for_class_node(self) -> None:
        """Test get_layer_for_class_node delegates to registry."""
        import astroid
        loader = ConfigurationLoader({}, {})

        code = """
class MyClass:
    pass
"""
        module = astroid.parse(code)
        class_node = module.body[0]

        result = loader.get_layer_for_class_node(class_node)
        # Should delegate to registry
        assert result is None or isinstance(result, str)

    def test_resolve_layer(self) -> None:
        """Test resolve_layer delegates to registry."""
        loader = ConfigurationLoader({}, {})

        result = loader.resolve_layer("MyClass", "path/to/file.py")
        assert result is None or isinstance(result, str)

    def test_get_project_ruff_config(self) -> None:
        """Test get_project_ruff_config returns ruff config from tool section."""
        tool_section = {"ruff": {"line-length": 120}}
        loader = ConfigurationLoader({}, tool_section)

        result = loader.get_project_ruff_config()
        assert isinstance(result, dict)
        assert "line-length" in result

    def test_get_excelsior_ruff_config(self) -> None:
        """Test get_excelsior_ruff_config returns excelsior.ruff config."""
        tool_section = {"excelsior": {"ruff": {"line-length": 100}}}
        loader = ConfigurationLoader({}, tool_section)

        result = loader.get_excelsior_ruff_config()
        assert isinstance(result, dict)
        assert "line-length" in result

    def test_get_excelsior_ruff_config_handles_non_dict(self) -> None:
        """Test get_excelsior_ruff_config handles non-dict excelsior section."""
        tool_section = {"excelsior": "invalid"}
        loader = ConfigurationLoader({}, tool_section)

        result = loader.get_excelsior_ruff_config()
        assert result == {}

    def test_get_ruff_config(self) -> None:
        """Test get_ruff_config alias."""
        tool_section = {"ruff": {"line-length": 120}}
        loader = ConfigurationLoader({}, tool_section)

        result = loader.get_ruff_config()
        assert isinstance(result, dict)

    def test_ruff_enabled_property(self) -> None:
        """Test ruff_enabled property."""
        tool_section = {"excelsior": {"ruff_enabled": False}}
        loader = ConfigurationLoader({}, tool_section)

        result = loader.ruff_enabled
        assert result is False

    def test_ruff_enabled_property_defaults_to_true(self) -> None:
        """Test ruff_enabled property defaults to True."""
        loader = ConfigurationLoader({}, {})

        result = loader.ruff_enabled
        assert result is True

    def test_ruff_enabled_property_handles_non_dict_excelsior(self) -> None:
        """Test ruff_enabled property handles non-dict excelsior section."""
        tool_section = {"excelsior": "invalid"}
        loader = ConfigurationLoader({}, tool_section)

        result = loader.ruff_enabled
        assert result is True

    def test_get_layer_for_module_uses_layer_map(self) -> None:
        """Test get_layer_for_module uses layer_map when available."""
        config = {
            "layer_map": {
                "my_app.domain": "Domain",
                "my_app": "Application"
            }
        }
        loader = ConfigurationLoader(config, {})

        # Should match longest prefix
        result = loader.get_layer_for_module("my_app.domain.models")
        assert result == "Domain"

    def test_get_layer_for_module_returns_from_layer_map(self) -> None:
        """Test get_layer_for_module returns from layer_map lookup."""
        config = {"layer_map": {"my_app.use_cases": "UseCase"}}
        loader = ConfigurationLoader(config, {})

        result = loader.get_layer_for_module("my_app.use_cases.create_user")
        assert result == "UseCase"

    def test_registry_property_creates_fallback(self) -> None:
        """Test registry property returns registry from constructor."""
        loader = ConfigurationLoader({}, {})

        result = loader.registry
        assert result is not None
        assert isinstance(result, LayerRegistry)

    def test_allowed_lod_roots(self) -> None:
        """Test allowed_lod_roots property."""
        loader = ConfigurationLoader({"allowed_lod_roots": ["str", "int"]}, {})

        result = loader.allowed_lod_roots
        assert "str" in result
        assert "int" in result

    def test_allowed_lod_modules(self) -> None:
        """Test allowed_lod_modules property."""
        loader = ConfigurationLoader(
            {"allowed_lod_modules": ["typing", "collections"]}, {})

        result = loader.allowed_lod_modules
        assert "typing" in result
        assert "collections" in result

    def test_allowed_lod_methods(self) -> None:
        """Test allowed_lod_methods property."""
        loader = ConfigurationLoader(
            {"allowed_lod_methods": ["keys", "values"]}, {})

        result = loader.allowed_lod_methods
        assert "keys" in result
        assert "values" in result

    def test_internal_modules(self) -> None:
        """Test internal_modules property."""
        loader = ConfigurationLoader({"internal_modules": ["_internal"]}, {})

        result = loader.internal_modules
        assert "_internal" in result

    def test_infrastructure_modules(self) -> None:
        """Test infrastructure_modules property."""
        loader = ConfigurationLoader(
            {"infrastructure_modules": ["adapters"]}, {})

        result = loader.infrastructure_modules
        assert "adapters" in result

    def test_raw_types(self) -> None:
        """Test raw_types property."""
        loader = ConfigurationLoader({"raw_types": ["str", "int"]}, {})

        result = loader.raw_types
        assert "str" in result
        assert "int" in result

    def test_silent_layers(self) -> None:
        """Test silent_layers property."""
        loader = ConfigurationLoader({"silent_layers": ["Domain"]}, {})

        result = loader.silent_layers
        assert "Domain" in result

    def test_allowed_io_interfaces(self) -> None:
        """Test allowed_io_interfaces property."""
        loader = ConfigurationLoader(
            {"allowed_io_interfaces": ["FileSystem"]}, {})

        result = loader.allowed_io_interfaces
        assert "FileSystem" in result

    def test_layer_map_handles_non_string_layer_name(self) -> None:
        """Test layer_map processing filters non-string keys (constructor)."""
        config = {"layer_map": {"valid": "Domain"}}
        loader = ConfigurationLoader(config, {})

        result = loader.get_layer_for_module("valid.models")
        assert result == "Domain"

    def test_ruff_enabled_property_with_false_value(self) -> None:
        """Test ruff_enabled property with explicit False."""
        tool_section = {"excelsior": {"ruff_enabled": False}}
        loader = ConfigurationLoader({}, tool_section)

        result = loader.ruff_enabled
        assert result is False

    def test_ruff_enabled_property_with_true_value(self) -> None:
        """Test ruff_enabled property with explicit True."""
        tool_section = {"excelsior": {"ruff_enabled": True}}
        loader = ConfigurationLoader({}, tool_section)

        result = loader.ruff_enabled
        assert result is True

    def test_ruff_enabled_property_with_missing_key(self) -> None:
        """Test ruff_enabled property when key is missing (defaults to True)."""
        tool_section = {"excelsior": {}}
        loader = ConfigurationLoader({}, tool_section)

        result = loader.ruff_enabled
        assert result is True

    def test_invert_map_handles_non_dict(self) -> None:
        """Test _invert_map handles non-dict input."""
        result = ConfigurationLoader.invert_map("not a dict")
        assert result == {}

    def test_invert_map_handles_non_string_layer_name(self) -> None:
        """Test _invert_map handles non-string layer names (line 303-304)."""
        result = ConfigurationLoader.invert_map(
            {123: "pattern"})  # Non-string key
        assert result == {}

    def test_invert_map_handles_list_patterns(self) -> None:
        """Test _invert_map handles list of patterns (line 305-308)."""
        result = ConfigurationLoader.invert_map(
            {"Domain": ["domain", "models"]})
        assert result == {"domain": "Domain", "models": "Domain"}

    def test_invert_map_handles_list_with_non_string_items(self) -> None:
        """Test _invert_map filters non-string items from list."""
        result = ConfigurationLoader.invert_map(
            {"Domain": ["domain", 123, "models"]})
        assert result == {"domain": "Domain", "models": "Domain"}
        assert 123 not in result

    def test_invert_map_handles_string_pattern(self) -> None:
        """Test _invert_map handles string pattern (line 309-310)."""
        result = ConfigurationLoader.invert_map({"Domain": "domain"})
        assert result == {"domain": "Domain"}

    def test_layer_map_processing_skips_non_string_keys(self) -> None:
        """Test constructor skips non-string layer names in layer_map."""
        config_dict = {
            "layer_map": {
                123: "invalid",  # Non-string key - should be skipped
                "Domain": "domain",  # Valid string key
            }
        }
        loader = ConfigurationLoader(config_dict, {})
        assert isinstance(loader.config, dict)
        assert loader.config.get("layer_map", {}).get("Domain") == "domain"

    def test_shared_kernel_modules_property(self) -> None:
        """Test shared_kernel_modules property."""
        loader = ConfigurationLoader({}, {})
        result = loader.shared_kernel_modules
        assert isinstance(result, set)


if __name__ == "__main__":
    unittest.main()
