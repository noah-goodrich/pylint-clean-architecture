"""Service for persisting audit trails."""

import json
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List

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

        self.telemetry.step(
            f"💾 Audit Trail persisted to: {json_path} and {txt_path}")

    def _build_audit_trail(
        self, audit_result: AuditResult, excelsior_dir: str
    ) -> AuditTrail:
        """Build domain AuditTrail entity from AuditResult."""
        mypy_adapter = MypyAdapter()
        excelsior_adapter = ExcelsiorAdapter()
        il_adapter = ImportLinterAdapter()
        ruff_adapter = RuffAdapter(
            telemetry=None) if audit_result.ruff_enabled else None

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
                lines.append(
                    f"  How to fix (juniors & AI): {violation.manual_instructions}")

    def save_ai_handover(self, audit_result: AuditResult) -> str:
        """
        Generate and save AI handover bundle for autonomous fixing.

        Creates a structured JSON file (.excelsior/ai_handover.json) with:
        - Remaining violations grouped by rule code
        - File locations with line numbers (for finding EXCELSIOR comment anchors)
        - Fixability status and instructions
        - Next steps guidance

        Returns:
            Path to the generated JSON file
        """
        excelsior_dir = ".excelsior"
        self.filesystem.make_dirs(excelsior_dir, exist_ok=True)

        # Build AI handover structure
        handover = self._build_ai_handover(audit_result)

        # Persist to filesystem
        json_path = self.filesystem.join_path(
            excelsior_dir, "ai_handover.json")
        json_content = json.dumps(handover, indent=2)
        self.filesystem.write_text(json_path, json_content)

        self.telemetry.step(f"🤖 AI Handover bundle saved to: {json_path}")
        return json_path

    def _build_ai_handover(self, audit_result: AuditResult) -> Dict[str, Any]:
        """Build AI handover JSON structure."""
        mypy_adapter = MypyAdapter()
        excelsior_adapter = ExcelsiorAdapter()
        il_adapter = ImportLinterAdapter()
        ruff_adapter = RuffAdapter(
            telemetry=None) if audit_result.ruff_enabled else None

        # Group violations by rule code
        violations_by_rule: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        files_with_comments: Dict[str, List[int]] = defaultdict(list)

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

            for result in results:
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
                    "code": result.code,
                    "message": result.message,
                    "locations": result.locations,
                    "category": category,
                    "fixable": fixable,
                    "comment_only": comment_only,
                    "manual_instructions": manual_instructions,
                }
                violations_by_rule[result.code].append(violation_data)

        # Build next steps guidance
        next_steps = self._build_next_steps(audit_result, violations_by_rule)

        return {
            "version": "1.0.0",
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_violations": sum(len(v) for v in violations_by_rule.values()),
                "rules_with_violations": len(violations_by_rule),
                "files_with_governance_comments": len(files_with_comments),
                "blocked_by": audit_result.blocked_by,
            },
            "violations_by_rule": dict(violations_by_rule),
            "files_with_governance_comments": {
                file_path: sorted(set(line_nums))
                for file_path, line_nums in files_with_comments.items()
            },
            "next_steps": next_steps,
        }

    def _build_next_steps(
        self, audit_result: AuditResult, violations_by_rule: Dict[str, List[Dict[str, Any]]]
    ) -> List[str]:
        """Build next steps guidance for AI."""
        steps = []

        if audit_result.is_blocked():
            steps.append(
                f"⚠️  BLOCKED: Audit was blocked by {audit_result.blocked_by}. "
                f"Fix upstream violations first."
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
                f"Run 'excelsior fix' to apply automatic fixes."
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
                f"See 'manual_instructions' in violation data."
            )

        if not steps:
            steps.append("✅ No violations found! Codebase is clean.")

        return steps
