"""Use Case: Check Audit - Orchestrate linter execution and return audit results."""

from typing import TYPE_CHECKING, List

from clean_architecture_linter.domain.entities import AuditResult, LinterResult
from clean_architecture_linter.domain.protocols import LinterAdapterProtocol, TelemetryPort

if TYPE_CHECKING:
    from clean_architecture_linter.domain.config import ConfigurationLoader


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

    def execute(self, target_path: str) -> AuditResult:
        """
        Execute gated sequential audit: Ruff → Mypy → Excelsior.

        Stops execution if a prior linter finds violations (blocking gate).

        Args:
            target_path: Path to audit

        Returns:
            AuditResult containing violations from executed linters.
            blocked_by field indicates which linter blocked execution (if any).
        """
        self.telemetry.step(
            f"Starting Gated Sequential Audit for: {target_path}"
        )

        # Pass 1: Ruff (Code Hygiene) - Must pass before proceeding
        ruff_results: List[LinterResult] = []
        if self.config_loader.ruff_enabled:
            self.telemetry.step("Pass 1: Running Code Quality Checks (Source: Ruff)...")
            ruff_results = self.ruff_adapter.gather_results(target_path)
            if ruff_results:
                self.telemetry.step("⚠️  Audit Blocked: Ruff violations detected.")
                return AuditResult(
                    ruff_results=ruff_results,
                    ruff_enabled=True,
                    blocked_by="ruff",
                )

        # Pass 2: Mypy (Type Integrity) - Must pass before proceeding
        self.telemetry.step("Pass 2: Gathering Type Integrity violations (Source: Mypy)...")
        mypy_results = self.mypy_adapter.gather_results(target_path)
        if mypy_results:
            self.telemetry.step("⚠️  Audit Blocked: Mypy violations detected.")
            return AuditResult(
                ruff_results=ruff_results,
                mypy_results=mypy_results,
                ruff_enabled=self.config_loader.ruff_enabled,
                blocked_by="mypy",
            )

        # Pass 3: Excelsior (Architectural Governance) - Only runs if prior passes succeeded
        self.telemetry.step(
            "Pass 3: Gathering Architectural violations (Source: Pylint/Excelsior)..."
        )
        excelsior_results = self.excelsior_adapter.gather_results(target_path)

        return AuditResult(
            ruff_results=ruff_results,
            mypy_results=mypy_results,
            excelsior_results=excelsior_results,
            ruff_enabled=self.config_loader.ruff_enabled,
            blocked_by=None,
        )
