import unittest

from clean_architecture_linter.layer_registry import LayerRegistry


class TestLayerRegistry(unittest.TestCase):
    def test_registry_resolve_layer_by_suffix(self):
        """Test resolution by class name suffix (Priority 1)."""
        registry = LayerRegistry()

        self.assertEqual(registry.resolve_layer("CreateUserUseCase", ""), "UseCase")
        self.assertEqual(registry.resolve_layer("UserEntity", ""), "Domain")
        self.assertEqual(registry.resolve_layer("UserRepository", ""), "Infrastructure")
        self.assertEqual(registry.resolve_layer("UserController", ""), "Interface")

    def test_registry_resolve_layer_by_directory(self):
        """Test resolution by directory path (Priority 2)."""
        registry = LayerRegistry()

        # Relative paths
        self.assertEqual(registry.resolve_layer("", "src/use_cases/create_user.py"), "UseCase")
        self.assertEqual(registry.resolve_layer("", "src/domain/entities.py"), "Domain")
        self.assertEqual(registry.resolve_layer("", "src/infrastructure/db.py"), "Infrastructure")
        self.assertEqual(registry.resolve_layer("", "src/interface/cli.py"), "Interface")

        # Absolute paths
        self.assertEqual(
            registry.resolve_layer("", "/app/src/adapters/snowflake.py"),
            "Infrastructure",
        )

        # Dotted module paths
        self.assertEqual(registry.resolve_layer("", "app.use_cases.interactor"), "UseCase")

    def test_registry_resolve_layer_unresolved(self):
        """Test that unknown layers return None."""
        registry = LayerRegistry()
        self.assertIsNone(registry.resolve_layer("RandomClass", "utils/helper.py"))

    def test_registry_presets(self):
        """Test that project_type presets update the SUFFIX_MAP."""
        from clean_architecture_linter.layer_registry import LayerRegistryConfig

        registry = LayerRegistry(LayerRegistryConfig(project_type="fastapi_sqlalchemy"))
        self.assertEqual(registry.resolve_layer("UserModel", ""), "Infrastructure")

        registry_cli = LayerRegistry(LayerRegistryConfig(project_type="cli_app"))
        self.assertEqual(registry_cli.resolve_layer("DeployCommand", ""), "Interface")

    def test_registry_path_normalization(self):
        """Test path normalization logic."""
        registry = LayerRegistry()

        # Windows path
        self.assertEqual(registry.resolve_layer("", "src\\domain\\logic.py"), "Domain")

        # Dotted path with .py (should invoke strip)
        self.assertEqual(registry.resolve_layer("", "src.domain.logic.py"), "Domain")


if __name__ == "__main__":
    unittest.main()
