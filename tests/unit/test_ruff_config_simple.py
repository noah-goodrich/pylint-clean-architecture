"""Simplified unit tests for Ruff configuration methods."""

import unittest

from clean_architecture_linter.domain.config import ConfigurationLoader


class TestRuffConfigMethods(unittest.TestCase):
    """Test Ruff configuration methods on ConfigurationLoader."""

    def setUp(self) -> None:
        # Get the singleton instance
        self.loader = ConfigurationLoader()

    def test_get_project_ruff_config_exists(self) -> None:
        """Should return dict for get_project_ruff_config."""
        config = self.loader.get_project_ruff_config()
        self.assertIsInstance(config, dict)

    def test_get_excelsior_ruff_config_exists(self) -> None:
        """Should return dict for get_excelsior_ruff_config."""
        config = self.loader.get_excelsior_ruff_config()
        self.assertIsInstance(config, dict)

    def test_get_ruff_config_alias(self) -> None:
        """Should alias get_project_ruff_config."""
        project_config = self.loader.get_project_ruff_config()
        alias_config = self.loader.get_ruff_config()
        self.assertEqual(project_config, alias_config)

    def test_ruff_enabled_property(self) -> None:
        """Should have ruff_enabled property (defaults to True)."""
        # Default is True
        self.assertIsInstance(self.loader.ruff_enabled, bool)
        # In this project it should be enabled
        self.assertTrue(self.loader.ruff_enabled)


if __name__ == "__main__":
    unittest.main()
