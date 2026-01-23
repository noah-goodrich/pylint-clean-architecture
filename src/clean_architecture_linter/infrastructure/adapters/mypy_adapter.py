import re
import subprocess
import os
import sys
from collections import defaultdict
from typing import List, Dict, Set
from clean_architecture_linter.domain.protocols import LinterAdapterProtocol
from clean_architecture_linter.domain.entities import LinterResult

class MypyAdapter(LinterAdapterProtocol):
    """Adapter for mypy output."""

    def gather_results(self, target_path: str) -> List[LinterResult]:
        """Run mypy and gather results."""
        env = os.environ.copy()
        try:
            result = subprocess.run(
                [sys.executable, "-m", "mypy", target_path, "--strict"],
                capture_output = True,
                text = True,
                check = False,
                env=env,
            )
            return self._parse_output(result.stdout)
        except Exception as e:
            # JUSTIFICATION: Error message wrapping requires explicit list creation.
            return [LinterResult("MYPY_ERROR", str(e), [])]

    def _parse_output(self, output: str) -> List[LinterResult]:
        # Structure: {error_code: {"message": str, "locations": set}}
        collected: Dict[str, Dict[str, object]] = defaultdict(lambda: {"message": "", "locations": set()})

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
            sorted_locations = sorted(list(locations_set)) if isinstance(locations_set, set) else []
            results.append(LinterResult(code, str(data["message"]), sorted_locations))

        return results
