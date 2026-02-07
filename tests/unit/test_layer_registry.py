import unittest

from excelsior_architect.domain.layer_registry import LayerRegistry


class TestLayerRegistry(unittest.TestCase):
    def test_registry_resolve_layer_by_suffix(self) -> None:
        """Test resolution by class name suffix (Priority 1)."""
        registry = LayerRegistry()

        self.assertEqual(registry.resolve_layer(
            "CreateUserUseCase", ""), "UseCase")
        self.assertEqual(registry.resolve_layer("UserEntity", ""), "Domain")
        self.assertEqual(registry.resolve_layer(
            "UserRepository", ""), "Infrastructure")
        self.assertEqual(registry.resolve_layer(
            "UserController", ""), "Interface")

    def test_registry_resolve_layer_by_directory(self) -> None:
        """Test resolution by directory path (Priority 2)."""
        registry = LayerRegistry()

        # Relative paths
        self.assertEqual(registry.resolve_layer(
            "", "src/use_cases/create_user.py"), "UseCase")
        self.assertEqual(registry.resolve_layer(
            "", "src/domain/entities.py"), "Domain")
        self.assertEqual(registry.resolve_layer(
            "", "src/infrastructure/db.py"), "Infrastructure")
        self.assertEqual(registry.resolve_layer(
            "", "src/interface/cli.py"), "Interface")

        # Absolute paths
        self.assertEqual(
            registry.resolve_layer("", "/app/src/adapters/snowflake.py"),
            "Infrastructure",
        )

        # Dotted module paths
        self.assertEqual(registry.resolve_layer(
            "", "app.use_cases.interactor"), "UseCase")

    def test_registry_resolve_layer_unresolved(self) -> None:
        """Test that unknown layers return None."""
        registry = LayerRegistry()
        self.assertIsNone(registry.resolve_layer(
            "RandomClass", "utils/helper.py"))

    def test_registry_presets(self) -> None:
        """Test that project_type presets update the SUFFIX_MAP."""
        from excelsior_architect.domain.layer_registry import LayerRegistryConfig

        registry = LayerRegistry(LayerRegistryConfig(
            project_type="fastapi_sqlalchemy"))
        self.assertEqual(registry.resolve_layer(
            "UserModel", ""), "Infrastructure")

        registry_cli = LayerRegistry(
            LayerRegistryConfig(project_type="cli_app"))
        self.assertEqual(registry_cli.resolve_layer(
            "DeployCommand", ""), "Interface")

    def test_registry_path_normalization(self) -> None:
        """Test path normalization logic."""
        registry = LayerRegistry()

        # Windows path
        self.assertEqual(registry.resolve_layer(
            "", "src\\domain\\logic.py"), "Domain")

        # Dotted path with .py (should invoke strip)
        self.assertEqual(registry.resolve_layer(
            "", "src.domain.logic.py"), "Domain")

    def test_get_layer_for_class_node_inheritance(self) -> None:
        """Test layer detection via inheritance using base_class_map."""
        from unittest.mock import MagicMock

        from excelsior_architect.domain.layer_registry import LayerRegistryConfig

        config = LayerRegistryConfig(
            base_class_map={"BaseUseCase": "UseCase"}
        )
        registry = LayerRegistry(config)

        # Mock AST node
        mock_node = MagicMock()
        mock_node.name = "MySpecialLogic"

        # Mock ancestors
        mock_base = MagicMock()
        mock_base.name = "BaseUseCase"
        mock_node.ancestors.return_value = [mock_base]

        # Should detect UseCase via inheritance
        layer = registry.get_layer_for_class_node(mock_node)
        self.assertEqual(layer, "UseCase")

        # Should respect suffix map priority if match found (which is step 1 in get_layer_for_class_node)
        mock_node.name = "MySpecialUseCase"
        layer_suffix = registry.get_layer_for_class_node(mock_node)
        self.assertEqual(layer_suffix, "UseCase")


if __name__ == "__main__":
    unittest.main()
