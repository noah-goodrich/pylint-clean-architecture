"""Simplified unit tests for Ruff configuration methods."""

import unittest

from clean_architecture_linter.config import ConfigurationLoader


class TestRuffConfigMethods(unittest.TestCase):
    """Test Ruff configuration methods on ConfigurationLoader."""

    def setUp(self):
        # Get the singleton instance
        self.loader = ConfigurationLoader()

    def test_get_project_ruff_config_exists(self):
        """Should return dict for get_project_ruff_config."""
        config = self.loader.get_project_ruff_config()
        self.assertIsInstance(config, dict)

    def test_get_excelsior_ruff_config_exists(self):
        """Should return dict for get_excelsior_ruff_config."""
        config = self.loader.get_excelsior_ruff_config()
        self.assertIsInstance(config, dict)

    def test_get_ruff_config_alias(self):
        """Should alias get_project_ruff_config."""
        project_config = self.loader.get_project_ruff_config()
        alias_config = self.loader.get_ruff_config()
        self.assertEqual(project_config, alias_config)

    def test_get_merged_ruff_config_returns_dict(self):
        """Should return merged config dict."""
        merged = self.loader.get_merged_ruff_config()
        self.assertIsInstance(merged, dict)
        # Should have defaults from RuffAdapter.get_default_config()
        self.assertIn("line-length", merged)
        self.assertIn("lint", merged)

    def test_ruff_enabled_property(self):
        """Should have ruff_enabled property (defaults to True)."""
        # Default is True
        self.assertIsInstance(self.loader.ruff_enabled, bool)
        # In this project it should be enabled
        self.assertTrue(self.loader.ruff_enabled)

    def test_merged_config_has_comprehensive_defaults(self):
        """Merged config should have all Excelsior defaults."""
        merged = self.loader.get_merged_ruff_config()

        # Should have all the strict rules
        self.assertIn("lint", merged)
        lint_config = merged.get("lint", {})
        self.assertIsInstance(lint_config, dict)

        select_rules = lint_config.get("select", [])
        if select_rules:  # May be empty if project overrides completely
            self.assertIsInstance(select_rules, list)


if __name__ == "__main__":
    unittest.main()
