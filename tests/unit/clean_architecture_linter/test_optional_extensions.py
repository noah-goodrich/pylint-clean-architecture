import unittest
from unittest.mock import MagicMock, patch
from clean_architecture_linter import checker
from clean_architecture_linter.config import ConfigurationLoader


class TestOptionalExtensions(unittest.TestCase):
    def setUp(self):
        # Reset singleton
        ConfigurationLoader._instance = None
        self.linter = MagicMock()

    def tearDown(self):
        ConfigurationLoader._instance = None

    @patch("clean_architecture_linter.config.toml.load")
    @patch("builtins.open", new_callable=unittest.mock.mock_open, read_data=b"")
    @patch("pathlib.Path.exists", return_value=True)
    def test_default_registration(self, mock_exists, mock_open, mock_toml_load):
        # Default config (empty or no enabled_extensions)
        mock_toml_load.return_value = {"tool": {"clean-arch": {}}}

        # Reload config explicitly to be sure
        ConfigurationLoader()

        checker.register(self.linter)

        # Verify Snowflake NOT registered
        registered = [
            call.args[0].__class__.__name__
            for call in self.linter.register_checker.call_args_list
        ]
        self.assertNotIn("SnowflakeGovernanceChecker", registered)

    @patch("clean_architecture_linter.config.toml.load")
    @patch("builtins.open", new_callable=unittest.mock.mock_open, read_data=b"")
    @patch("pathlib.Path.exists", return_value=True)
    def test_snowflake_registration(self, mock_exists, mock_open, mock_toml_load):
        # Config with snowflake extension
        mock_toml_load.return_value = {
            "tool": {"clean-arch": {"enabled_extensions": ["snowflake"]}}
        }

        # Reload config
        ConfigurationLoader()

        checker.register(self.linter)

        # Verify Snowflake registered
        registered = [
            call.args[0].__class__.__name__
            for call in self.linter.register_checker.call_args_list
        ]
        self.assertIn("SnowflakeGovernanceChecker", registered)
