import unittest
from unittest.mock import MagicMock, patch

from clean_architecture_linter.infrastructure.adapters.linter_adapters import MypyAdapter


class TestMypyAdapter(unittest.TestCase):
    def setUp(self) -> None:
        self.adapter = MypyAdapter(
            raw_log_port=MagicMock(),
            guidance_service=MagicMock(),
        )

    def test_parse_output_with_errors(self) -> None:
        # Sample mypy output with error codes
        mypy_output = (
            "src/domain/user.py:10: error: Incompatible types in assignment "
            "(expression has type \"int\", variable has type \"str\")  [assignment]\n"
            "src/use_cases/login.py:5: error: Module \"requests\" has no attribute \"get\"  "
            "[attr-defined]\n"
            "src/domain/user.py:20: error: Incompatible types in assignment "
            "(expression has type \"float\", variable has type \"str\")  [assignment]\n"
        )

        results = self.adapter._parse_output(mypy_output)

        # Check we have 2 distinct error codes
        codes = [r.code for r in results]
        self.assertIn("assignment", codes)
        self.assertIn("attr-defined", codes)
        self.assertEqual(len(results), 2)

        # Check locations grouping
        assignment_result = [r for r in results if r.code == "assignment"][0]
        self.assertEqual(len(assignment_result.locations), 2)
        self.assertIn("src/domain/user.py:10", assignment_result.locations)
        self.assertIn("src/domain/user.py:20", assignment_result.locations)

    def test_parse_output_fallback(self) -> None:
        # Mypy output WITHOUT error codes
        mypy_output: str = "src/domain/user.py:10: error: Some generic error\n"
        results = self.adapter._parse_output(mypy_output)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].code, "MYPY")
        self.assertEqual(results[0].message, "Some generic error")

    @patch('subprocess.run')
    def test_gather_results_exception(self, mock_run) -> None:
        mock_run.side_effect = Exception("System Error")
        results = self.adapter.gather_results("src")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].code, "MYPY_ERROR")
        self.assertIn("System Error", results[0].message)

    @patch('subprocess.run')
    def test_gather_results(self, mock_run) -> None:
        mock_run.return_value = MagicMock(
            stdout="src/file.py:1: error: msg  [code]",
            returncode=1
        )

        results = self.adapter.gather_results("src")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].code, "code")
        self.assertEqual(results[0].message, "msg")
        self.assertEqual(results[0].locations, ["src/file.py:1"])

    @patch('subprocess.run')
    def test_gather_results_non_zero_unparsed_output(self, mock_run) -> None:
        """When mypy fails with non-zero exit and output doesn't match error pattern, report as MYPY_ERROR."""
        mock_run.return_value = MagicMock(
            stdout="Source file found twice under different module names",
            stderr="Some stderr",
            returncode=1
        )

        results = self.adapter.gather_results("src")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].code, "MYPY_ERROR")
        self.assertIn("Source file found twice", results[0].message)
        self.assertIn("Some stderr", results[0].message)


class TestExcelsiorAdapter(unittest.TestCase):
    def setUp(self) -> None:
        from clean_architecture_linter.domain.config import ConfigurationLoader
        from clean_architecture_linter.infrastructure.adapters.linter_adapters import ExcelsiorAdapter
        self.adapter = ExcelsiorAdapter(
            config_loader=ConfigurationLoader({}, {}),
            raw_log_port=MagicMock(),
            guidance_service=MagicMock(),
        )

    def test_parse_output(self) -> None:
        output: str = "src/domain/user.py:10: W9001: Dependency violation (dependency-violation)\n"
        results = self.adapter._parse_output(output)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].code, "W9001")
        self.assertEqual(results[0].message,
                         "Dependency violation (dependency-violation)")

    def test_parse_output_r0801_multiline_one_block_per_duplicate_group(self) -> None:
        # R0801 is multi-line: first line has trigger file:line, next lines are ==module:[start:end].
        # Parser must emit one LinterResult per block with real duplicate locations (from == lines).
        output = (
            "src/ignored.py:1: R0801: Similar lines in 2 files\n"
            "==clean_architecture_linter.infrastructure.adapters.mypy_adapter:[99:116]\n"
            "==clean_architecture_linter.infrastructure.adapters.ruff_adapter:[229:247]\n"
            "src/ignored.py:1: R0801: Similar lines in 2 files\n"
            "==clean_architecture_linter.infrastructure.reporters:[86:95]\n"
            "==clean_architecture_linter.infrastructure.services.audit_trail:[88:97]\n"
        )
        results = self.adapter._parse_output(output)
        r0801 = [r for r in results if r.code == "R0801"]
        self.assertEqual(
            len(r0801), 2, "expect one R0801 result per duplicate block")
        self.assertEqual(
            r0801[0].locations,
            [
                "src/clean_architecture_linter/infrastructure/adapters/mypy_adapter.py:99",
                "src/clean_architecture_linter/infrastructure/adapters/ruff_adapter.py:229",
            ],
        )
        self.assertEqual(
            r0801[1].locations,
            [
                "src/clean_architecture_linter/infrastructure/reporters.py:86",
                "src/clean_architecture_linter/infrastructure/services/audit_trail.py:88",
            ],
        )
        self.assertEqual(r0801[0].message, "Similar lines in 2 files")

    @patch('subprocess.run')
    def test_gather_results(self, mock_run) -> None:
        mock_run.return_value = MagicMock(
            stdout="src/domain/user.py:10: W9001: msg\n",
            returncode=1
        )
        results = self.adapter.gather_results("src")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].code, "W9001")

    @patch('subprocess.run')
    def test_gather_results_exception(self, mock_run) -> None:
        mock_run.side_effect = Exception("Pylint Failed")
        results = self.adapter.gather_results("src")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].code, "EXCELSIOR_ERROR")


if __name__ == "__main__":
    unittest.main()
