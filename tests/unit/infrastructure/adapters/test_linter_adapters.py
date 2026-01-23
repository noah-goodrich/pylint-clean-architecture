import unittest
from unittest.mock import patch, MagicMock
from clean_architecture_linter.infrastructure.adapters.linter_adapters import MypyAdapter, LinterResult

class TestMypyAdapter(unittest.TestCase):
    def setUp(self):
        self.adapter = MypyAdapter()

    def test_parse_output_with_errors(self):
        # Sample mypy output with error codes
        mypy_output = (
            "src/domain/user.py:10: error: Incompatible types in assignment (expression has type \"int\", variable has type \"str\")  [assignment]\n"
            "src/use_cases/login.py:5: error: Module \"requests\" has no attribute \"get\"  [attr-defined]\n"
            "src/domain/user.py:20: error: Incompatible types in assignment (expression has type \"float\", variable has type \"str\")  [assignment]\n"
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

    def test_parse_output_fallback(self):
        # Mypy output WITHOUT error codes
        mypy_output = "src/domain/user.py:10: error: Some generic error\n"
        results = self.adapter._parse_output(mypy_output)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].code, "MYPY")
        self.assertEqual(results[0].message, "Some generic error")

    @patch('subprocess.run')
    def test_gather_results_exception(self, mock_run):
        mock_run.side_effect = Exception("System Error")
        results = self.adapter.gather_results("src")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].code, "MYPY_ERROR")
        self.assertIn("System Error", results[0].message)

    @patch('subprocess.run')
    def test_gather_results(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout = "src/file.py:1: error: msg  [code]",
            returncode = 1
        )

        results = self.adapter.gather_results("src")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].code, "code")
        self.assertEqual(results[0].message, "msg")
        self.assertEqual(results[0].locations, ["src/file.py:1"])

class TestExcelsiorAdapter(unittest.TestCase):
    def setUp(self):
        from clean_architecture_linter.infrastructure.adapters.linter_adapters import ExcelsiorAdapter
        self.adapter = ExcelsiorAdapter()

    def test_parse_output(self):
        output = "src/domain/user.py:10: W9001: Dependency violation (dependency-violation)\n"
        results = self.adapter._parse_output(output)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].code, "W9001")
        self.assertEqual(results[0].message, "Dependency violation (dependency-violation)")

    @patch('subprocess.run')
    def test_gather_results(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout = "src/domain/user.py:10: W9001: msg\n",
            returncode = 1
        )
        results = self.adapter.gather_results("src")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].code, "W9001")

    @patch('subprocess.run')
    def test_gather_results_exception(self, mock_run):
        mock_run.side_effect = Exception("Pylint Failed")
        results = self.adapter.gather_results("src")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].code, "EXCELSIOR_ERROR")

if __name__ == "__main__":
    unittest.main()
