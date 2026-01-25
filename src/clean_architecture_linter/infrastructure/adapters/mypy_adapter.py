import os
import re
import subprocess
import sys
from collections import defaultdict
from typing import Dict, List

from clean_architecture_linter.domain.entities import LinterResult
from clean_architecture_linter.domain.protocols import LinterAdapterProtocol


class MypyAdapter(LinterAdapterProtocol):
    """Adapter for mypy output."""

    def gather_results(self, target_path: str) -> List[LinterResult]:
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
            return self._parse_output(result.stdout)
        except Exception as e:
            # JUSTIFICATION: Error message wrapping requires explicit list creation.
            return [LinterResult("MYPY_ERROR", str(e), [])]

    def _parse_output(self, output: str) -> List[LinterResult]:
        # Structure: {error_code: {"message": str, "locations": set}}
        collected: Dict[str, Dict[str, object]] = defaultdict(
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
            sorted_locations = sorted(list(locations_set)) if isinstance(
                locations_set, set) else []
            results.append(LinterResult(
                code, str(data["message"]), sorted_locations))

        return results

    def supports_autofix(self) -> bool:
        """Check if this linter supports automatic fixing."""
        return False

    def get_fixable_rules(self) -> List[str]:
        """Return list of rule codes that can be auto-fixed."""
        return []  # Mypy does not support auto-fixing

    def get_manual_fix_instructions(self, rule_code: str) -> str:
        """Readable, step-by-step guidance for juniors and AI."""
        manual_instructions = {
            "type-arg": (
                "Add an explicit type annotation. Example: x: int = 1. "
                "Use typing.List, Dict, Optional, etc. when needed."
            ),
            "arg-type": (
                "Make the argument type match the function signature. "
                "Add a type cast (e.g. cast(...)) if the value is correct but mypy cannot infer it."
            ),
            "return-value": (
                "Ensure the return value matches the declared return type. "
                "Fix the implementation or update the return type hint."
            ),
            "assignment": (
                "Ensure the assigned value matches the variable's type. "
                "Change the value, add a cast, or fix the variable's annotation."
            ),
            "no-untyped-def": (
                "Add type annotations to all parameters and the return type. "
                "Example: def f(x: int) -> str: ..."
            ),
            "no-untyped-call": (
                "The function being called lacks type annotations. "
                "Add types to that function's parameters and return value."
            ),
            "var-annotated": (
                "Add a type annotation to the variable. "
                "Example: my_var: List[str] = []"
            ),
            "union-attr": (
                "Use a type guard before accessing attributes. "
                "Example: if isinstance(x, Foo): x.bar  # mypy knows x is Foo here."
            ),
            "attr-defined": (
                "The attribute is not defined on the type. "
                "Check spelling, or add the attribute to the class definition."
            ),
        }
        default: str = "See Mypy docs: https://mypy.readthedocs.io/ Fix types at the reported location."
        return manual_instructions.get(rule_code, default)
