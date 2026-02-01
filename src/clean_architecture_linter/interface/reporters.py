"""Interface for audit reporting."""

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from clean_architecture_linter.domain.entities import AuditResult, LinterResult
    from clean_architecture_linter.infrastructure.services.rule_analysis import RuleFixabilityService


class AuditReporter(Protocol):
    """Protocol for reporting audit results."""

    def report_audit(self, audit_result: "AuditResult") -> None:
        """Report audit results to the user."""
        ...


class TerminalAuditReporter:
    """Terminal reporter using stellar_ui_kit for audit tables."""

    def __init__(self, rule_fixability_service: "RuleFixabilityService") -> None:
        from stellar_ui_kit import TerminalReporter
        self.reporter = TerminalReporter()
        self.rule_fixability_service = rule_fixability_service

    def report_audit(self, audit_result: "AuditResult") -> None:
        """Print audit tables for all linters."""
        # Check for blocking gate
        if audit_result.is_blocked():
            linter_name = audit_result.blocked_by.upper() if audit_result.blocked_by else "Unknown"
            print("\n" + "=" * 60)
            print(f"🚫 AUDIT BLOCKED: Resolve {linter_name} violations before proceeding to Architectural Governance.")
            print("=" * 60 + "\n")
            # Still show the blocking linter's results
            if audit_result.blocked_by == "import_linter" and audit_result.import_linter_results:
                self._report_import_linter_results(audit_result)
            elif audit_result.blocked_by == "ruff" and audit_result.ruff_results:
                self._report_ruff_results(audit_result)
            elif audit_result.blocked_by == "mypy" and audit_result.mypy_results:
                self._report_mypy_results(audit_result)
            elif audit_result.blocked_by == "excelsior" and audit_result.excelsior_results:
                self._report_excelsior_results(audit_result)
            return

        from stellar_ui_kit import ColumnDefinition, ReportSchema

        from clean_architecture_linter.infrastructure.adapters.linter_adapters import (
            ExcelsiorAdapter,
            MypyAdapter,
        )
        from clean_architecture_linter.infrastructure.adapters.ruff_adapter import RuffAdapter

        mypy_adapter = MypyAdapter()
        excelsior_adapter = ExcelsiorAdapter()
        ruff_adapter = RuffAdapter(telemetry=None) if audit_result.ruff_enabled else None

        # Mypy table
        if audit_result.mypy_results:
            mypy_schema = ReportSchema(
                title="[MYPY] Type Integrity Audit",
                columns=[
                    ColumnDefinition(header="Error Code", key="code", style="#00EEFF"),
                    ColumnDefinition(header="Count", key="count", style="bold #007BFF"),
                    ColumnDefinition(header="Fix?", key="fix"),
                    ColumnDefinition(header="Message", key="message"),
                ],
                header_style="bold #007BFF",
            )
            self.reporter.generate_report(
                self._process_results(audit_result.mypy_results, mypy_adapter),
                mypy_schema
            )
        else:
            print("\n✅ No Type Integrity violations detected.")

        # Excelsior table
        if audit_result.excelsior_results:
            excelsior_schema = ReportSchema(
                title="[EXCELSIOR] Architectural Governance Audit",
                columns=[
                    ColumnDefinition(header="Rule ID", key="code", style="#C41E3A"),
                    ColumnDefinition(header="Count", key="count", style="bold #007BFF"),
                    ColumnDefinition(header="Fix?", key="fix"),
                    ColumnDefinition(header="Violation Description", key="message"),
                ],
                header_style="bold #F9A602",
            )
            self.reporter.generate_report(
                self._process_results(audit_result.excelsior_results, excelsior_adapter),
                excelsior_schema,
            )
        else:
            print("\n✅ No Architectural violations detected.")

        # Import-Linter table
        if audit_result.import_linter_results:
            il_schema = ReportSchema(
                title="[IMPORT-LINTER] Package Boundary Audit",
                columns=[
                    ColumnDefinition(header="Rule ID", key="code", style="#7B68EE"),
                    ColumnDefinition(header="Fix?", key="fix"),
                    ColumnDefinition(header="Contract Violation", key="message"),
                ],
                header_style="bold #7B68EE",
            )
            il_rows = []
            for r in audit_result.import_linter_results:
                d = dict(r.to_dict())
                d["fix"] = "⚠️ Manual"  # Import-Linter has no autofix
                il_rows.append(d)
            self.reporter.generate_report(il_rows, il_schema)

        # Ruff table
        if audit_result.ruff_enabled and ruff_adapter:
            ruff_schema = ReportSchema(
                title="[RUFF] Code Quality Audit",
                columns=[
                    ColumnDefinition(header="Rule ID", key="code", style="#FFA500"),
                    ColumnDefinition(header="Count", key="count", style="bold #007BFF"),
                    ColumnDefinition(header="Fix?", key="fix"),
                    ColumnDefinition(header="Issue", key="message"),
                ],
                header_style="bold #FFA500",
            )
            if audit_result.ruff_results:
                self.reporter.generate_report(
                    self._process_results(audit_result.ruff_results, ruff_adapter),
                    ruff_schema,
                )
            else:
                print("\n✅ No Code Quality violations detected.")

    def _process_results(
        self, results: list["LinterResult"], adapter: object
    ) -> list[dict]:
        """Build table rows with count and fixability."""
        out = []
        for r in results:
            d: dict[str, object] = dict(r.to_dict())
            d["count"] = len(r.locations) if r.locations else 1

            # Determine fix type: Auto-fixable, Comment-only, or Manual
            is_fixable = self.rule_fixability_service.is_rule_fixable(adapter, r.code)
            is_comment_only = False
            if hasattr(adapter, "is_comment_only_rule"):
                is_comment_only = adapter.is_comment_only_rule(r.code)

            if is_comment_only:
                d["fix"] = "💬 Comment"
            elif is_fixable:
                d["fix"] = "✅ Auto"
            else:
                d["fix"] = "⚠️ Manual"

            out.append(d)
        return sorted(
            out,
            key=lambda x: int(x["count"]) if isinstance(x["count"], int) else 0,
            reverse=True,
        )

    def _report_ruff_results(self, audit_result: "AuditResult") -> None:
        """Report Ruff results when audit is blocked."""
        from stellar_ui_kit import ColumnDefinition, ReportSchema

        from clean_architecture_linter.infrastructure.adapters.ruff_adapter import RuffAdapter

        if not audit_result.ruff_results:
            return

        ruff_adapter = RuffAdapter(telemetry=None)
        ruff_schema = ReportSchema(
            title="[RUFF] Code Quality Audit",
            columns=[
                ColumnDefinition(header="Rule ID", key="code", style="#FFA500"),
                ColumnDefinition(header="Count", key="count", style="bold #007BFF"),
                ColumnDefinition(header="Fix?", key="fix"),
                ColumnDefinition(header="Issue", key="message"),
            ],
            header_style="bold #FFA500",
        )
        self.reporter.generate_report(
            self._process_results(audit_result.ruff_results, ruff_adapter),
            ruff_schema,
        )

    def _report_mypy_results(self, audit_result: "AuditResult") -> None:
        """Report Mypy results when audit is blocked."""
        from stellar_ui_kit import ColumnDefinition, ReportSchema

        from clean_architecture_linter.infrastructure.adapters.linter_adapters import MypyAdapter

        if not audit_result.mypy_results:
            return

        mypy_adapter = MypyAdapter()
        mypy_schema = ReportSchema(
            title="[MYPY] Type Integrity Audit",
            columns=[
                ColumnDefinition(header="Error Code", key="code", style="#00EEFF"),
                ColumnDefinition(header="Count", key="count", style="bold #007BFF"),
                ColumnDefinition(header="Fix?", key="fix"),
                ColumnDefinition(header="Message", key="message"),
            ],
            header_style="bold #007BFF",
        )
        self.reporter.generate_report(
            self._process_results(audit_result.mypy_results, mypy_adapter),
            mypy_schema
        )

    def _report_import_linter_results(self, audit_result: "AuditResult") -> None:
        """Report Import-Linter results when audit is blocked."""
        from stellar_ui_kit import ColumnDefinition, ReportSchema

        if not audit_result.import_linter_results:
            return

        il_schema = ReportSchema(
            title="[IMPORT-LINTER] Package Boundary Audit",
            columns=[
                ColumnDefinition(header="Rule ID", key="code", style="#7B68EE"),
                ColumnDefinition(header="Fix?", key="fix"),
                ColumnDefinition(header="Contract Violation", key="message"),
            ],
            header_style="bold #7B68EE",
        )
        il_rows = []
        for r in audit_result.import_linter_results:
            d = dict(r.to_dict())
            d["fix"] = "⚠️ Manual"  # Import-Linter has no autofix
            il_rows.append(d)
        self.reporter.generate_report(il_rows, il_schema)

    def _report_excelsior_results(self, audit_result: "AuditResult") -> None:
        """Report Excelsior results when audit is blocked."""
        from stellar_ui_kit import ColumnDefinition, ReportSchema

        from clean_architecture_linter.infrastructure.adapters.linter_adapters import (
            ExcelsiorAdapter,
        )

        if not audit_result.excelsior_results:
            return

        excelsior_adapter = ExcelsiorAdapter()
        excelsior_schema = ReportSchema(
            title="[EXCELSIOR] Architectural Governance Audit",
            columns=[
                ColumnDefinition(header="Rule ID", key="code", style="#C41E3A"),
                ColumnDefinition(header="Count", key="count", style="bold #007BFF"),
                ColumnDefinition(header="Fix?", key="fix"),
                ColumnDefinition(header="Violation Description", key="message"),
            ],
            header_style="bold #F9A602",
        )
        self.reporter.generate_report(
            self._process_results(audit_result.excelsior_results, excelsior_adapter),
            excelsior_schema,
        )
