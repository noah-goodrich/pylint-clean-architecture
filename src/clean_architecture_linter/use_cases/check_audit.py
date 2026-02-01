"""Use Case: Check Audit - Orchestrate linter execution and return audit results."""

from typing import TYPE_CHECKING

from clean_architecture_linter.domain.entities import AuditResult, LinterResult
from clean_architecture_linter.domain.protocols import LinterAdapterProtocol, TelemetryPort
from clean_architecture_linter.infrastructure.adapters.ruff_adapter import (
    RUFF_CODE_QUALITY_SELECT,
    RUFF_IMPORT_TYPING_SELECT,
)

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
        Execute gated sequential audit: Layers first, then style/typing, then code quality.

        Order: 1) Import-linter (layer contracts), 2) Ruff import/typing, 3) Mypy,
        4) Excelsior (architectural), 5) Ruff code quality. Stops at first blocking violation.

        Args:
            target_path: Path to audit

        Returns:
            AuditResult containing violations from executed linters.
            blocked_by field indicates which linter blocked execution (if any).
        """
        self.telemetry.step(
            f"Starting Gated Sequential Audit for: {target_path}"
        )

        ruff_results: list[LinterResult] = []

        # Pass 1: Import-linter (layer / dependency contracts) - first
        self.telemetry.step(
            "Pass 1: Checking layer contracts (Source: Import-Linter)..."
        )
        import_linter_results = self.import_linter_adapter.gather_results(
            target_path
        )
        if import_linter_results:
            self.telemetry.step(
                "⚠️  Audit Blocked: Import-linter contract violations detected."
            )
            return AuditResult(
                import_linter_results=import_linter_results,
                ruff_results=ruff_results,
                ruff_enabled=self.config_loader.ruff_enabled,
                blocked_by="import_linter",
            )

        # Pass 2: Ruff import & typing (I, UP, B)
        if self.config_loader.ruff_enabled:
            self.telemetry.step(
                "Pass 2: Running Import & Typing checks (Source: Ruff I, UP, B)..."
            )
            ruff_import_typing = self.ruff_adapter.gather_results(
                target_path, select_only=RUFF_IMPORT_TYPING_SELECT
            )
            ruff_results.extend(ruff_import_typing)
            if ruff_import_typing:
                self.telemetry.step(
                    "⚠️  Audit Blocked: Ruff import/typing violations detected."
                )
                return AuditResult(
                    import_linter_results=import_linter_results,
                    ruff_results=ruff_results,
                    ruff_enabled=True,
                    blocked_by="ruff",
                )

        # Pass 3: Mypy (type integrity)
        self.telemetry.step(
            "Pass 3: Gathering Type Integrity violations (Source: Mypy)..."
        )
        mypy_results = self.mypy_adapter.gather_results(target_path)
        if mypy_results:
            self.telemetry.step("⚠️  Audit Blocked: Mypy violations detected.")
            return AuditResult(
                import_linter_results=import_linter_results,
                ruff_results=ruff_results,
                mypy_results=mypy_results,
                ruff_enabled=self.config_loader.ruff_enabled,
                blocked_by="mypy",
            )

        # Pass 4: Excelsior (architectural)
        self.telemetry.step(
            "Pass 4: Gathering Architectural violations (Source: Pylint/Excelsior)..."
        )
        excelsior_results = self.excelsior_adapter.gather_results(target_path)
        if excelsior_results:
            self.telemetry.step(
                "⚠️  Audit Blocked: Excelsior architectural violations detected."
            )
            return AuditResult(
                import_linter_results=import_linter_results,
                ruff_results=ruff_results,
                mypy_results=mypy_results,
                excelsior_results=excelsior_results,
                ruff_enabled=self.config_loader.ruff_enabled,
                blocked_by="excelsior",
            )

        # Pass 5: Ruff code quality (E, F, W, C90, ...) - last
        if self.config_loader.ruff_enabled:
            self.telemetry.step(
                "Pass 5: Running Code Quality checks (Source: Ruff E, F, W, C90, ...)..."
            )
            ruff_code_quality = self.ruff_adapter.gather_results(
                target_path, select_only=RUFF_CODE_QUALITY_SELECT
            )
            ruff_results.extend(ruff_code_quality)
            if ruff_code_quality:
                self.telemetry.step(
                    "⚠️  Audit Blocked: Ruff code quality violations detected."
                )
                return AuditResult(
                    import_linter_results=import_linter_results,
                    ruff_results=ruff_results,
                    mypy_results=mypy_results,
                    excelsior_results=excelsior_results,
                    ruff_enabled=True,
                    blocked_by="ruff",
                )

        return AuditResult(
            import_linter_results=import_linter_results,
            ruff_results=ruff_results,
            mypy_results=mypy_results,
            excelsior_results=excelsior_results,
            ruff_enabled=self.config_loader.ruff_enabled,
            blocked_by=None,
        )
