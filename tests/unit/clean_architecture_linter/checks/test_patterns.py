import unittest
from clean_architecture_linter.config import ConfigurationLoader
from clean_architecture_linter.checks.patterns import PatternChecker, CouplingChecker
from tests.linter_test_utils import run_checker


class TestPatternChecker(unittest.TestCase):

    def setUp(self):
        ConfigurationLoader._instance = None

    def test_pattern_checker_delegation(self):
        """Test _is_delegation_call via visit_if."""
        code = """
def process(x):
    if x == 1:
        return do_something(x)
    elif x == 2:
        return do_other(x)
        """
        # Need >= 2 branches or else clause for chain detection
        msgs = run_checker(PatternChecker, code, "src/use_cases/logic.py")
        self.assertIn("clean-arch-delegation", msgs)

    def test_pattern_checker_no_delegation_complex(self):
        """Test that complex logic is not flagged as delegation."""
        code = """
def process(x):
    if x == 1:
        y = x + 1
        return y
        """
        msgs = run_checker(PatternChecker, code, "src/use_cases/logic.py")
        self.assertEqual(msgs, [])


class TestCouplingChecker(unittest.TestCase):

    def setUp(self):
        ConfigurationLoader._instance = None

    def test_demeter_chain_violation(self):
        code = """
def logic(obj):
    obj.a.b.c()
        """
        msgs = run_checker(CouplingChecker, code, "src/use_cases/logic.py")
        self.assertIn("clean-arch-demeter", msgs)

    def test_demeter_stranger_violation(self):
        code = """
def logic(obj):
    stranger = obj.get_thing()
    stranger.do_stuff()
        """
        msgs = run_checker(CouplingChecker, code, "src/use_cases/logic.py")
        self.assertIn("clean-arch-demeter", msgs)

    def test_demeter_allowed(self):
        code = """
def logic(obj):
    obj.allowed().sort() # 'sort' is allowed terminal
        """
        msgs = run_checker(CouplingChecker, code, "src/use_cases/logic.py")
        self.assertEqual(msgs, [])


if __name__ == "__main__":
    unittest.main()
