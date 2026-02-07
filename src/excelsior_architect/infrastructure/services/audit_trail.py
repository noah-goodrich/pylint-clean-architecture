"""Service for persisting audit trails."""

import json
from collections import defaultdict
from datetime import datetime
from typing import TYPE_CHECKING

from excelsior_architect.domain.entities import (
    ArchitecturalHealthReport,
    AuditResult,
    AuditTrail,
    AuditTrailSummary,
    AuditTrailViolations,
    LinterResult,
    ViolationWithFixInfo,
)
from excelsior_architect.domain.protocols import (
    ArtifactStorageProtocol,
    AuditTrailServiceProtocol,
    LinterAdapterProtocol,
    RawLogPort,
    TelemetryPort,
)
from excelsior_architect.infrastructure.adapters.linter_adapters import (
    ExcelsiorAdapter,
    ImportLinterAdapter,
    MypyAdapter,
)
from excelsior_architect.infrastructure.adapters.ruff_adapter import RuffAdapter
from excelsior_architect.infrastructure.services.guidance_service import (
    GuidanceService,
)
from excelsior_architect.infrastructure.services.rule_analysis import (
    RuleFixabilityService,
)

if TYPE_CHECKING:
    from excelsior_architect.domain.config import ConfigurationLoader


class AuditTrailService(AuditTrailServiceProtocol):
    """Service for saving audit trails to .excelsior directory. Implements AnalysisPersistenceProtocol."""

    def __init__(
        self,
        telemetry: TelemetryPort,
        rule_fixability_service: RuleFixabilityService,
        artifact_storage: ArtifactStorageProtocol,
        config_loader: "ConfigurationLoader",
        guidance_service: GuidanceService,
        raw_log_port: RawLogPort,
    ) -> None:
        self.telemetry = telemetry
        self.rule_fixability_service = rule_fixability_service
        self.artifact_storage = artifact_storage
        self._config_loader = config_loader
        self._guidance = guidance_service
        self._raw_log_port = raw_log_port

    def save_report(
        self, report: ArchitecturalHealthReport, source: str | None = None
    ) -> None:
        """Save full health report (e.g. last_audit.json). Implements AnalysisPersistenceProtocol."""
        key = f"{source}/last_audit.json" if source else "last_audit.json"
        content = json.dumps(report.to_dict(), indent=2)
        self.artifact_storage.write_artifact(key, content)
        self.telemetry.step(f"Health report persisted to: {key}")

    def _build_ai_handover_from_report(
        self, report: ArchitecturalHealthReport
    ) -> dict[str, object]:
        """Build AI handover JSON from ArchitecturalHealthReport (systemic_findings, health_score, etc.)."""
        violations_by_rule: dict[str,
                                 list[dict[str, object]]] = defaultdict(list)
        for v in report.violation_details:
            violations_by_rule[v.code].append({
                "code": v.code,
                "message": v.message,
                "locations": v.locations,
                "fixable": v.fixable,
                "comment_only": v.comment_only,
                "manual_instructions": v.manual_instructions,
            })
        layer_health_dict: dict[str, dict[str, object]] = {
            lh.layer: lh.to_dict() for lh in report.layer_health
        }
        return {
            "version": "2.0.0",
            "health_score": report.overall_score,
            "blocking_gate": report.blocking_gate,
            "portability_assessment": report.portability_assessment,
            "systemic_findings": [f.to_dict() for f in report.findings],
            "pattern_recommendations": [p.to_dict() for p in report.pattern_recommendations],
            "layer_health": layer_health_dict,
            "violations_by_rule": violations_by_rule,
            "violation_details": [v.to_dict() for v in report.violation_details],
        }

    def save_audit_trail(
        self, audit_result: AuditResult, source: str | None = None
    ) -> None:
        """
        Save audit results to .excelsior directory for human/AI review.

        Args:
            audit_result: Result of the audit.
            source: Command that produced the audit ('check', 'fix', 'ai_workflow').
                     When set, files are under .excelsior/{source}/ (e.g. check/last_audit.json).
        """
        if source:
            json_key = f"{source}/last_audit.json"
            txt_key = f"{source}/last_audit.txt"
        else:
            json_key = "last_audit.json"
            txt_key = "last_audit.txt"

        # Build domain entity from audit result
        audit_trail = self._build_audit_trail(audit_result)

        json_content = json.dumps(audit_trail.to_dict(), indent=2)
        self.artifact_storage.write_artifact(json_key, json_content)

        txt_content = self._build_text_content(audit_result, audit_trail)
        self.artifact_storage.write_artifact(txt_key, txt_content)

        self.telemetry.step(
            f"💾 Audit Trail persisted to: {json_key} and {txt_key}")

    def _build_audit_trail(self, audit_result: AuditResult) -> AuditTrail:
        """Build domain AuditTrail entity from AuditResult."""
        mypy_adapter = MypyAdapter(
            raw_log_port=self._raw_log_port,
            guidance_service=self._guidance,
        )
        excelsior_adapter = ExcelsiorAdapter(
            config_loader=self._config_loader,
            raw_log_port=self._raw_log_port,
            guidance_service=self._guidance,
        )
        il_adapter = ImportLinterAdapter(guidance_service=self._guidance)
        ruff_adapter = (
            RuffAdapter(
                config_loader=self._config_loader,
                telemetry=self.telemetry,
                raw_log_port=self._raw_log_port,
                guidance_service=self._guidance,
            )
            if audit_result.ruff_enabled
            else None
        )

        summary = AuditTrailSummary(
            type_integrity=len(audit_result.mypy_results),
            architectural=len(audit_result.excelsior_results),
            contracts=len(audit_result.import_linter_results),
            code_quality=len(audit_result.ruff_results),
        )

        violations = AuditTrailViolations(
            type_integrity=self._build_violations_with_fix_info(
                audit_result.mypy_results, mypy_adapter
            ),
            architectural=self._build_violations_with_fix_info(
                audit_result.excelsior_results, excelsior_adapter
            ),
            contracts=self._build_violations_with_fix_info(
                audit_result.import_linter_results, il_adapter
            ),
            code_quality=(
                self._build_violations_with_fix_info(
                    audit_result.ruff_results, ruff_adapter)
                if ruff_adapter
                else []
            ),
        )

        return AuditTrail(
            version="2.0.0",
            timestamp=datetime.now().isoformat(),
            summary=summary,
            violations=violations,
        )

    def _build_violations_with_fix_info(
        self, results: list[LinterResult], adapter: LinterAdapterProtocol
    ) -> list[ViolationWithFixInfo]:
        """Build domain ViolationWithFixInfo entities from LinterResults."""
        from excelsior_architect.domain.entities import LinterResult
        violations = []

        # Consolidation for R0801: Group all duplicate-code results into a single entry
        r0801_results = [r for r in results if r.code == "R0801"]
        other_results = [r for r in results if r.code != "R0801"]

        if r0801_results:
            all_locations = []
            for r in r0801_results:
                all_locations.extend(r.locations)

            consolidated = LinterResult(
                code="R0801",
                message="Duplicate code detected across multiple files. See locations for details.",
                locations=sorted(set(all_locations))
            )
            other_results.append(consolidated)

        for result in other_results:
            fixable = self.rule_fixability_service.is_rule_fixable(
                adapter, result.code)
            comment_only = (
                adapter.is_comment_only_rule(result.code)
                if hasattr(adapter, "is_comment_only_rule")
                else False
            )
            manual_instructions = None
            if not fixable and hasattr(adapter, "get_manual_fix_instructions"):
                manual_instructions = adapter.get_manual_fix_instructions(
                    result.code)

            violation = ViolationWithFixInfo(
                code=result.code,
                message=result.message,
                location=", ".join(
                    result.locations) if result.locations else "N/A",
                locations=result.locations,
                fixable=fixable,
                manual_instructions=manual_instructions,
                comment_only=comment_only,
            )
            violations.append(violation)
        return violations

    def _build_text_content(
        self, audit_result: AuditResult, audit_trail: AuditTrail
    ) -> str:
        """Build human-readable text format of audit trail."""
        lines = [
            "=== EXCELSIOR v2 AUDIT LOG ===",
            (
                f"Summary: {audit_trail.summary.architectural} Architectural, "
                f"{audit_trail.summary.type_integrity} Type Integrity, "
                f"{audit_trail.summary.contracts} Contracts, "
                f"{audit_trail.summary.code_quality} Code Quality"
            ),
        ]

        self._append_violations_section(
            lines, "ARCHITECTURAL VIOLATIONS", audit_trail.violations.architectural
        )
        self._append_violations_section(
            lines, "TYPE INTEGRITY VIOLATIONS", audit_trail.violations.type_integrity
        )
        self._append_violations_section(
            lines, "CONTRACT VIOLATIONS", audit_trail.violations.contracts, include_locations=False
        )
        if audit_result.ruff_enabled:
            self._append_violations_section(
                lines, "CODE QUALITY VIOLATIONS (RUFF)", audit_trail.violations.code_quality
            )

        return "\n".join(lines) + "\n"

    def _append_violations_section(
        self,
        lines: list[str],
        title: str,
        violations: list[ViolationWithFixInfo],
        include_locations: bool = True,
    ) -> None:
        """Append a violations section to lines list."""
        lines.append(f"\n--- {title} ---")
        for violation in violations:
            if violation.comment_only:
                label = "💬 Comment"
            elif violation.fixable:
                label = "✅ Auto-fixable"
            else:
                label = "⚠️ Manual fix required"
            lines.append(f"[{violation.code}] {label}")
            lines.append(f"  {violation.message}")
            if include_locations and violation.locations:
                for loc in violation.locations:
                    lines.append(f"  - {loc}")
            if not violation.fixable and violation.manual_instructions:
                lines.append(
                    f"  How to fix (juniors & AI): {violation.manual_instructions}")

    def save_ai_handover(
        self,
        audit_result_or_report: AuditResult | ArchitecturalHealthReport,
        source: str | None = None,
    ) -> str:
        """
        Generate and save AI handover bundle. Implements both AuditTrailServiceProtocol
        (AuditResult) and AnalysisPersistenceProtocol (ArchitecturalHealthReport).

        Args:
            audit_result_or_report: Audit result or architectural health report.
            source: Command that produced the audit ('check', 'fix', 'ai_workflow').

        Returns:
            Logical key of the generated JSON artifact (e.g. check/ai_handover.json)
        """
        if isinstance(audit_result_or_report, ArchitecturalHealthReport):
            key = f"{source}/ai_handover.json" if source else "ai_handover.json"
            handover = self._build_ai_handover_from_report(
                audit_result_or_report)
            content = json.dumps(handover, indent=2)
            self.artifact_storage.write_artifact(key, content)
            self.telemetry.step(f"AI handover persisted to: {key}")
            return key
        audit_result = audit_result_or_report
        json_key = f"{source}/ai_handover.json" if source else "ai_handover.json"

        handover = self._build_ai_handover(audit_result)
        json_content = json.dumps(handover, indent=2)
        self.artifact_storage.write_artifact(json_key, json_content)

        self.telemetry.step(f"🤖 AI Handover bundle saved to: {json_key}")
        return json_key

    def append_audit_history(
        self,
        audit_result: AuditResult,
        source: str,
        json_path: str,
        txt_path: str,
    ) -> None:
        """
        Append one record to the audit history file (append-only, never overwrite).

        Helps debug gaps between check and fix by viewing history of what each run found.
        Each line is a single JSON object (NDJSON).
        """
        history_key = "audit_history.jsonl"

        total = (
            len(audit_result.ruff_results)
            + len(audit_result.mypy_results)
            + len(audit_result.excelsior_results)
            + len(audit_result.import_linter_results)
        )
        record = {
            "timestamp": datetime.now().isoformat(),
            "source": source,
            "blocked_by": audit_result.blocked_by,
            "total_violations": total,
            "ruff": len(audit_result.ruff_results),
            "mypy": len(audit_result.mypy_results),
            "excelsior": len(audit_result.excelsior_results),
            "import_linter": len(audit_result.import_linter_results),
            "snapshot_json": json_path,
            "snapshot_txt": txt_path,
        }
        line = json.dumps(record) + "\n"
        self.artifact_storage.append_artifact(history_key, line)
        self.telemetry.step(
            f"📜 Audit history appended to: {history_key}"
        )

    def _build_ai_handover(self, audit_result: AuditResult) -> dict[str, object]:
        """Build AI handover JSON structure."""
        mypy_adapter = MypyAdapter(
            raw_log_port=self._raw_log_port,
            guidance_service=self._guidance,
        )
        excelsior_adapter = ExcelsiorAdapter(
            config_loader=self._config_loader,
            raw_log_port=self._raw_log_port,
            guidance_service=self._guidance,
        )
        il_adapter = ImportLinterAdapter(guidance_service=self._guidance)
        ruff_adapter = (
            RuffAdapter(
                config_loader=self._config_loader,
                telemetry=self.telemetry,
                raw_log_port=self._raw_log_port,
                guidance_service=self._guidance,
            )
            if audit_result.ruff_enabled
            else None
        )

        # Group violations by rule code
        violations_by_rule: dict[str,
                                 list[dict[str, object]]] = defaultdict(list)
        files_with_comments: dict[str, list[int]] = defaultdict(list)

        # Category -> linter name for registry rule_id (e.g. mypy.no-any-return, excelsior.W9006)
        category_to_linter: dict[str, str] = {
            "code_quality": "ruff",
            "type_integrity": "mypy",
            "architectural": "excelsior",
            "contracts": "import_linter",
        }

        # Process all violations
        all_results = [
            (audit_result.ruff_results, ruff_adapter, "code_quality"),
            (audit_result.mypy_results, mypy_adapter, "type_integrity"),
            (audit_result.excelsior_results, excelsior_adapter, "architectural"),
            (audit_result.import_linter_results, il_adapter, "contracts"),
        ]

        for results, adapter, category in all_results:
            if not adapter or not results:
                continue

            linter = category_to_linter.get(category, category)

            # Consolidation for R0801 in AI Handover
            current_results = results
            if category == "architectural":
                r0801_results = [r for r in results if r.code == "R0801"]
                if r0801_results:
                    from excelsior_architect.domain.entities import LinterResult
                    other_results = [r for r in results if r.code != "R0801"]
                    all_locations = []
                    for r in r0801_results:
                        all_locations.extend(r.locations)
                    consolidated = LinterResult(
                        code="R0801",
                        message="Duplicate code detected across multiple files. See locations for details.",
                        locations=sorted(set(all_locations))
                    )
                    current_results = [*other_results, consolidated]

            for result in current_results:
                if not adapter:
                    continue
                fixable = self.rule_fixability_service.is_rule_fixable(
                    adapter, result.code)
                comment_only = (
                    adapter.is_comment_only_rule(result.code)
                    if hasattr(adapter, "is_comment_only_rule")
                    else False
                )
                manual_instructions = None
                if hasattr(adapter, "get_manual_fix_instructions"):
                    manual_instructions = adapter.get_manual_fix_instructions(
                        result.code)
                if manual_instructions is None and self._guidance:
                    manual_instructions = self._guidance.get_manual_instructions(
                        linter, result.code)

                # rule_id for registry lookup (e.g. mypy.no-any-return, excelsior.W9006)
                rule_id = f"{linter}.{result.code}"

                # Ready-to-paste directive for an AI to fix this single violation
                locations_str = ", ".join(
                    result.locations) if result.locations else "N/A"
                prompt_fragment = (
                    f"Fix [{rule_id}]: {result.message}\n"
                    f"Location(s): {locations_str}\n"
                    f"Instructions: {manual_instructions or 'See registry for this rule_id.'}"
                )

                # Extract file paths and line numbers
                for location in result.locations:
                    location_parts = location.split(":")
                    if len(location_parts) >= 2:
                        file_path = location_parts[0]
                        try:
                            line_num = int(location_parts[1])
                            if comment_only:
                                files_with_comments[file_path].append(line_num)
                        except ValueError:
                            pass

                violation_data = {
                    "rule_id": rule_id,
                    "code": result.code,
                    "message": result.message,
                    "locations": result.locations,
                    "category": category,
                    "fixable": fixable,
                    "comment_only": comment_only,
                    "manual_instructions": manual_instructions,
                    "prompt_fragment": prompt_fragment,
                }
                violations_by_rule[result.code].append(violation_data)

        # Build next steps guidance
        next_steps = self._build_next_steps(audit_result, violations_by_rule)

        # Unique rule_ids for plan workflow (e.g. mypy.union-attr, excelsior.W9006)
        rule_ids_set: set[str] = set()
        for entries in violations_by_rule.values():
            for v in entries:
                rid = v.get("rule_id")
                if isinstance(rid, str):
                    rule_ids_set.add(rid)
        rule_ids = sorted(rule_ids_set)

        return {
            "version": "1.0.0",
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_violations": sum(len(v) for v in violations_by_rule.values()),
                "rules_with_violations": len(violations_by_rule),
                "files_with_governance_comments": len(files_with_comments),
                "blocked_by": audit_result.blocked_by,
            },
            "rule_ids": rule_ids,
            "violations_by_rule": dict(violations_by_rule),
            "files_with_governance_comments": {
                file_path: sorted(set(line_nums))
                for file_path, line_nums in files_with_comments.items()
            },
            "next_steps": next_steps,
        }

    def _build_next_steps(
        self, audit_result: AuditResult, violations_by_rule: dict[str, list[dict[str, object]]]
    ) -> list[str]:
        """Build next steps guidance for AI."""
        steps = []

        if audit_result.is_blocked():
            steps.append(
                f"⚠️  BLOCKED: Audit was blocked by {audit_result.blocked_by}. "
                f"Fix upstream violations first."
            )
            steps.append(
                "   For each violation type, run: excelsior plan <rule_id> "
                "(rule_ids are in this handover). Then fix guided by the generated plan."
            )
            return steps

        # Check for auto-fixable violations
        auto_fixable_rules = [
            code for code, violations in violations_by_rule.items()
            if any(v.get("fixable", False) for v in violations)
        ]
        if auto_fixable_rules:
            steps.append(
                f"✅ {len(auto_fixable_rules)} rule(s) are auto-fixable. "
                f"Run 'excelsior fix' to apply automatic fixes (or plan first for per-rule plans)."
            )
            # W9015: type hints are only auto-injected when type can be inferred
            if "W9015" in auto_fixable_rules:
                steps.append(
                    "   W9015 (missing type hint): Run 'excelsior fix' first. "
                    "Any locations that remain need manual type hints (inference failed for those parameters)."
                )

        # Check for comment-only violations (governance comments already injected)
        comment_only_rules = [
            code for code, violations in violations_by_rule.items()
            if any(v.get("comment_only", False) for v in violations)
        ]
        if comment_only_rules:
            steps.append(
                f"💬 {len(comment_only_rules)} rule(s) have governance comments injected. "
                f"Look for EXCELSIOR comment blocks in source files to guide manual fixes."
            )
            steps.append(
                "   Search for 'EXCELSIOR' in files listed under 'files_with_governance_comments'."
            )

        # Check for manual-fix violations
        manual_fix_rules = [
            code for code, violations in violations_by_rule.items()
            if not any(v.get("fixable", False) for v in violations)
            and not any(v.get("comment_only", False) for v in violations)
        ]
        if manual_fix_rules:
            steps.append(
                f"⚠️  {len(manual_fix_rules)} rule(s) require manual fixes. "
                f"Run 'excelsior plan <rule_id>' for each (see handover 'rule_ids'); "
                f"then fix guided by the generated plan. See 'manual_instructions' in violation data."
            )

        if not steps:
            steps.append("✅ No violations found! Codebase is clean.")

        return steps
