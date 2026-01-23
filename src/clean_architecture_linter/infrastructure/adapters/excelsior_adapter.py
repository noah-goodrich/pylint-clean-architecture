import re
import subprocess
import os
import sys
from collections import defaultdict
from typing import List, Dict, Set
from clean_architecture_linter.domain.protocols import LinterAdapterProtocol
from clean_architecture_linter.domain.entities import LinterResult

class ExcelsiorAdapter(LinterAdapterProtocol):
    """Adapter for Pylint Clean Architecture output."""

    def gather_results(self, target_path: str) -> List[LinterResult]:
        """Run pylint with Clean Architecture and gather results."""
        env = os.environ.copy()
        env["PYTHONPATH"] = "src"
        try:
            # We use --output-format=text to get standard output
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pylint",
                    target_path,
                    "--load-plugins=clean_architecture_linter",
                    "--msg-template={path}:{line}: {msg_id}: {msg} ({symbol})",
                ],
                env=env,
                capture_output = True,
                text = True,
                check = False,
            )
            return self._parse_output(result.stdout)
        except Exception as e:
            # JUSTIFICATION: Error message wrapping requires explicit list creation.
            return [LinterResult("EXCELSIOR_ERROR", str(e), [])]

    def _parse_output(self, output: str) -> List[LinterResult]:
        # Structure: {msg_id: {"message": str, "locations": set}}
        collected: Dict[str, Dict[str, object]] = defaultdict(lambda: {"message": "", "locations": set()})
        # Pattern: path:line: msg_id: msg (symbol)
        pattern = re.compile(r"^(.*?):(\d+): (.*?): (.*)$")

        for line in output.splitlines():
            match = pattern.match(line)
            if match:
                # JUSTIFICATION: Regex match groups access is permitted for standard library utilities.
                file_path, line_num, msg_id, message = match.groups()
                location = f"{file_path}:{line_num}"

                # JUSTIFICATION: Type casting is necessary due to defaultdict(dict) structure.
                entry = collected[msg_id]
                entry["message"] = message
                # JUSTIFICATION: Type-safe access to the locations set.
                locations_set = entry["locations"]
                if isinstance(locations_set, set):
                    locations_set.add(location)

        results = []
        for msg_id, data in collected.items():
            # JUSTIFICATION: Converting set to sorted list for deterministic reporting.
            locations_set = data["locations"]
            sorted_locations = sorted(list(locations_set)) if isinstance(locations_set, set) else []
            results.append(LinterResult(msg_id, str(data["message"]), sorted_locations))

        return results
