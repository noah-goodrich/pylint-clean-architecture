"""Terminal reporter implementation - lives in infrastructure (imports adapters)."""

from collections import defaultdict
from typing import TYPE_CHECKING, TypedDict, cast

if TYPE_CHECKING:
    from excelsior_architect.domain.config import ConfigurationLoader
    from excelsior_architect.domain.entities import (
        ArchitecturalHealthReport,
        AuditResult,
        LinterResult,
        ViolationWithFixInfo,
    )
    from excelsior_architect.domain.protocols import (
        LinterAdapterProtocol,
        RawLogPort,
        TelemetryPort,
    )

from excelsior_architect.infrastructure.adapters.linter_adapters import (
    ExcelsiorAdapter,
    MypyAdapter,
)
from excelsior_architect.infrastructure.adapters.ruff_adapter import RuffAdapter
from excelsior_architect.infrastructure.services.guidance_service import (
    GuidanceService,
)
from excelsior_architect.infrastructure.services.rule_analysis import (
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
    """Terminal reporter using stellar_ui_kit for audit tables. Implements AnalysisRendererProtocol."""

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

    def render_status(self, message: str, level: str = "info") -> None:
        """Render a status message (routes to telemetry). Implements AnalysisRendererProtocol."""
        self._telemetry.step(message)

    def render_health_report(
        self,
        report: "ArchitecturalHealthReport",
        format: str = "terminal",
        mode: str = "standard",
    ) -> None:
        """Render full architectural health report: score, layer health, systemic findings, action plan."""
        if format == "json":
            import json as _json
            print(_json.dumps(report.to_dict(), indent=2))
            return
        if format == "markdown":
            self._render_health_report_markdown(report)
            return
        from stellar_ui_kit import ColumnDefinition, ReportSchema

        # ── 1. Score Banner ──
        score = report.overall_score
        portability = report.portability_assessment
        gate = report.blocking_gate or "none"
        self._telemetry.step("")
        self._telemetry.step("=" * 64)
        self._telemetry.step(
            f"  ARCHITECTURAL HEALTH SCORE: {score}/100   Portability: {portability}   Blocking gate: {gate}")
        self._telemetry.step("=" * 64)

        # ── 2. Layer Health ──
        if report.layer_health:
            rows: list[dict[str, object]] = []
            for lh in sorted(report.layer_health, key=lambda x: x.violation_density, reverse=True):
                rows.append({
                    "layer": lh.layer,
                    "files": str(lh.file_count),
                    "violations": str(lh.violation_count),
                    "density": f"{lh.violation_density:.1f}",
                })
            schema = ReportSchema(
                title="Layer Health (sorted by violation density). Full paths in JSON.",
                columns=[
                    ColumnDefinition(header="Layer", key="layer"),
                    ColumnDefinition(header="Files", key="files"),
                    ColumnDefinition(header="Violations", key="violations"),
                    ColumnDefinition(header="Density", key="density"),
                ],
            )
            self.reporter.generate_report(rows, schema)

        # ── 3. Systemic Findings (sorted by priority) ──
        if report.findings:
            sorted_findings = sorted(
                report.findings,
                key=lambda f: (-f.score.priority, -f.violation_count),
            )
            rows = []
            for rank, f in enumerate(sorted_findings, 1):
                sev_label = f.severity_label.upper()
                rec = ""
                if f.pattern_recommendation:
                    rec = f"{f.pattern_recommendation.pattern}: {f.pattern_recommendation.rationale}"
                what_wrong = f.root_cause[:80] + \
                    ("..." if len(f.root_cause) > 80 else "")
                learn = (
                    f.learn_more[:50] + "...") if len(f.learn_more) > 50 else f.learn_more
                rows.append({
                    "rank": str(rank),
                    "severity": sev_label,
                    "priority": f"{f.score.priority:.1f}",
                    "finding": f.title,
                    "what_wrong": what_wrong,
                    "violations": str(f.violation_count),
                    "scope": f"{len(f.affected_files)} files",
                    "recommendation": rec[:90] + ("..." if len(rec) > 90 else "") if rec else "-",
                    "learn_more": learn or "-",
                })
            schema = ReportSchema(
                title=f"Systemic Findings ({len(report.findings)} root causes). Full paths in JSON.",
                columns=[
                    ColumnDefinition(header="Rank", key="rank"),
                    ColumnDefinition(header="Sev", key="severity"),
                    ColumnDefinition(header="Score", key="priority"),
                    ColumnDefinition(header="Finding", key="finding"),
                    ColumnDefinition(header="What's Wrong", key="what_wrong"),
                    ColumnDefinition(header="#", key="violations"),
                    ColumnDefinition(header="Scope", key="scope"),
                    ColumnDefinition(header="Recommendation",
                                     key="recommendation"),
                    ColumnDefinition(header="Learn More", key="learn_more"),
                ],
            )
            self.reporter.generate_report(rows, schema)
            self._telemetry.step("")
            self._telemetry.step(
                "Legend — Priority score = (reach × impact × confidence) / (effort + 0.1)")
            self._telemetry.step(
                "  Reach: % of project files affected (0–100). Impact: rule weight 1–10. Confidence: true-positive likelihood 0–1.")
            self._telemetry.step(
                "  Effort: fix effort 1–5 (1=auto, 5=architectural). Higher score = fix first. Full paths in JSON artifacts.")
            self._telemetry.step("")
            if mode == "eli5":
                sorted_findings = sorted(
                    report.findings,
                    key=lambda f: (-f.score.priority, -f.violation_count),
                )
                for rank, f in enumerate(sorted_findings, 1):
                    if f.eli5_description:
                        self._telemetry.step(
                            f"  [{rank}] {f.title}: Why it matters — {f.eli5_description}")
                self._telemetry.step("")

        # ── 4. Action Plan (pattern recommendations) ──
        if report.pattern_recommendations:
            self._telemetry.step("")
            self._telemetry.step(
                "ACTION PLAN — Prioritized Pattern Recommendations")
            self._telemetry.step("-" * 64)
            for i, rec in enumerate(report.pattern_recommendations, 1):
                related = ", ".join(
                    rec.related_violations) if rec.related_violations else "-"
                self._telemetry.step(
                    f"  {i}. Apply {rec.pattern} ({rec.category})")
                self._telemetry.step(f"     Trigger: {rec.trigger}")
                self._telemetry.step(f"     Rationale: {rec.rationale}")
                self._telemetry.step(f"     How: {rec.example_fix}")
                self._telemetry.step(
                    f"     Fixes: {related}  |  Affected: {len(rec.affected_files)} files (see JSON for paths)")
                self._telemetry.step("")

        # ── 5. Estimated Impact Summary ──
        total_violations = sum(f.violation_count for f in report.findings)
        fixable_by_pattern = sum(
            f.violation_count for f in report.findings if f.pattern_recommendation
        )
        if total_violations > 0 and fixable_by_pattern > 0:
            pct = (fixable_by_pattern / total_violations) * 100
            self._telemetry.step(
                f"Implementing the above recommendations addresses ~{fixable_by_pattern} of {total_violations} violations (~{pct:.0f}% of total).")
        self._telemetry.step("")

    def _render_health_report_markdown(self, report: "ArchitecturalHealthReport") -> None:
        """Output health report as markdown tables."""
        gate = report.blocking_gate or "none"
        self._telemetry.step("")
        self._telemetry.step(
            f"## Architectural Health: {report.overall_score}/100")
        self._telemetry.step(
            f"Portability: {report.portability_assessment} | Blocking gate: {gate}")
        self._telemetry.step("")
        if report.layer_health:
            self._telemetry.step("### Layer Health")
            self._telemetry.step("| Layer | Files | Violations | Density |")
            self._telemetry.step("|-------|-------|------------|--------|")
            for lh in sorted(report.layer_health, key=lambda x: x.violation_density, reverse=True):
                self._telemetry.step(
                    f"| {lh.layer} | {lh.file_count} | {lh.violation_count} | {lh.violation_density:.1f} |")
            self._telemetry.step("")
        if report.findings:
            sorted_findings = sorted(
                report.findings, key=lambda f: (-f.score.priority, -f.violation_count))
            self._telemetry.step("### Systemic Findings")
            self._telemetry.step(
                "| Rank | Sev | Score | Finding | What's Wrong | # | Scope | Recommendation | Learn More |")
            self._telemetry.step(
                "|------|-----|-------|---------|--------------|---|-------|----------------|------------|")
            for rank, f in enumerate(sorted_findings, 1):
                rec = ""
                if f.pattern_recommendation:
                    rec = (f.pattern_recommendation.pattern + ": " +
                           f.pattern_recommendation.rationale)[:40].replace("|", ",")
                title_s = f.title[:20].replace("|", ",")
                root_s = f.root_cause[:30].replace("\n", " ").replace("|", ",")
                learn_s = f.learn_more[:25].replace("|", ",")
                self._telemetry.step(
                    f"| {rank} | {f.severity_label.upper()} | {f.score.priority:.1f} | {title_s} | {root_s}... | {f.violation_count} | {len(f.affected_files)} files | {rec} | {learn_s} |"
                )
            self._telemetry.step("")
            self._telemetry.step(
                "**Legend**: Priority = (reach × impact × confidence) / (effort + 0.1). Higher = fix first.")
        self._telemetry.step("")

    def render_violations(
        self, violations: list["ViolationWithFixInfo"]
    ) -> None:
        """Render violation list. Implements AnalysisRendererProtocol."""
        if not violations:
            self.render_status("No violations.", "info")
            return
        from stellar_ui_kit import ColumnDefinition, ReportSchema
        rows: list[dict[str, object]] = []
        for v in violations[:100]:
            rows.append({
                "code": v.code,
                "message": v.message[:60] + "..." if len(v.message) > 60 else v.message,
                "location": v.location[:50] + "..." if len(v.location) > 50 else v.location,
                "fix": "Comment" if v.comment_only else ("Auto" if v.fixable else "Manual"),
            })
        schema = ReportSchema(
            title="Violations",
            columns=[
                ColumnDefinition(header="Code", key="code"),
                ColumnDefinition(header="Fix?", key="fix"),
                ColumnDefinition(header="Message", key="message"),
                ColumnDefinition(header="Location", key="location"),
            ],
        )
        self.reporter.generate_report(rows, schema)

    def report_audit(
        self, audit_result: "AuditResult", view: str = "by_code"
    ) -> None:
        """Print audit tables for all linters. view: 'by_code' or 'by_file'."""
        if audit_result.is_blocked():
            linter_name = (
                audit_result.blocking_gate.upper()
                if audit_result.blocking_gate else "Unknown"
            )
            self.render_status("\n" + "=" * 60, "warning")
            self.render_status(
                f"AUDIT BLOCKED: Resolve {linter_name} violations before proceeding to Architectural Governance.",
                "warning",
            )
            self.render_status("=" * 60 + "\n", "warning")
            if audit_result.blocking_gate:
                entry = self._BLOCKED_REPORTERS.get(audit_result.blocking_gate)
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
                from typing import Any
                from typing import cast as type_cast
                self.reporter.generate_report(
                    type_cast(list[dict[str, Any]], self._process_results_by_file(
                        audit_result.mypy_results)),
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
                    # type: ignore[arg-type]
                    audit_result.mypy_results, mypy_adapter),
                mypy_schema
            )
        else:
            self.render_status(
                "\nNo Type Integrity violations detected.", "info")

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
                    # type: ignore[arg-type]
                    audit_result.excelsior_results, excelsior_adapter),
                excelsior_schema,
            )
        else:
            self.render_status(
                "\nNo Architectural violations detected.", "info")

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
            if audit_result.ruff_results and ruff_adapter:
                self.reporter.generate_report(
                    self._process_results(
                        # type: ignore[arg-type]
                        audit_result.ruff_results, ruff_adapter),
                    ruff_schema,
                )
            else:
                self.render_status(
                    "\nNo Code Quality violations detected.", "info")

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
        rows: list[FileResultRow] = []
        for file_path, code_counts in by_file.items():
            total = sum(code_counts.values())
            parts = sorted(code_counts.items(), key=lambda x: -x[1])
            breakdown = ", ".join(f"{c}: {n}" for c, n in parts)
            row: FileResultRow = {"file": file_path, "total": total,
                                  "breakdown": breakdown}
            rows.append(row)
        return sorted(rows, key=lambda x: x["total"], reverse=True)

    def _process_results(
        self, results: list["LinterResult"], adapter: "LinterAdapterProtocol"
    ) -> list[ResultRow]:
        """Build table rows with count and fixability."""
        from excelsior_architect.domain.entities import LinterResult
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
                locations=sorted(set(all_locations))
            )
            processed_results.append(consolidated)

        for r in processed_results:
            d: dict[str, object] = dict(r.to_dict())
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
            from typing import Any
            from typing import cast as type_cast
            self.reporter.generate_report(
                type_cast(list[dict[str, Any]], self._process_results_by_file(
                    audit_result.ruff_results)),
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
            # type: ignore[arg-type]
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
            from typing import Any
            from typing import cast as type_cast
            self.reporter.generate_report(
                type_cast(list[dict[str, Any]], self._process_results_by_file(
                    audit_result.mypy_results)),
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
            # type: ignore[arg-type]
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
            from typing import Any
            from typing import cast as type_cast
            self.reporter.generate_report(
                type_cast(list[dict[str, Any]], self._process_results_by_file(
                    audit_result.excelsior_results)),
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
                # type: ignore[arg-type]
                audit_result.excelsior_results, excelsior_adapter),
            excelsior_schema,
        )
