"""Service for persisting audit trails."""

import json
from typing import List

from clean_architecture_linter.domain.entities import (
    AuditResult,
    AuditTrail,
    AuditTrailSummary,
    AuditTrailViolations,
    LinterResult,
    ViolationWithFixInfo,
)
from clean_architecture_linter.domain.protocols import FileSystemProtocol, TelemetryPort
from clean_architecture_linter.infrastructure.adapters.linter_adapters import (
    ExcelsiorAdapter,
    ImportLinterAdapter,
    MypyAdapter,
)
from clean_architecture_linter.infrastructure.adapters.ruff_adapter import RuffAdapter
from clean_architecture_linter.infrastructure.services.rule_analysis import RuleFixabilityService


class AuditTrailService:
    """Service for saving audit trails to .excelsior directory."""

    def __init__(
        self,
        telemetry: TelemetryPort,
        rule_fixability_service: RuleFixabilityService,
        filesystem: FileSystemProtocol,
    ) -> None:
        self.telemetry = telemetry
        self.rule_fixability_service = rule_fixability_service
        self.filesystem = filesystem

    def save_audit_trail(self, audit_result: AuditResult) -> None:
        """Save audit results to .excelsior directory for human/AI review."""
        excelsior_dir = ".excelsior"
        self.filesystem.make_dirs(excelsior_dir, exist_ok=True)

        # Build domain entity from audit result
        audit_trail = self._build_audit_trail(audit_result, excelsior_dir)

        # Persist to filesystem (Infrastructure concern)
        json_path = self.filesystem.join_path(excelsior_dir, "last_audit.json")
        json_content = json.dumps(audit_trail.to_dict(), indent=2)
        self.filesystem.write_text(json_path, json_content)

        # Write human-readable text format
        txt_path = self.filesystem.join_path(excelsior_dir, "last_audit.txt")
        txt_content = self._build_text_content(audit_result, audit_trail)
        self.filesystem.write_text(txt_path, txt_content)

        self.telemetry.step(f"💾 Audit Trail persisted to: {json_path} and {txt_path}")

    def _build_audit_trail(
        self, audit_result: AuditResult, excelsior_dir: str
    ) -> AuditTrail:
        """Build domain AuditTrail entity from AuditResult."""
        mypy_adapter = MypyAdapter()
        excelsior_adapter = ExcelsiorAdapter()
        il_adapter = ImportLinterAdapter()
        ruff_adapter = RuffAdapter(telemetry=None) if audit_result.ruff_enabled else None

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
                self._build_violations_with_fix_info(audit_result.ruff_results, ruff_adapter)
                if ruff_adapter
                else []
            ),
        )

        return AuditTrail(
            version="2.0.0",
            timestamp=str(self.filesystem.get_mtime(excelsior_dir)),
            summary=summary,
            violations=violations,
        )

    def _build_violations_with_fix_info(
        self, results: List[LinterResult], adapter: object
    ) -> List[ViolationWithFixInfo]:
        """Build domain ViolationWithFixInfo entities from LinterResults."""
        violations = []
        for result in results:
            fixable = self.rule_fixability_service.is_rule_fixable(adapter, result.code)
            comment_only = (
                adapter.is_comment_only_rule(result.code)
                if hasattr(adapter, "is_comment_only_rule")
                else False
            )
            manual_instructions = None
            if not fixable and hasattr(adapter, "get_manual_fix_instructions"):
                manual_instructions = adapter.get_manual_fix_instructions(result.code)

            violation = ViolationWithFixInfo(
                code=result.code,
                message=result.message,
                location=", ".join(result.locations) if result.locations else "N/A",
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
        lines: List[str],
        title: str,
        violations: List[ViolationWithFixInfo],
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
                lines.append(f"  How to fix (juniors & AI): {violation.manual_instructions}")
