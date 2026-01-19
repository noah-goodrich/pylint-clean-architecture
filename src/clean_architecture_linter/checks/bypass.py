"""Anti-Bypass Guard checks (W9501)."""

import tokenize
from typing import TYPE_CHECKING, ClassVar, Optional

if TYPE_CHECKING:
    from pylint.lint import PyLinter

from pylint.checkers import BaseTokenChecker

_MODULE_HEADER_MAX_LINES = 20


class BypassChecker(BaseTokenChecker):
    """W9501: Anti-Bypass Guard enforcement."""

    name = "clean-arch-bypass"

    def __init__(self, linter: Optional["PyLinter"] = None) -> None:
        self.msgs = {
            "W9501": (
                "Anti-Bypass Violation: %s detected. %s Clean Fix: Justify with '# JUSTIFICATION: <reason>' or "
                "resolve the architectural issue.",
                "anti-bypass-violation",
                "Module-level disables or unjustified complexity disables are forbidden.",
            )
        }
        super().__init__(linter)

    ALLOWED_DISABLES: ClassVar[set[str]] = {
        "line-too-long",
        "missing-docstring",
        "trailing-whitespace",
    }

    def process_tokens(self, tokens: list[tokenize.TokenInfo]) -> None:
        """Scan tokens for forbidden pylint: disable comments."""
        lines = {}
        for tok_type, tok_string, start, _, line_content in tokens:
            if tok_type == tokenize.COMMENT:
                lineno = start[0]
                lines[lineno] = line_content
                self._check_comment(tok_string, lineno, line_content, lines)

    def _check_comment(self, tok_string: str, lineno: int, line_content: str, lines: dict[int, str]) -> None:
        """Check a single comment for bypass violations."""
        if "pylint:" not in tok_string or "disable=" not in tok_string:
            return

        # 1. Check for module-level (global) disable
        is_standalone = not line_content.split("#")[0].strip()
        if lineno < _MODULE_HEADER_MAX_LINES and is_standalone:
            self.add_message(
                "anti-bypass-violation",
                line=lineno,
                args=("Global pylint: disable", "Fix the issue instead."),
            )

        # 2. Check for disables not in the allow list
        # Extract everything after disable=
        try:
            disable_part = tok_string.split("disable=")[1].split("#")[0].split(";")[0]
            rules = [r.strip() for r in disable_part.split(",")]
            for rule in rules:
                if not rule:
                    continue
                if rule not in self.ALLOWED_DISABLES:
                    self._check_justification(rule, lineno, lines)
        except IndexError:
            pass

    BANNED_PHRASES: ClassVar[set[str]] = {
        "internal helper",
        "detailed arguments",
        "passing the linter",
    }

    def _check_justification(self, forbidden: str, lineno: int, lines: dict[int, str]) -> None:
        """Ensure forbidden disable is justified on previous line."""
        prev_lineno = lineno - 1
        justified = False
        justification_content = ""
        if prev_lineno in lines:
            line = lines[prev_lineno]
            if "JUSTIFICATION:" in line:
                justified = True
                justification_content = line.split("JUSTIFICATION:")[1].strip().lower()

        if not justified:
            self.add_message(
                "anti-bypass-violation",
                line=lineno,
                args=(
                    f"Unjustified disable of {forbidden}",
                    "Add '# JUSTIFICATION: <reason>' on the previous line.",
                ),
            )
            return

        # Check for banned phrases
        for banned in self.BANNED_PHRASES:
            if banned in justification_content:
                self.add_message(
                    "anti-bypass-violation",
                    line=lineno,
                    args=(
                        f"Banned justification for {forbidden}",
                        (f"The justification '{banned}' is lazy/invalid. Provide a real architectural reason."),
                    ),
                )
                break
