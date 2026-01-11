import tokenize
import unittest
from io import BytesIO

from clean_architecture_linter.checks.bypass import BypassChecker

from tests.linter_test_utils import MockLinter


class TestBypassChecker(unittest.TestCase):
    def run_token_checker(self, code):
        linter = MockLinter()
        checker = BypassChecker(linter)

        tokens = list(tokenize.tokenize(BytesIO(code.encode("utf-8")).readline))
        checker.process_tokens(tokens)
        return linter.messages

    def test_global_disable(self):
        code = "# pylint: disable=all\nclass Foo: pass"
        msgs = self.run_token_checker(code)
        self.assertIn("anti-bypass-violation", msgs)

    def test_unjustified_disable(self):
        code = """
class Foo:
    def bar(self, a, b, c, d, e, f, g): # pylint: disable=too-many-arguments
        pass
        """
        msgs = self.run_token_checker(code)
        self.assertIn("anti-bypass-violation", msgs)  # Unjustified

    def test_justified_disable(self):
        code = """
class Foo:
    # JUSTIFICATION: This is a legacy method
    def bar(self, a, b, c, d, e, f, g): # pylint: disable=too-many-arguments
        pass
        """
        msgs = self.run_token_checker(code)
        self.assertEqual(msgs, [])

    def test_banned_justification(self):
        code = """
class Foo:
    # JUSTIFICATION: internal helper
    def bar(self, a, b, c, d, e, f, g): # pylint: disable=too-many-arguments
        pass
        """
        msgs = self.run_token_checker(code)
        self.assertIn("anti-bypass-violation", msgs)

    def test_allowed_disable(self):
        code = """
x = 1 # pylint: disable=line-too-long
        """
        msgs = self.run_token_checker(code)
        self.assertEqual(msgs, [])


if __name__ == "__main__":
    unittest.main()
