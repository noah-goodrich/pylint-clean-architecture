"""Terminal reporter implementation - lives in infrastructure (imports adapters)."""

from collections import defaultdict
from typing import TYPE_CHECKING, TypedDict, cast

if TYPE_CHECKING:
    from clean_architecture_linter.domain.config import ConfigurationLoader
    from clean_architecture_linter.domain.entities import AuditResult, LinterResult
    from clean_architecture_linter.domain.protocols import RawLogPort, TelemetryPort

from clean_architecture_linter.infrastructure.adapters.linter_adapters import (
    ExcelsiorAdapter,
    MypyAdapter,
)
from clean_architecture_linter.infrastructure.adapters.ruff_adapter import RuffAdapter
from clean_architecture_linter.infrastructure.services.guidance_service import (
    GuidanceService,
)
from clean_architecture_linter.infrastructure.services.rule_analysis import (
    RuleFixabilityService,
)


class FileResultRow(TypedDict):
    """Row for by-file view: file path, total count, code breakdown."""

    file: str
    total: int
    breakdown: str


class ResultRow(TypedDict):
    """Row for by-code view: linter result fields plus count and fix label."""

    code: str
    message: str
    location: str
    locations: list[str]
    count: int
    fix: str


class TerminalAuditReporter:
    """Terminal reporter using stellar_ui_kit for audit tables."""

    _BLOCKED_REPORTERS: dict[str, tuple[str, str]] = {
        "import_linter": ("import_linter_results", "_report_import_linter_results"),
        "ruff": ("ruff_results", "_report_ruff_results"),
        "mypy": ("mypy_results", "_report_mypy_results"),
        "excelsior": ("excelsior_results", "_report_excelsior_results"),
    }

    def __init__(
        self,
        rule_fixability_service: RuleFixabilityService,
        config_loader: "ConfigurationLoader",
        guidance_service: GuidanceService,
        raw_log_port: "RawLogPort",
        telemetry: "TelemetryPort",
    ) -> None:
        from stellar_ui_kit import TerminalReporter
        self.reporter = TerminalReporter()
        self.rule_fixability_service = rule_fixability_service
        self._config_loader = config_loader
        self._guidance = guidance_service
        self._raw_log_port = raw_log_port
        self._telemetry = telemetry

    def report_audit(
        self, audit_result: "AuditResult", view: str = "by_code"
    ) -> None:
        """Print audit tables for all linters. view: 'by_code' or 'by_file'."""
        if audit_result.is_blocked():
            linter_name = audit_result.blocked_by.upper(
            ) if audit_result.blocked_by else "Unknown"
            print("\n" + "=" * 60)
            print(
                f"🚫 AUDIT BLOCKED: Resolve {linter_name} violations before proceeding to Architectural Governance.")
            print("=" * 60 + "\n")
            entry = self._BLOCKED_REPORTERS.get(audit_result.blocked_by)
            if entry and getattr(audit_result, entry[0], None):
                getattr(self, entry[1])(audit_result, view=view)
            return

        from stellar_ui_kit import ColumnDefinition, ReportSchema

        mypy_adapter = MypyAdapter(
            raw_log_port=self._raw_log_port,
            guidance_service=self._guidance,
        )
        excelsior_adapter = ExcelsiorAdapter(
            config_loader=self._config_loader,
            raw_log_port=self._raw_log_port,
            guidance_service=self._guidance,
        )
        ruff_adapter = (
            RuffAdapter(
                config_loader=self._config_loader,
                telemetry=self._telemetry,
                raw_log_port=self._raw_log_port,
                guidance_service=self._guidance,
            )
            if audit_result.ruff_enabled
            else None
        )

        if audit_result.mypy_results:
            if view == "by_file":
                mypy_schema = ReportSchema(
                    title="[MYPY] Type Integrity Audit (by file)",
                    columns=[
                        ColumnDefinition(
                            header="File", key="file", style="#00EEFF"),
                        ColumnDefinition(
                            header="Total", key="total", style="bold #007BFF"),
                        ColumnDefinition(header="Error types",
                                         key="breakdown"),
                    ],
                    header_style="bold #007BFF",
                )
                self.reporter.generate_report(
                    self._process_results_by_file(audit_result.mypy_results),
                    mypy_schema,
                )
            else:
                mypy_schema = ReportSchema(
                    title="[MYPY] Type Integrity Audit",
                    columns=[
                        ColumnDefinition(header="Error Code",
                                         key="code", style="#00EEFF"),
                        ColumnDefinition(
                            header="Count", key="count", style="bold #007BFF"),
                        ColumnDefinition(header="Fix?", key="fix"),
                        ColumnDefinition(header="Message", key="message"),
                    ],
                    header_style="bold #007BFF",
                )
                self.reporter.generate_report(
                    self._process_results(
                        audit_result.mypy_results, mypy_adapter),
                    mypy_schema
                )
        else:
            print("\n✅ No Type Integrity violations detected.")

        if audit_result.excelsior_results:
            excelsior_schema = ReportSchema(
                title="[EXCELSIOR] Architectural Governance Audit",
                columns=[
                    ColumnDefinition(header="Rule ID",
                                     key="code", style="#C41E3A"),
                    ColumnDefinition(
                        header="Count", key="count", style="bold #007BFF"),
                    ColumnDefinition(header="Fix?", key="fix"),
                    ColumnDefinition(
                        header="Violation Description", key="message"),
                ],
                header_style="bold #F9A602",
            )
            self.reporter.generate_report(
                self._process_results(
                    audit_result.excelsior_results, excelsior_adapter),
                excelsior_schema,
            )
        else:
            print("\n✅ No Architectural violations detected.")

        if audit_result.import_linter_results:
            il_schema = ReportSchema(
                title="[IMPORT-LINTER] Package Boundary Audit",
                columns=[
                    ColumnDefinition(header="Rule ID",
                                     key="code", style="#7B68EE"),
                    ColumnDefinition(header="Fix?", key="fix"),
                    ColumnDefinition(
                        header="Contract Violation", key="message"),
                ],
                header_style="bold #7B68EE",
            )
            il_rows = []
            for r in audit_result.import_linter_results:
                d = dict(r.to_dict())
                d["fix"] = "⚠️ Manual"
                il_rows.append(d)
            self.reporter.generate_report(il_rows, il_schema)

        if audit_result.ruff_enabled and ruff_adapter:
            ruff_schema = ReportSchema(
                title="[RUFF] Code Quality Audit",
                columns=[
                    ColumnDefinition(header="Rule ID",
                                     key="code", style="#FFA500"),
                    ColumnDefinition(
                        header="Count", key="count", style="bold #007BFF"),
                    ColumnDefinition(header="Fix?", key="fix"),
                    ColumnDefinition(header="Issue", key="message"),
                ],
                header_style="bold #FFA500",
            )
            if audit_result.ruff_results:
                self.reporter.generate_report(
                    self._process_results(
                        audit_result.ruff_results, ruff_adapter),
                    ruff_schema,
                )
            else:
                print("\n✅ No Code Quality violations detected.")

    def _process_results_by_file(
        self, results: list["LinterResult"]
    ) -> list[FileResultRow]:
        """Group results by file: file, total, breakdown. Sorted by total descending."""
        by_file: dict[str, dict[str, int]] = defaultdict(
            lambda: defaultdict(int))
        for r in results:
            for loc in r.locations or ["<unknown>"]:
                file_path = loc.rsplit(":", 1)[0] if ":" in loc else loc
                by_file[file_path][r.code] += 1
        rows = []
        for file_path, code_counts in by_file.items():
            total = sum(code_counts.values())
            parts = sorted(code_counts.items(), key=lambda x: -x[1])
            breakdown = ", ".join(f"{c}: {n}" for c, n in parts)
            rows.append({"file": file_path, "total": total,
                        "breakdown": breakdown})
        return sorted(rows, key=lambda x: x["total"], reverse=True)

    def _process_results(
        self, results: list["LinterResult"], adapter: object
    ) -> list[ResultRow]:
        """Build table rows with count and fixability."""
        from clean_architecture_linter.domain.entities import LinterResult
        out: list[ResultRow] = []

        # Consolidation for R0801: Group all duplicate-code results into a single row
        r0801_results = [r for r in results if r.code == "R0801"]
        other_results = [r for r in results if r.code != "R0801"]

        processed_results = other_results
        if r0801_results:
            all_locations = []
            for r in r0801_results:
                all_locations.extend(r.locations)

            consolidated = LinterResult(
                code="R0801",
                message="Duplicate code detected across multiple files. See fix plan for details.",
                locations=sorted(list(set(all_locations)))
            )
            processed_results.append(consolidated)

        for r in processed_results:
            d = dict(r.to_dict())
            d["count"] = len(r.locations) if r.locations else 1
            is_fixable = self.rule_fixability_service.is_rule_fixable(
                adapter, r.code)
            is_comment_only = False
            if hasattr(adapter, "is_comment_only_rule"):
                is_comment_only = adapter.is_comment_only_rule(r.code)
            if is_comment_only:
                d["fix"] = "💬 Comment"
            elif is_fixable:
                d["fix"] = "✅ Auto"
            else:
                d["fix"] = "⚠️ Manual"
            out.append(cast(ResultRow, d))
        return sorted(
            out,
            key=lambda x: int(x["count"]) if isinstance(
                x["count"], int) else 0,
            reverse=True,
        )

    def _report_ruff_results(
        self, audit_result: "AuditResult", view: str = "by_code"
    ) -> None:
        if not audit_result.ruff_results:
            return
        from stellar_ui_kit import ColumnDefinition, ReportSchema

        if view == "by_file":
            ruff_schema = ReportSchema(
                title="[RUFF] Code Quality Audit (by file)",
                columns=[
                    ColumnDefinition(
                        header="File", key="file", style="#FFA500"),
                    ColumnDefinition(
                        header="Total", key="total", style="bold #007BFF"),
                    ColumnDefinition(header="Error types", key="breakdown"),
                ],
                header_style="bold #FFA500",
            )
            self.reporter.generate_report(
                self._process_results_by_file(audit_result.ruff_results),
                ruff_schema,
            )
            return
        ruff_adapter = RuffAdapter(
            config_loader=self._config_loader,
            telemetry=self._telemetry,
            raw_log_port=self._raw_log_port,
            guidance_service=self._guidance,
        )
        ruff_schema = ReportSchema(
            title="[RUFF] Code Quality Audit",
            columns=[
                ColumnDefinition(header="Rule ID",
                                 key="code", style="#FFA500"),
                ColumnDefinition(header="Count", key="count",
                                 style="bold #007BFF"),
                ColumnDefinition(header="Fix?", key="fix"),
                ColumnDefinition(header="Issue", key="message"),
            ],
            header_style="bold #FFA500",
        )
        self.reporter.generate_report(
            self._process_results(audit_result.ruff_results, ruff_adapter),
            ruff_schema,
        )

    def _report_mypy_results(
        self, audit_result: "AuditResult", view: str = "by_code"
    ) -> None:
        if not audit_result.mypy_results:
            return
        from stellar_ui_kit import ColumnDefinition, ReportSchema

        if view == "by_file":
            mypy_schema = ReportSchema(
                title="[MYPY] Type Integrity Audit (by file)",
                columns=[
                    ColumnDefinition(
                        header="File", key="file", style="#00EEFF"),
                    ColumnDefinition(
                        header="Total", key="total", style="bold #007BFF"),
                    ColumnDefinition(header="Error types", key="breakdown"),
                ],
                header_style="bold #007BFF",
            )
            self.reporter.generate_report(
                self._process_results_by_file(audit_result.mypy_results),
                mypy_schema,
            )
            return
        mypy_adapter = MypyAdapter(
            raw_log_port=self._raw_log_port,
            guidance_service=self._guidance,
        )
        mypy_schema = ReportSchema(
            title="[MYPY] Type Integrity Audit",
            columns=[
                ColumnDefinition(header="Error Code",
                                 key="code", style="#00EEFF"),
                ColumnDefinition(header="Count", key="count",
                                 style="bold #007BFF"),
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
        if not audit_result.import_linter_results:
            return
        from stellar_ui_kit import ColumnDefinition, ReportSchema

        il_schema = ReportSchema(
            title="[IMPORT-LINTER] Package Boundary Audit",
            columns=[
                ColumnDefinition(header="Rule ID",
                                 key="code", style="#7B68EE"),
                ColumnDefinition(header="Fix?", key="fix"),
                ColumnDefinition(header="Contract Violation", key="message"),
            ],
            header_style="bold #7B68EE",
        )
        il_rows = []
        for r in audit_result.import_linter_results:
            d = dict(r.to_dict())
            d["fix"] = "⚠️ Manual"
            il_rows.append(d)
        self.reporter.generate_report(il_rows, il_schema)

    def _report_excelsior_results(
        self, audit_result: "AuditResult", view: str = "by_code"
    ) -> None:
        if not audit_result.excelsior_results:
            return
        from stellar_ui_kit import ColumnDefinition, ReportSchema

        if view == "by_file":
            excelsior_schema = ReportSchema(
                title="[EXCELSIOR] Architectural Governance Audit (by file)",
                columns=[
                    ColumnDefinition(
                        header="File", key="file", style="#C41E3A"),
                    ColumnDefinition(
                        header="Total", key="total", style="bold #007BFF"),
                    ColumnDefinition(header="Error types", key="breakdown"),
                ],
                header_style="bold #F9A602",
            )
            self.reporter.generate_report(
                self._process_results_by_file(audit_result.excelsior_results),
                excelsior_schema,
            )
            return
        excelsior_adapter = ExcelsiorAdapter(
            config_loader=self._config_loader,
            raw_log_port=self._raw_log_port,
            guidance_service=self._guidance,
        )
        excelsior_schema = ReportSchema(
            title="[EXCELSIOR] Architectural Governance Audit",
            columns=[
                ColumnDefinition(header="Rule ID",
                                 key="code", style="#C41E3A"),
                ColumnDefinition(header="Count", key="count",
                                 style="bold #007BFF"),
                ColumnDefinition(header="Fix?", key="fix"),
                ColumnDefinition(
                    header="Violation Description", key="message"),
            ],
            header_style="bold #F9A602",
        )
        self.reporter.generate_report(
            self._process_results(
                audit_result.excelsior_results, excelsior_adapter),
            excelsior_schema,
        )
