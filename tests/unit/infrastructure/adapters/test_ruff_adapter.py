"""Unit tests for RuffAdapter."""

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from excelsior_architect.domain.entities import LinterResult
from excelsior_architect.infrastructure.adapters.ruff_adapter import RuffAdapter


class TestRuffAdapter(unittest.TestCase):
    """Test the RuffAdapter for running Ruff and parsing output."""

    def setUp(self) -> None:
        self.telemetry = MagicMock()
        self._config_loader = MagicMock()
        self._config_loader.get_project_ruff_config.return_value = {}
        self._config_loader.get_excelsior_ruff_config.return_value = {}
        self.raw_log_port = MagicMock()
        self.guidance_service = MagicMock()
        self.adapter = RuffAdapter(
            config_loader=self._config_loader,
            telemetry=self.telemetry,
            raw_log_port=self.raw_log_port,
            guidance_service=self.guidance_service,
        )

    def test_run_ruff_no_violations(self) -> None:
        """Should return empty list when Ruff finds no issues."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="", stderr="")

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
            mock_run.return_value = MagicMock(
                returncode=0, stdout="", stderr="")

            self.adapter.run(Path("/fake/path"),
                             config={"select": ["E", "F", "W"]})

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
        # flake8-unused-arguments
        self.assertIn("ARG", config["lint"]["select"])
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

    def test_run_with_select_only_adds_select_flag(self) -> None:
        """run(select_only=...) adds --select to command."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="", stderr="")
            self.adapter.run(Path("/fake/path"), select_only=["E", "F", "I"])
            call_args = mock_run.call_args[0][0]
            self.assertIn("--select", call_args)
            self.assertIn("E,F,I", call_args)

    def test_run_calls_raw_log_port_when_set(self) -> None:
        """When _raw_log_port is set, log_raw is called with stdout/stderr."""
        raw_log = MagicMock()
        adapter = RuffAdapter(
            config_loader=MagicMock(),
            telemetry=self.telemetry,
            raw_log_port=raw_log,
            guidance_service=MagicMock(),
        )
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1, stdout="out", stderr="err"
            )
            adapter.run(Path("/fake/path"))
            raw_log.log_raw.assert_called_once_with("ruff", "out", "err")

    def test_run_timeout_returns_error_result(self) -> None:
        """When subprocess times out, return RUFF_ERROR result."""
        import subprocess
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("ruff", 300)
            results = self.adapter.run(Path("/fake/path"))
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].code, "RUFF_ERROR")
            self.assertIn("timed out", results[0].message)

    def test_run_generic_exception_returns_error_result(self) -> None:
        """When subprocess raises generic Exception, return RUFF_ERROR result."""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = RuntimeError("something broke")
            results = self.adapter.run(Path("/fake/path"))
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].code, "RUFF_ERROR")
            self.assertIn("something broke", results[0].message)

    def test_get_manual_fix_instructions_without_guidance_returns_fallback(self) -> None:
        """When guidance_service.get_manual_instructions returns empty, return fallback or default."""
        guidance = MagicMock()
        guidance.get_manual_instructions.return_value = ""
        adapter = RuffAdapter(
            config_loader=MagicMock(),
            telemetry=self.telemetry,
            raw_log_port=MagicMock(),
            guidance_service=guidance,
        )
        text = adapter.get_manual_fix_instructions("ARG001")
        self.assertIn("unused", text.lower())
        text_unknown = adapter.get_manual_fix_instructions("UNKNOWN_CODE")
        self.assertIn("Ruff documentation", text_unknown)

    def test_apply_fixes_with_select_only(self) -> None:
        """apply_fixes with select_only adds --select to command."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="", stderr="")
            result = self.adapter.apply_fixes(
                Path("/fake/path"), select_only=["I", "UP"]
            )
            self.assertTrue(result)
            call_args = mock_run.call_args[0][0]
            self.assertIn("--select", call_args)
            self.assertIn("I,UP", call_args)

    def test_apply_fixes_file_not_found_returns_false(self) -> None:
        """When ruff is not installed, apply_fixes returns False."""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = FileNotFoundError("ruff not found")
            result = self.adapter.apply_fixes(Path("/fake/path"))
            self.assertFalse(result)
            self.telemetry.step.assert_called()
            self.assertIn("Ruff not found", str(self.telemetry.step.call_args))


if __name__ == "__main__":
    unittest.main()
