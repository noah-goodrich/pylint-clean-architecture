import subprocess
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

    def supports_autofix(self) -> bool:
        """Check if this linter supports automatic fixing."""
        return False

    def get_fixable_rules(self) -> List[str]:
        """Return list of rule codes that can be auto-fixed."""
        return []  # Import-Linter does not support auto-fixing

    def get_manual_fix_instructions(self, rule_code: str) -> str:
        """Readable, step-by-step guidance for juniors and AI."""
        return (
            "Remove or refactor the import that breaks the contract. "
            "1) Check pyproject.toml [tool.importlinter] for defined contracts. "
            "2) Move the imported code to an allowed layer, or invert the dependency (e.g. use a Port). "
            "3) Ensure the importing module lives in a layer that may depend on the imported module."
        )
