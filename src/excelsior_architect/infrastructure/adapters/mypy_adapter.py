import os
import re
import subprocess
import sys
from collections import defaultdict
from typing import TYPE_CHECKING

from excelsior_architect.domain.entities import LinterResult
from excelsior_architect.domain.protocols import LinterAdapterProtocol
from excelsior_architect.infrastructure.services.guidance_service import (
    GuidanceService,
)

if TYPE_CHECKING:
    from excelsior_architect.domain.protocols import RawLogPort


class MypyAdapter(LinterAdapterProtocol):
    """Adapter for mypy output."""

    LINTER = "mypy"

    def __init__(
        self,
        raw_log_port: "RawLogPort",
        guidance_service: GuidanceService,
    ) -> None:
        self._raw_log_port = raw_log_port
        self._guidance = guidance_service

    def gather_results(
        self,
        target_path: str,
        select_only: list[str] | None = None,
    ) -> list[LinterResult]:
        """Run mypy and gather results."""
        env = os.environ.copy()
        try:
            result = subprocess.run(
                [sys.executable, "-m", "mypy", target_path, "--strict"],
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )
            self._raw_log_port.log_raw(
                "mypy",
                result.stdout or "",
                result.stderr or "",
            )
            # Treat "mypy not installed" or similar run failures as MYPY_ERROR so audit blocks.
            stderr_text = result.stderr or ""
            if result.returncode != 0:
                if "No module named mypy" in stderr_text or "ModuleNotFoundError" in stderr_text:
                    return [
                        LinterResult(
                            "MYPY_ERROR",
                            stderr_text.strip() or "mypy failed to run (non-zero exit).",
                            [],
                        )
                    ]

                # If mypy failed but we didn't get any parsed results from stdout,
                # we must report the error from stdout/stderr.
                results = self._parse_output(result.stdout)
                if not results:
                    error_msg = (result.stdout + "\n" + result.stderr).strip()
                    return [
                        LinterResult(
                            "MYPY_ERROR",
                            error_msg or f"mypy failed with exit code {result.returncode}",
                            [],
                        )
                    ]
                return results

            return self._parse_output(result.stdout)
        except Exception as e:
            # JUSTIFICATION: Error message wrapping requires explicit list creation.
            return [LinterResult("MYPY_ERROR", str(e), [])]

    def _parse_output(self, output: str) -> list[LinterResult]:
        # Structure: {error_code: {"message": str, "locations": set}}
        collected: dict[str, dict[str, object]] = defaultdict(
            lambda: {"message": "", "locations": set()})

        # Pattern: file:line: error: message [code]
        pattern = re.compile(r"^(.*?):(\d+): error: (.*?)  \[(.*?)\]$")

        for line in output.splitlines():
            match = pattern.match(line)
            if match:
                # JUSTIFICATION: Regex match groups access is permitted for standard library utilities.
                file_path, line_num, message, error_code = match.groups()
                location = f"{file_path}:{line_num}"

                entry = collected[error_code]
                entry["message"] = message
                locations_set = entry["locations"]
                if isinstance(locations_set, set):
                    locations_set.add(location)
            else:
                # Fallback for lines without error codes
                fallback_pattern = re.compile(r"^(.*?):(\d+): error: (.*)$")
                fallback_match = fallback_pattern.match(line)
                if fallback_match:
                    # JUSTIFICATION: Regex match groups access is permitted for standard library utilities.
                    file_path, line_num, message = fallback_match.groups()
                    location = f"{file_path}:{line_num}"
                    key: str = "MYPY"
                    entry = collected[key]
                    entry["message"] = message
                    locations_set = entry["locations"]
                    if isinstance(locations_set, set):
                        locations_set.add(location)

        results = []
        for code, data in collected.items():
            locations_set = data["locations"]
            sorted_locations = sorted(locations_set) if isinstance(
                locations_set, set) else []
            results.append(LinterResult(
                code, str(data["message"]), sorted_locations))

        return results

    def supports_autofix(self) -> bool:
        """Check if this linter supports automatic fixing."""
        return False

    def get_fixable_rules(self) -> list[str]:
        """Return list of rule codes that can be auto-fixed."""
        return []  # Mypy does not support auto-fixing

    def apply_fixes(
        self,
        target_path: str,
        select_only: list[str] | None = None,
    ) -> bool:
        """Mypy does not support automatic fixes."""
        return False

    def get_manual_fix_instructions(self, rule_code: str) -> str:
        """Readable, step-by-step guidance for juniors and AI (from registry when available)."""
        instructions = self._guidance.get_manual_instructions(
            self.LINTER, rule_code)
        if instructions and instructions.strip():
            return instructions
        default = "See Mypy docs: https://mypy.readthedocs.io/ Fix types at the reported location."
        fallback: dict[str, str] = {
            "type-arg": "Add an explicit type annotation. Example: x: int = 1. Use typing.List, Dict, Optional, etc. when needed.",
            "arg-type": "Make the argument type match the function signature. Add a type cast (e.g. cast(...)) if the value is correct but mypy cannot infer it.",
            "return-value": "Ensure the return value matches the declared return type. Fix the implementation or update the return type hint.",
            "assignment": "Ensure the assigned value matches the variable's type. Change the value, add a cast, or fix the variable's annotation.",
            "no-untyped-def": "Add type annotations to all parameters and the return type. Example: def f(x: int) -> str: ...",
            "no-untyped-call": "The function being called lacks type annotations. Add types to that function's parameters and return value.",
            "var-annotated": "Add a type annotation to the variable. Example: my_var: List[str] = []",
            "union-attr": "Use a type guard before accessing attributes. Example: if isinstance(x, Foo): x.bar  # mypy knows x is Foo here.",
            "attr-defined": "The attribute is not defined on the type. Check spelling, or add the attribute to the class definition.",
        }
        return fallback.get(rule_code, default)
