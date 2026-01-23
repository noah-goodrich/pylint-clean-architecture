import subprocess
import os
import sys
from typing import List
from clean_architecture_linter.domain.entities import LinterResult
from clean_architecture_linter.domain.protocols import LinterAdapterProtocol

class ImportLinterAdapter(LinterAdapterProtocol):
    """Adapter for Import Linter output."""

    def gather_results(self, target_path: str) -> List[LinterResult]:
        """Run import-linter and gather results."""
        # Note: import-linter usually looks for a configuration file (.importlinter or setup.cfg)
        # It doesn't typically take a target path as a CLI arg in the same way,
        # but we can try to run it.
        try:
            # Try lint-imports first, then fallback to python -m
            cmd = ["lint-imports"]
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=False,
                )
            except FileNotFoundError:
                result = subprocess.run(
                    [sys.executable, "-m", "importlinter", "lint"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
            return self._parse_output(result.stdout)
        except Exception as e:
            return [LinterResult("IMPORT_LINTER_ERROR", str(e), [])]

    def _parse_output(self, output: str) -> List[LinterResult]:
        results = []
        # Import Linter output is usually human-readable text describing contract failures.
        # This is a very basic parser for its "Broken contract" sections.
        if "Broken contract" in output:
            lines = output.splitlines()
            current_contract: str = ""
            for line in lines:
                if "Broken contract" in line:
                    current_contract = line.strip()
                elif "is not allowed to import" in line:
                    results.append(LinterResult("IL001", f"{current_contract}: {line.strip()}", []))

        return results
