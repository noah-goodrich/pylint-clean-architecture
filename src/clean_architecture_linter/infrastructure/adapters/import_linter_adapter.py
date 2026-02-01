import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

from clean_architecture_linter.domain.entities import LinterResult
from clean_architecture_linter.domain.protocols import LinterAdapterProtocol


class ImportLinterAdapter(LinterAdapterProtocol):
    """Adapter for Import Linter output."""

    def gather_results(self, target_path: str) -> list[LinterResult]:
        """Run import-linter and gather results."""
        # Note: import-linter looks for pyproject.toml [tool.importlinter] in cwd.
        # It doesn't take a target path; we run from project root.
        try:
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

    def _parse_output(self, output: str) -> list[LinterResult]:
        results: list[LinterResult] = []
        text = output or ""

        # Format 1: "No matches for ignored import X -> Y" (import-linter layers contract)
        # The import can span lines: "X -> \nY" or be on one line.
        no_matches_re = re.compile(
            r"No matches for ignored import\s+([\w.]+)\s*->\s*([\w.]+)",
            re.DOTALL,
        )
        for m in no_matches_re.finditer(text):
            importer = m.group(1).strip().rstrip(".")
            importee = m.group(2).strip().rstrip(".")
            results.append(
                LinterResult(
                    "IL001",
                    f"Layer violation: {importer} imports {importee} (not allowed)",
                    [],
                )
            )

        # Format 2: "Broken contract" + "X is not allowed to import Y" (older format)
        if not results and "Broken contract" in text:
            lines = text.splitlines()
            current_contract: str = ""
            for line in lines:
                if "Broken contract" in line:
                    current_contract = line.strip()
                elif "is not allowed to import" in line:
                    results.append(
                        LinterResult("IL001", f"{current_contract}: {line.strip()}", [])
                    )

        return results

    def supports_autofix(self) -> bool:
        """Check if this linter supports automatic fixing."""
        return False

    def get_fixable_rules(self) -> list[str]:
        """Return list of rule codes that can be auto-fixed."""
        return []  # Import-Linter does not support auto-fixing

    def apply_fixes(
        self,
        target_path: Path,
        select_only: Optional[list[str]] = None,
    ) -> bool:
        """Import-Linter does not support automatic fixes."""
        return False

    def get_manual_fix_instructions(self, rule_code: str) -> str:
        """Readable, step-by-step guidance for juniors and AI."""
        return (
            "Remove or refactor the import that breaks the contract. "
            "1) Check pyproject.toml [tool.importlinter] for defined contracts. "
            "2) Move the imported code to an allowed layer, or invert the dependency (e.g. use a Port). "
            "3) Ensure the importing module lives in a layer that may depend on the imported module."
        )
