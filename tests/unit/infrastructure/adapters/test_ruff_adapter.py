"""Unit tests for RuffAdapter."""

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from clean_architecture_linter.domain.entities import LinterResult
from clean_architecture_linter.infrastructure.adapters.ruff_adapter import RuffAdapter


class TestRuffAdapter(unittest.TestCase):
    """Test the RuffAdapter for running Ruff and parsing output."""

    def setUp(self) -> None:
        self.telemetry = MagicMock()
        self.adapter = RuffAdapter(telemetry=self.telemetry)

    def test_run_ruff_no_violations(self) -> None:
        """Should return empty list when Ruff finds no issues."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

            results = self.adapter.run(Path("/fake/path"))

            self.assertEqual(results, [])
            self.telemetry.step.assert_called()

    def test_run_ruff_with_violations(self) -> None:
        """Should parse Ruff JSON output into LinterResult objects."""
        # Actual Ruff JSON format
        ruff_json: str = """[
  {
    "code": "C901",
    "message": "`foo` is too complex (15 > 11)",
    "location": {"row": 10, "column": 5},
    "end_location": {"row": 10, "column": 20},
    "filename": "src/example.py",
    "url": "https://docs.astral.sh/ruff/rules/complex-structure"
  }
]"""

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout=ruff_json,
                stderr=""
            )

            results = self.adapter.run(Path("/fake/path"))

            self.assertEqual(len(results), 1)
            self.assertIsInstance(results[0], LinterResult)
            self.assertEqual(results[0].code, "C901")
            self.assertIn("too complex", results[0].message)
            self.assertIn("src/example.py:10", results[0].locations[0])

    def test_run_ruff_with_config_from_pyproject(self) -> None:
        """Should respect Ruff config from pyproject.toml."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

            self.adapter.run(Path("/fake/path"), config={"select": ["E", "F", "W"]})

            # Verify subprocess was called with proper args
            call_args = mock_run.call_args[0][0]
            self.assertIn("ruff", call_args[0])
            self.assertIn("check", call_args)

    def test_run_ruff_subprocess_error(self) -> None:
        """Should handle subprocess errors gracefully."""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = FileNotFoundError("ruff not found")

            results = self.adapter.run(Path("/fake/path"))

            self.assertEqual(len(results), 1)
            self.assertIn("Ruff not found", results[0].message)
            self.assertEqual(results[0].code, "RUFF_ERROR")

    def test_parse_ruff_output_empty(self) -> None:
        """Should handle empty Ruff output."""
        results = self.adapter._parse_ruff_output("", 0)
        self.assertEqual(results, [])

    def test_parse_ruff_output_malformed_json(self) -> None:
        """Should handle malformed JSON gracefully."""
        results = self.adapter._parse_ruff_output("not json{", 1)
        self.assertEqual(len(results), 1)
        self.assertIn("parse", results[0].message.lower())

    def test_get_default_config(self) -> None:
        """Should return comprehensive default Ruff config."""
        config = RuffAdapter.get_default_config()

        # Based on snowarch's strictest config
        self.assertEqual(config["line-length"], 120)
        self.assertEqual(config["lint"]["mccabe"]["max-complexity"], 10)
        self.assertIn("E", config["lint"]["select"])  # pycodestyle errors
        self.assertIn("F", config["lint"]["select"])  # pyflakes
        self.assertIn("W", config["lint"]["select"])  # pycodestyle warnings
        self.assertIn("C90", config["lint"]["select"])  # mccabe
        self.assertIn("I", config["lint"]["select"])  # isort
        self.assertIn("N", config["lint"]["select"])  # pep8-naming
        self.assertIn("B", config["lint"]["select"])  # flake8-bugbear
        self.assertIn("PL", config["lint"]["select"])  # pylint rules
        self.assertIn("UP", config["lint"]["select"])  # pyupgrade
        self.assertIn("SIM", config["lint"]["select"])  # flake8-simplify
        self.assertIn("ARG", config["lint"]["select"])  # flake8-unused-arguments
        self.assertIn("PTH", config["lint"]["select"])  # flake8-use-pathlib
        self.assertIn("RUF", config["lint"]["select"])  # Ruff-specific

    def test_merge_configs_project_wins(self) -> None:
        """Should merge configs with project settings taking precedence (Option C)."""
        project_config = {
            "line-length": 100,
            "lint": {"select": ["E", "F"]}
        }
        excelsior_config = {
            "line-length": 120,
            "lint": {"select": ["E", "F", "W", "I"]}
        }

        merged = self.adapter._merge_configs(project_config, excelsior_config)

        # Project config wins for conflicts
        self.assertEqual(merged["line-length"], 100)  # Project wins
        # Project select list fully overrides (no merge)
        self.assertEqual(set(merged["lint"]["select"]), {"E", "F"})
        # But defaults still present
        self.assertIn("mccabe", merged["lint"])


if __name__ == "__main__":
    unittest.main()
