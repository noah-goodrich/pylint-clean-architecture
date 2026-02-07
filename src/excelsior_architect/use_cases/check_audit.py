"""Use Case: Check Audit - Orchestrate linter execution and return audit results."""

from typing import TYPE_CHECKING

from excelsior_architect.domain.constants import (
    RUFF_CODE_QUALITY_SELECT,
    RUFF_IMPORT_TYPING_SELECT,
)
from excelsior_architect.domain.entities import AuditResult, LinterResult
from excelsior_architect.domain.protocols import LinterAdapterProtocol, TelemetryPort

if TYPE_CHECKING:
    from excelsior_architect.domain.config import ConfigurationLoader


class CheckAuditUseCase:
    """Orchestrate the running of all linters and return audit results."""

    def __init__(
        self,
        mypy_adapter: LinterAdapterProtocol,
        excelsior_adapter: LinterAdapterProtocol,
        import_linter_adapter: LinterAdapterProtocol,
        ruff_adapter: LinterAdapterProtocol,
        telemetry: TelemetryPort,
        config_loader: "ConfigurationLoader",
    ) -> None:
        self.mypy_adapter = mypy_adapter
        self.excelsior_adapter = excelsior_adapter
        self.import_linter_adapter = import_linter_adapter
        self.ruff_adapter = ruff_adapter
        self.telemetry = telemetry
        self.config_loader = config_loader

    def execute(self, target_path: str, mode: str = "check") -> AuditResult:
        """
        Execute full audit: run all tools, gather all results, then set blocking_gate.

        All five passes always run. blocking_gate indicates which gate would block CI
        (first in priority: import_linter > ruff > mypy > excelsior).

        Args:
            target_path: Path to audit
            mode: "check" (gated exit code for CI) or "health" (full analysis, no gating)

        Returns:
            AuditResult with all violations from all linters and blocking_gate set.
        """
        self.telemetry.step(
            f"Starting Full Audit for: {target_path} (mode={mode})"
        )

        # Pass 1: Import-linter (layer / dependency contracts)
        self.telemetry.step(
            "Pass 1: Checking layer contracts (Source: Import-Linter)..."
        )
        import_linter_results = self.import_linter_adapter.gather_results(
            target_path
        )

        # Pass 2: Ruff import & typing (I, UP, B)
        ruff_results: list[LinterResult] = []
        if self.config_loader.ruff_enabled:
            self.telemetry.step(
                "Pass 2: Running Import & Typing checks (Source: Ruff I, UP, B)..."
            )
            ruff_import_typing = self.ruff_adapter.gather_results(
                target_path, select_only=RUFF_IMPORT_TYPING_SELECT
            )
            ruff_results.extend(ruff_import_typing)

        # Pass 3: Mypy (type integrity)
        self.telemetry.step(
            "Pass 3: Gathering Type Integrity violations (Source: Mypy)..."
        )
        mypy_results = self.mypy_adapter.gather_results(target_path)

        # Pass 4: Excelsior (architectural)
        self.telemetry.step(
            "Pass 4: Gathering Architectural violations (Source: Pylint/Excelsior)..."
        )
        excelsior_results = self.excelsior_adapter.gather_results(target_path)

        # Pass 5: Ruff code quality (E, F, W, C90, ...)
        if self.config_loader.ruff_enabled:
            self.telemetry.step(
                "Pass 5: Running Code Quality checks (Source: Ruff E, F, W, C90, ...)..."
            )
            ruff_code_quality = self.ruff_adapter.gather_results(
                target_path, select_only=RUFF_CODE_QUALITY_SELECT
            )
            ruff_results.extend(ruff_code_quality)

        blocking_gate = self._determine_blocking_gate(
            import_linter_results=import_linter_results,
            ruff_results=ruff_results,
            mypy_results=mypy_results,
            excelsior_results=excelsior_results,
        )
        if blocking_gate:
            self.telemetry.step(
                f"Audit would be blocked by: {blocking_gate} (all results gathered)."
            )

        return AuditResult(
            import_linter_results=import_linter_results,
            ruff_results=ruff_results,
            mypy_results=mypy_results,
            excelsior_results=excelsior_results,
            ruff_enabled=self.config_loader.ruff_enabled,
            mode=mode,
            blocking_gate=blocking_gate,
        )

    def _determine_blocking_gate(
        self,
        import_linter_results: list[LinterResult],
        ruff_results: list[LinterResult],
        mypy_results: list[LinterResult],
        excelsior_results: list[LinterResult],
    ) -> str | None:
        """Return which gate would block CI (first in priority order), or None."""
        if import_linter_results:
            return "import_linter"
        if ruff_results:
            return "ruff"
        if mypy_results:
            return "mypy"
        if excelsior_results:
            return "excelsior"
        return None
