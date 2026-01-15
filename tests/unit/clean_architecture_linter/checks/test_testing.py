import unittest

from clean_architecture_linter.checks.testing import TestingChecker as CheckerToTest
from clean_architecture_linter.config import ConfigurationLoader
from tests.linter_test_utils import run_checker


class TestTestingChecker(unittest.TestCase):
    def setUp(self):
        ConfigurationLoader._instance = None

    def test_private_method_test(self):
        code = "def test_foo(): sut._private()"
        msgs = run_checker(CheckerToTest, code)
        self.assertIn("private-method-test", msgs)

    def test_fragile_test_mocks(self):
        code = """
        def test_heavy():
            patch('a'); patch('b'); patch('c'); patch('d'); patch('e')
        """
        msgs = run_checker(CheckerToTest, code)
        self.assertIn("fragile-test-mocks", msgs)


if __name__ == "__main__":
    unittest.main()
