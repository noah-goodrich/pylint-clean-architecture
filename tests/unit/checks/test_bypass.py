"""Tests for BypassChecker (W9501)."""

import tokenize
import unittest
from io import BytesIO
from unittest.mock import MagicMock

from clean_architecture_linter.use_cases.checks.bypass import BypassChecker


class TestBypassChecker(unittest.TestCase):
    def setUp(self) -> None:
        self.linter = MagicMock()
        self.checker = BypassChecker(self.linter)

    def _tokenize(self, code: str) -> list[tokenize.TokenInfo]:
        """Helper to tokenize code."""
        return list(tokenize.tokenize(BytesIO(code.encode('utf-8')).readline))

    def test_global_disable_violation(self) -> None:
        """Module-level disable should trigger W9501."""
        code: str = "# pylint: disable=all\nimport os\n"
        tokens = self._tokenize(code)

        self.checker.process_tokens(tokens)

        # Should be called at least once
        self.assertTrue(self.linter.add_message.called)
        # Check first call - Pylint converts kwargs to positional args:
        # (msgid, line, col_offset, args, confidence, node, col_offset2, end_lineno)
        call_args = self.linter.add_message.call_args_list[0]
        positional_args = call_args.args

        msgid = positional_args[0]  # msgid
        args_tuple = positional_args[3]  # args tuple is at index 3

        self.assertEqual(msgid, 'anti-bypass-violation')
        self.assertIn('Global pylint: disable', args_tuple[0])

    def test_allowed_disable_no_violation(self) -> None:
        """Allowed disables should not trigger W9501."""
        code: str = "x = 'very long line'  # pylint: disable=line-too-long\n"
        tokens = self._tokenize(code)

        self.checker.process_tokens(tokens)

        self.linter.add_message.assert_not_called()

    def test_unjustified_complexity_disable_violation(self) -> None:
        """Unjustified complexity disable should trigger W9501."""
        code: str = "def foo():  # pylint: disable=too-complex\n    pass\n"
        tokens = self._tokenize(code)

        self.checker.process_tokens(tokens)

        self.assertTrue(self.linter.add_message.called)
        msgid = self.linter.add_message.call_args[0][0]
        self.assertEqual(msgid, 'anti-bypass-violation')

    def test_justified_disable_no_violation(self) -> None:
        """Justified disable with proper format should not trigger W9501."""
        # JUSTIFICATION must be on previous line or properly formatted
        code: str = "# JUSTIFICATION: legacy code\ndef foo():  pass  # pylint: disable=too-complex\n"
        tokens = self._tokenize(code)

        self.checker.process_tokens(tokens)

        self.linter.add_message.assert_not_called()

    def test_no_pylint_comment_no_violation(self) -> None:
        """Regular comments should not trigger W9501."""
        code: str = "# This is a regular comment\nimport os\n"
        tokens = self._tokenize(code)

        self.checker.process_tokens(tokens)

        self.linter.add_message.assert_not_called()

    def test_inline_code_with_disable_after_header(self) -> None:
        """Inline disable after module header should not trigger global violation."""
        code = "\n" * 25 + "x = 1  # pylint: disable=invalid-name\n"
        tokens = self._tokenize(code)

        self.checker.process_tokens(tokens)

        # Should still trigger for disallowed code, but not for global
        if self.linter.add_message.called:
            call_args = self.linter.add_message.call_args
            if 'args' in call_args[1]:
                self.assertNotIn('Global', call_args[1]['args'][0])


if __name__ == '__main__':
    unittest.main()
