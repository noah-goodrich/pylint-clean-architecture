"""Anti-Bypass Guard checks (W9501)."""

import tokenize

from pylint.checkers import BaseTokenChecker


class BypassChecker(BaseTokenChecker):
    """W9501: Anti-Bypass Guard enforcement."""

    name = "clean-arch-bypass"
    msgs = {
        "W9501": (
            "Anti-Bypass Violation: %s detected. %s",
            "anti-bypass-violation",
            "Module-level disables or unjustified complexity disables are forbidden.",
        ),
    }

    FORBIDDEN_DISABLES = {
        "too-many-arguments",
        "too-many-instance-attributes",
        "too-many-positional-arguments",
    }

    def process_tokens(self, tokens):
        """Scan tokens for forbidden pylint: disable comments."""
        lines = {}
        for tok_type, tok_string, start, _, line_content in tokens:
            if tok_type == tokenize.COMMENT:
                lineno = start[0]
                lines[lineno] = line_content
                self._check_comment(tok_string, lineno, line_content, lines)

    def _check_comment(self, tok_string, lineno, line_content, lines):
        """Check a single comment for bypass violations."""
        if "pylint:" not in tok_string or "disable" not in tok_string:
            return

        # 1. Check for module-level (global) disable
        # We consider a disable global if it's in the first 20 lines and on a standalone line.
        is_standalone = not line_content.split("#")[0].strip()
        if lineno < 20 and is_standalone:
            self.add_message(
                "anti-bypass-violation",
                line=lineno,
                args=("Global pylint: disable", "Fix the issue instead."),
            )

        # 2. Check for specific forbidden disables
        for forbidden in self.FORBIDDEN_DISABLES:
            if forbidden in tok_string:
                self._check_justification(forbidden, lineno, lines)

    BANNED_PHRASES = {
        "internal helper",
        "detailed arguments",
        "passing the linter",
    }

    def _check_justification(self, forbidden, lineno, lines):
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
                        (
                            f"The justification '{banned}' is lazy/invalid. "
                            "Provide a real architectural reason."
                        ),
                    ),
                )
                break
