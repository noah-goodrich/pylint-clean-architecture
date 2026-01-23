from unittest.mock import MagicMock, patch
import unittest
from clean_architecture_linter.cli import check_command

class TestCheckCommand(unittest.TestCase):
    @patch("clean_architecture_linter.cli.MypyAdapter")
    @patch("clean_architecture_linter.cli.ExcelsiorAdapter")
    @patch("clean_architecture_linter.cli.ImportLinterAdapter")
    @patch("clean_architecture_linter.cli.TerminalReporter")
    def test_check_command_execution(self, mock_reporter, mock_il, mock_excelsior, mock_mypy):
        telemetry = MagicMock()
        target_path: str = "src"

        # Mock results
        mock_mypy_instance = mock_mypy.return_value
        mock_mypy_instance.gather_results.return_value = [
            MagicMock(to_dict=lambda: {"code": "MYPY001", "message": "error", "location": "f1.py:1"})
        ]

        mock_excelsior_instance = mock_excelsior.return_value
        mock_excelsior_instance.gather_results.return_value = [
            MagicMock(to_dict=lambda: {"code": "W9001", "message": "error", "location": "f2.py:2"})
        ]

        mock_il_instance = mock_il.return_value
        mock_il_instance.gather_results.return_value = [] # No IL errors for this test

        check_command(telemetry, target_path)

        # Verify calls
        telemetry.step.assert_any_call(f"Starting Excelsior Audit for: {target_path}")
        mock_mypy_instance.gather_results.assert_called_with(target_path)
        mock_excelsior_instance.gather_results.assert_called_with(target_path)

        # Verify reporter was called twice (once for Mypy, once for Excelsior, 0 for IL)
        self.assertEqual(mock_reporter.return_value.generate_report.call_count, 2)

if __name__ == "__main__":
    unittest.main()
