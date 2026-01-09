import unittest
import tempfile
import shutil
import os
from pathlib import Path
from clean_architecture_linter.config import ConfigurationLoader
from clean_architecture_linter.layer_registry import LayerRegistry


class TestGenericConfiguration(unittest.TestCase):
    def setUp(self):
        # Reset Singleton
        ConfigurationLoader._instance = None
        self.test_dir = tempfile.mkdtemp()
        self.old_cwd = os.getcwd()
        os.chdir(self.test_dir)

    def tearDown(self):
        ConfigurationLoader._instance = None
        os.chdir(self.old_cwd)
        shutil.rmtree(self.test_dir)

    def test_custom_layer_mapping(self):
        """Test that custom layer mapping works (services -> UseCase)."""
        content = """
[tool.clean-arch]
project_type = "generic"

[tool.clean-arch.layer_map]
UseCase = ["services", "managers"]
Infrastructure = "gateways"
"""
        with open("pyproject.toml", "w") as f:
            f.write(content)

        loader = ConfigurationLoader()
        registry = loader.registry

        # Check explicit resolution
        # 1. 'services' and 'managers' directory should be UseCase
        layer = registry.resolve_layer("UserService", "src/services/user_service.py")
        self.assertEqual(layer, "UseCase")
        layer = registry.resolve_layer("UserManager", "src/managers/user_manager.py")
        self.assertEqual(layer, "UseCase")

        # 2. 'gateways' directory should be Infrastructure
        layer = registry.resolve_layer("UserGateway", "src/gateways/db.py")
        self.assertEqual(layer, "Infrastructure")

        # 3. Default 'domain' should still work
        layer = registry.resolve_layer("User", "src/domain/user.py")
        self.assertEqual(layer, "Domain")
