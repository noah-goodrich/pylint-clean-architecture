import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

from clean_architecture_linter.domain.entities import LinterResult
from clean_architecture_linter.domain.protocols import LinterAdapterProtocol
from clean_architecture_linter.infrastructure.services.guidance_service import (
    GuidanceService,
)


class ImportLinterAdapter(LinterAdapterProtocol):
    """Adapter for Import Linter output."""

    LINTER = "import_linter"
    DEFAULT_RULE_CODE = "contract"

    def __init__(self, guidance_service: GuidanceService) -> None:
        self._guidance = guidance_service

    def gather_results(
        self,
        target_path: str,
        select_only: Optional[list[str]] = None,
    ) -> list[LinterResult]:
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
            state: dict = {"current_contract": "", "results": results}
            for line in text.splitlines():
                for pattern, handler_name in self._PARSE_LINE_HANDLERS:
                    if pattern in line:
                        getattr(self, handler_name)(line, state)
                        break

        return results

    _PARSE_LINE_HANDLERS: list[tuple[str, str]] = [
        ("Broken contract", "_handle_broken_contract_line"),
        ("is not allowed to import", "_handle_import_violation_line"),
    ]

    def _handle_broken_contract_line(self, line: str, state: dict) -> None:
        state["current_contract"] = line.strip()

    def _handle_import_violation_line(self, line: str, state: dict) -> None:
        state["results"].append(
            LinterResult(
                "IL001",
                f"{state['current_contract']}: {line.strip()}",
                [],
            )
        )

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
        """Readable, step-by-step guidance for juniors and AI (from registry when available)."""
        instructions = self._guidance.get_manual_instructions(
            self.LINTER, self.DEFAULT_RULE_CODE
        )
        if instructions and instructions.strip():
            return instructions
        return (
            "Remove or refactor the import that breaks the contract. "
            "1) Check pyproject.toml [tool.importlinter] for defined contracts. "
            "2) Move the imported code to an allowed layer, or invert the dependency (e.g. use a Port). "
            "3) Ensure the importing module lives in a layer that may depend on the imported module."
        )
