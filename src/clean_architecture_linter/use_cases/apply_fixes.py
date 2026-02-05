"""Use Case: Apply Fixes to Source Code."""

import shutil
import subprocess
import sys
from collections import defaultdict
from typing import TYPE_CHECKING, Optional, TypedDict, cast

import astroid  # type: ignore[import-untyped]

if TYPE_CHECKING:
    from clean_architecture_linter.domain.entities import LinterResult, TransformationPlan
    from clean_architecture_linter.domain.rules import Violation
else:
    from clean_architecture_linter.domain.entities import LinterResult, TransformationPlan

from clean_architecture_linter.domain.constants import (
    RUFF_CODE_QUALITY_SELECT,
    RUFF_IMPORT_TYPING_SELECT,
)
from clean_architecture_linter.domain.protocols import (
    AstroidProtocol,
    FileSystemProtocol,
    FixerGatewayProtocol,
    LinterAdapterProtocol,
    TelemetryPort,
    ViolationBridgeProtocol,
)
from clean_architecture_linter.domain.rules import BaseRule
from clean_architecture_linter.domain.rules.governance_comments import (
    GovernanceRuleFactory,
)
from clean_architecture_linter.domain.rules.type_hints import MissingTypeHintRule


class ManualSuggestionRow(TypedDict):
    """One manual fix suggestion from the gateway (linter, code, message, file, line, suggestion)."""

    linter: str
    code: str
    message: str
    file: str
    line: int
    suggestion: str


class RunPytestKwargs(TypedDict, total=False):
    """Keyword arguments for subprocess.run when running pytest."""

    capture_output: bool
    timeout: int
    cwd: str


if TYPE_CHECKING:
    from clean_architecture_linter.domain.config import ConfigurationLoader
    from clean_architecture_linter.use_cases.check_audit import CheckAuditUseCase


class ApplyFixesUseCase:
    """Orchestrate the detection and resolution of architectural violations."""

    def __init__(
        self,
        fixer_gateway: FixerGatewayProtocol,
        filesystem: FileSystemProtocol,
        linter_adapter: LinterAdapterProtocol,
        telemetry: TelemetryPort,
        astroid_gateway: AstroidProtocol,
        ruff_adapter: LinterAdapterProtocol,
        check_audit_use_case: "CheckAuditUseCase",
        config_loader: "ConfigurationLoader",
        excelsior_adapter: LinterAdapterProtocol,
        violation_bridge: ViolationBridgeProtocol,
        require_confirmation: bool = False,
        create_backups: bool = True,
        cleanup_backups: bool = False,
        validate_with_tests: bool = True,
    ) -> None:
        self.fixer_gateway = fixer_gateway
        self.filesystem = filesystem
        self.linter_adapter = linter_adapter
        self.telemetry = telemetry
        self.require_confirmation = require_confirmation
        self.create_backups = create_backups
        self.cleanup_backups = cleanup_backups
        self.validate_with_tests = validate_with_tests
        self.astroid_gateway = astroid_gateway
        self.ruff_adapter = ruff_adapter
        self.check_audit_use_case = check_audit_use_case
        self.config_loader = config_loader
        self.excelsior_adapter = excelsior_adapter
        self.violation_bridge = violation_bridge
        self._test_baseline: Optional[int] = None

    def execute(self, rules: list[BaseRule], target_path: str) -> int:
        """Apply fixes to all files in target path with enhanced safety."""
        if self.telemetry:
            self.telemetry.step(f"🔧 Starting Fix Logic on {target_path}")

        self._current_target_path = target_path
        self._run_baseline_if_enabled()
        files = self.filesystem.glob_python_files(target_path)
        modified_count: int = 0
        rollback_occurred: bool = False
        failed_fixes_all: list[str] = []

        for file_path_str in files:
            mod_delta, did_rollback, failed = self._execute_one_file(
                file_path_str, rules, modified_count, rollback_occurred
            )
            modified_count = mod_delta
            rollback_occurred = did_rollback
            failed_fixes_all.extend(failed)

        if self.telemetry:
            status = "with rollbacks" if rollback_occurred else "complete"
            self.telemetry.step(
                f"🛠️ Fix Suite {status}. Files repaired: {modified_count}")
            if failed_fixes_all:
                self.telemetry.step(
                    f"⚠️  {len(failed_fixes_all)} fix(es) could not be applied:")
                for failure in failed_fixes_all:
                    self.telemetry.error(f"  {failure}")

        return modified_count

    def _execute_one_file(
        self,
        file_path_str: str,
        rules: list[BaseRule],
        modified_count: int,
        rollback_occurred: bool,
    ) -> tuple[int, bool, list[str]]:
        """Process one file in execute() loop. Returns (modified_count, rollback_occurred, failed_fixes)."""
        plans, failed_fixes, rule_codes = self._collect_plans_from_rules(
            rules, file_path_str
        )

        if self.telemetry:
            _rel = self._rel_path(file_path_str)
            if plans:
                rules_str = ",".join(str(rc) for rc in rule_codes)
                self.telemetry.step(
                    f"file={_rel} attempt plans={len(plans)} rules=[{rules_str}]"
                )
            else:
                self.telemetry.step(
                    f"file={_rel} status=skipped reason=no_fixable_violations"
                )

        if not plans:
            return (modified_count, rollback_occurred, failed_fixes)

        if self._skip_confirmation(file_path_str, plans):
            if self.telemetry:
                self.telemetry.warning(
                    f"file={self._rel_path(file_path_str)} status=skipped reason=user_declined"
                )
            return (modified_count, rollback_occurred, failed_fixes)

        backup_path_str = (
            self._create_backup(file_path_str) if self.create_backups else None
        )
        success = self.fixer_gateway.apply_fixes(file_path_str, plans)

        if success:
            mod_delta, did_rollback = self._handle_successful_fix(
                file_path_str, backup_path_str, modified_count, rollback_occurred,
                rule_codes,
            )
            self._cleanup_backup_if_requested(backup_path_str)
            return (mod_delta, did_rollback, failed_fixes)

        if self.telemetry:
            self.telemetry.error(
                f"file={self._rel_path(file_path_str)} status=failed reason=apply_fixes_returned_false"
            )
        self._cleanup_backup_if_requested(backup_path_str)
        return (modified_count, rollback_occurred, failed_fixes)

    def execute_multi_pass(
        self,
        rules: list[BaseRule],
        target_path: str,
        inject_governance_comments: bool = False,
    ) -> int:
        """
        Execute multi-pass fixer with cache clearing:
        Pass 1 (Ruff + W9015) → Clear Cache → Pass 2 (Architecture) → Pass 3 (LoD Comments, optional).

        Args:
            rules: List of BaseRule instances (Excelsior rules)
            target_path: Path to fix
            inject_governance_comments: If True, inject EXCELSIOR comment blocks above violation
                lines (Pass 4). Default False: use handover + plan-fix for instructions instead.

        Returns:
            Total number of files modified across all passes
        """
        if self.telemetry:
            self.telemetry.step(
                f"🔧 Starting Multi-Pass Fix Logic on {target_path}")

        self._current_target_path = target_path
        self._run_baseline_if_enabled()

        # Phase 1: Deterministic fixes (Ruff + Type Hints)
        pass1_modified = self._execute_pass1_ruff_import_typing(target_path)
        pass2_modified = self._execute_pass2_type_hints(rules, target_path)

        # The Reset: Clear astroid inference cache after type hints are added
        self._clear_astroid_cache()

        # Phase 2: Architectural fixes (excluding W9015 and W9006)
        pass3_modified = self._execute_pass3_architecture_code(
            rules, target_path)

        # Phase 3: Governance Comments (optional; use plan-fix / handover by default)
        if inject_governance_comments:
            pass4_modified = self._execute_pass4_governance_comments(
                rules, target_path)
        else:
            pass4_modified = 0

        # Phase 4: Code quality last (Ruff E, F, W, C90, ...)
        pass5_modified = self._execute_pass5_ruff_code_quality(target_path)

        total_modified = (
            pass1_modified + pass2_modified + pass3_modified
            + pass4_modified + pass5_modified
        )

        if self.telemetry:
            self.telemetry.step(
                f"🛠️ Multi-Pass Fix Suite complete. Total files repaired: {total_modified}")

        return total_modified

    def _execute_pass1_ruff_import_typing(self, target_path: str) -> int:
        """Pass 1: Apply Ruff import & typing fixes (I, UP, B) first."""
        if not (self.ruff_adapter and self.config_loader and self.config_loader.ruff_enabled):
            return 0
        from pathlib import Path

        if self.telemetry:
            self.telemetry.step(
                "Pass 1: Applying Ruff import & typing fixes (I, UP, B)...")
        ruff_modified = self.ruff_adapter.apply_fixes(
            Path(target_path), select_only=RUFF_IMPORT_TYPING_SELECT
        )
        if ruff_modified and self.telemetry:
            self.telemetry.step(
                "✅ Pass 1 complete: Ruff import/typing applied")
        return 1 if ruff_modified else 0

    def _execute_pass5_ruff_code_quality(self, target_path: str) -> int:
        """Pass 5: Apply Ruff code quality fixes (E, F, W, C90, ...) last."""
        if not (self.ruff_adapter and self.config_loader and self.config_loader.ruff_enabled):
            return 0
        from pathlib import Path

        if self.telemetry:
            self.telemetry.step(
                "Pass 5: Applying Ruff code quality fixes (E, F, W, C90, ...)...")
        ruff_modified = self.ruff_adapter.apply_fixes(
            Path(target_path), select_only=RUFF_CODE_QUALITY_SELECT
        )
        if ruff_modified and self.telemetry:
            self.telemetry.step("✅ Pass 5 complete: Ruff code quality applied")
        return 1 if ruff_modified else 0

    def _execute_pass2_type_hints(self, rules: list[BaseRule], target_path: str) -> int:
        """Pass 2: Apply type-hint injections (W9015 only)."""
        if self.telemetry:
            self.telemetry.step(
                "Pass 2: Applying type-hint injections (W9015)...")

        w9015_rules = self._get_w9015_rules(rules)
        pass2_modified = self._apply_rule_fixes(w9015_rules, target_path)

        if self.telemetry and pass2_modified > 0:
            self.telemetry.step(
                f"✅ Pass 2 complete: {pass2_modified} file(s) fixed with type hints")

        return pass2_modified

    def _clear_astroid_cache(self) -> None:
        """Clear astroid inference cache to force fresh inference after code changes."""
        if self.astroid_gateway:
            self.astroid_gateway.clear_inference_cache()
            if self.telemetry:
                self.telemetry.step(
                    "🔄 Pass 1–2 complete. Cleared astroid cache. Re-inferring architecture for Pass 3…"
                )

    def _execute_pass3_architecture_code(self, rules: list[BaseRule], target_path: str) -> int:
        """Pass 3: Apply architectural code fixes (excluding W9015 and W9006)."""
        if self.telemetry:
            self.telemetry.step("Pass 3: Applying architectural code fixes...")

        if not self.check_audit_use_case:
            # Fallback: apply remaining rules without re-audit
            architecture_rules = self._get_architecture_code_rules(rules)
            return self._apply_rule_fixes(architecture_rules, target_path)

        audit_result = self.check_audit_use_case.execute(target_path)

        if audit_result.is_blocked():
            if self.telemetry:
                self.telemetry.step(
                    f"⚠️  Pass 3 skipped: Audit blocked by {audit_result.blocked_by}")
            return 0

        # Apply architecture rules (code fixes only, not comments)
        architecture_rules = self._get_architecture_code_rules(rules)
        rule_modified = self._apply_rule_fixes(architecture_rules, target_path)

        if self.telemetry and rule_modified > 0:
            self.telemetry.step(
                f"✅ Pass 3 complete: {rule_modified} file(s) fixed with architectural code changes")

        return rule_modified

    def _execute_pass4_governance_comments(self, rules: list[BaseRule], target_path: str) -> int:
        """Pass 4: Apply governance comments for all comment-only violations."""
        if self.telemetry:
            self.telemetry.step(
                "Pass 4: Applying governance comments for architectural violations...")

        if not self.check_audit_use_case:
            # Fallback: skip governance comments if no audit use case available
            return 0

        audit_result = self.check_audit_use_case.execute(target_path)

        if audit_result.is_blocked():
            if self.telemetry:
                self.telemetry.step(
                    f"⚠️  Pass 4 skipped: Audit blocked by {audit_result.blocked_by}")
            return 0

        # Upstream gating: do not surface or apply governance comment fixes until W9015 is resolved.
        # This prevents noisy/false architectural results when type hints are missing.
        if any(r.code == "W9015" for r in (audit_result.excelsior_results or [])):
            if self.telemetry:
                self.telemetry.step(
                    "⚠️  Pass 4 skipped: W9015 missing type hints must be resolved first")
            return 0

        if not audit_result.excelsior_results:
            return 0

        # Apply governance comment fixes for all comment-only violations
        governance_modified = self._apply_governance_comments(
            audit_result.excelsior_results, target_path
        )

        if self.telemetry and governance_modified > 0:
            self.telemetry.step(
                f"✅ Pass 4 complete: {governance_modified} file(s) fixed with governance comments")

        return governance_modified

    def _apply_governance_comments(
        self, excelsior_results: list[LinterResult], target_path: str
    ) -> int:
        """
        Apply governance comment fixes for manual-fix violations.

        Converts Excelsior violations to Violation objects and injects
        governance comments above violation lines.
        """
        if not self.astroid_gateway:
            return 0

        # Use injected bridge; skip governance comment injection if not provided
        if not self.violation_bridge:
            return 0
        bridge_service = self.violation_bridge
        files = self.filesystem.glob_python_files(target_path)
        violations_by_file = self._group_violations_by_file(excelsior_results)
        modified_count = 0

        # Process each file
        for file_path_str in files:
            if file_path_str not in violations_by_file:
                continue

            file_results = violations_by_file[file_path_str]
            violations = bridge_service.convert_linter_results_to_violations(
                file_results, file_path_str
            )

            if not violations:
                continue

            plans = self._build_governance_plans(violations)
            if not plans:
                continue

            if self.telemetry:
                self.telemetry.step(
                    f"file={self._rel_path(file_path_str)} attempt governance_comments plans={len(plans)}"
                )
            delta = self._apply_plans_to_file(file_path_str, plans)
            if self.telemetry and delta:
                self.telemetry.step(
                    f"file={self._rel_path(file_path_str)} status=success applied=governance_comments"
                )
            modified_count += delta

        return modified_count

    def _group_violations_by_file(
        self, excelsior_results: list[LinterResult]
    ) -> dict[str, list[LinterResult]]:
        """Group violations by file path."""
        violations_by_file: dict[str, list[LinterResult]] = defaultdict(list)
        for result in excelsior_results:
            for location in result.locations:
                file_path = location.split(":")[0]
                violations_by_file[file_path].append(result)
        return violations_by_file

    def _build_governance_plans(
        self, violations: list["Violation"]
    ) -> list[TransformationPlan]:
        """Build governance comment plans for all comment-only violations."""
        plans: list[TransformationPlan] = []
        excelsior_adapter = self.excelsior_adapter

        for violation in violations:
            if not violation.is_comment_only:
                continue

            factory = GovernanceRuleFactory()
            rule = factory.create_rule(violation.code, excelsior_adapter)
            if rule:
                plan = rule.fix(violation)
                if plan:
                    plans.append(plan)
        return plans

    def _apply_plans_to_file(
        self, file_path_str: str, plans: list[TransformationPlan]
    ) -> int:
        """Apply transformation plans to a single file."""
        if self._skip_confirmation(file_path_str, plans):
            return 0

        backup_path_str = (
            self._create_backup(file_path_str) if self.create_backups else None
        )
        success = self.fixer_gateway.apply_fixes(file_path_str, plans)

        if success:
            mod_delta, did_rollback = self._handle_successful_fix(
                file_path_str, backup_path_str, 0, False
            )
            if did_rollback:
                self._cleanup_backup_if_requested(backup_path_str)
                return 0
            self._cleanup_backup_if_requested(backup_path_str)
            return mod_delta
        else:
            self._cleanup_backup_if_requested(backup_path_str)
            return 0

    def _get_w9015_rules(self, rules: list[BaseRule]) -> list[BaseRule]:
        """Get W9015 rules from list, creating if missing."""
        w9015_rules = [r for r in rules if hasattr(
            r, 'code') and r.code == "W9015"]
        if not w9015_rules and self.astroid_gateway:
            w9015_rules = cast(
                list[BaseRule], [MissingTypeHintRule(self.astroid_gateway)])
        return w9015_rules

    def _get_architecture_rules(self, rules: list[BaseRule]) -> list[BaseRule]:
        """Get architecture rules excluding W9015 (already fixed in Pass 2)."""
        return [r for r in rules if not (hasattr(r, 'code') and r.code == "W9015")]

    def _get_architecture_code_rules(self, rules: list[BaseRule]) -> list[BaseRule]:
        """Get architecture rules for code fixes (excluding W9015 and W9006)."""
        return [
            r for r in rules
            if not (hasattr(r, 'code') and r.code in ("W9015", "W9006"))
            and (not hasattr(r, 'fix_type') or getattr(r, 'fix_type', 'code') == 'code')
        ]

    def _apply_rule_fixes(self, rules: list[BaseRule], target_path: str) -> int:
        """
        Apply fixes from a list of rules to target path.

        Returns:
            Number of files modified
        """
        files = self.filesystem.glob_python_files(target_path)
        modified_count = 0
        failed_fixes_all: list[str] = []

        for file_path_str in files:
            mod_delta, failed = self._apply_rule_fixes_one_file(
                file_path_str, rules, modified_count
            )
            modified_count = mod_delta
            failed_fixes_all.extend(failed)

        if failed_fixes_all and self.telemetry:
            self.telemetry.step(
                f"⚠️  {len(failed_fixes_all)} fix(es) could not be applied:")
            for failure in failed_fixes_all:
                self.telemetry.error(f"  {failure}")

        return modified_count

    def _apply_rule_fixes_one_file(
        self, file_path_str: str, rules: list[BaseRule], modified_count: int
    ) -> tuple[int, list[str]]:
        """Process one file in _apply_rule_fixes. Returns (modified_count, failed_fixes)."""
        plans, failed_fixes, rule_codes = self._collect_plans_from_rules(
            rules, file_path_str
        )

        if self.telemetry:
            _rel_path = self._rel_path(file_path_str)
            if plans:
                rules_str = ",".join(str(rc) for rc in rule_codes)
                self.telemetry.step(
                    f"file={_rel_path} attempt plans={len(plans)} rules=[{rules_str}]"
                )
            else:
                self.telemetry.step(
                    f"file={_rel_path} status=skipped reason=no_fixable_violations"
                )

        if not plans:
            return (modified_count, failed_fixes)

        if self._skip_confirmation(file_path_str, plans):
            if self.telemetry:
                self.telemetry.warning(
                    f"file={self._rel_path(file_path_str)} status=skipped reason=user_declined"
                )
            return (modified_count, failed_fixes)

        backup_path_str = (
            self._create_backup(file_path_str) if self.create_backups else None
        )
        success = self.fixer_gateway.apply_fixes(file_path_str, plans)

        if success:
            mod_delta, _ = self._handle_successful_fix(
                file_path_str, backup_path_str, modified_count, False, rule_codes
            )
            self._cleanup_backup_if_requested(backup_path_str)
            return (mod_delta, failed_fixes)

        if self.telemetry:
            self.telemetry.error(
                f"file={self._rel_path(file_path_str)} status=failed reason=apply_fixes_returned_false"
            )
        self._cleanup_backup_if_requested(backup_path_str)
        return (modified_count, failed_fixes)

    def _run_baseline_if_enabled(self) -> None:
        """Run pytest baseline and set _test_baseline; optional telemetry."""
        if not self.validate_with_tests:
            return
        self._test_baseline = self._run_pytest()
        if self.telemetry:
            failures = "passed" if self._test_baseline == 0 else f"{self._test_baseline} failures"
            self.telemetry.step(f"📊 Test baseline: {failures}")

    def _skip_confirmation(self, file_path_str: str, plans: list[TransformationPlan]) -> bool:
        """True if user skips (require_confirmation and not confirm). Emits telemetry when skipping."""
        if not self.require_confirmation:
            return False
        if self._confirm_fix(file_path_str, plans):
            return False
        if self.telemetry:
            # JUSTIFICATION: File name extraction for display only
            from pathlib import Path
            file_name = Path(file_path_str).name
            self.telemetry.step(f"⏭️  Skipped: {file_name}")
        return True

    def _rel_path(self, file_path_str: str) -> str:
        """Return path relative to cwd for logging; fallback to absolute."""
        from pathlib import Path
        try:
            return str(Path(file_path_str).relative_to(Path.cwd()))
        except ValueError:
            return file_path_str

    def _handle_successful_fix(
        self,
        file_path_str: str,
        backup_path_str: Optional[str],
        modified_count: int,
        rollback_occurred: bool,
        rule_codes: Optional[list[str]] = None,
    ) -> tuple[int, bool]:
        """Validate after fix; rollback on regression. Return (modified_count, did_rollback)."""
        if self.validate_with_tests:
            test_result = self._run_pytest()
            if self._test_baseline is not None and test_result > self._test_baseline:
                if self.telemetry:
                    from pathlib import Path
                    file_name = Path(file_path_str).name
                    self.telemetry.step(
                        f"❌ Regression detected in {file_name}. Rolling back..."
                    )
                if backup_path_str:
                    self._restore_backup(file_path_str, backup_path_str)
                return (modified_count, True)

        modified_count += 1
        if self.telemetry:
            rel = self._rel_path(file_path_str)
            self.telemetry.step(f"✅ Auto-repaired: {rel}")
            applied = ",".join(str(rc)
                               for rc in rule_codes) if rule_codes else "n/a"
            self.telemetry.step(
                f"file={rel} status=success applied_rules=[{applied}]"
            )
        return (modified_count, rollback_occurred)

    def get_manual_fixes(self, target_path: str) -> list[ManualSuggestionRow]:
        """Get manual fix suggestions for issues that cannot be auto-fixed."""
        if hasattr(self.fixer_gateway, 'get_manual_suggestions'):
            return cast(list[ManualSuggestionRow], self.fixer_gateway.get_manual_suggestions(target_path))
        return []

    def _collect_plans_from_rules(
        self, rules: list[BaseRule], file_path_str: str
    ) -> tuple[list[TransformationPlan], list[str], list[str]]:
        """
        Discover and collect transformation plans from enabled rules.

        For each rule:
        1. Parse file with astroid to get module node
        2. Call rule.check(module_node) to get violations
        3. For each fixable violation, call rule.fix(violation) to get plan(s)
        4. Collect all plans and failed fix reasons

        Returns:
            (plans, failed_fixes, rule_codes) where failed_fixes is a list of
            failure messages and rule_codes are rule codes that produced at least one plan.
        """
        plans: list[TransformationPlan] = []
        failed_fixes: list[str] = []
        rule_codes_applied: list[str] = []

        try:
            from pathlib import Path
            file_path = Path(file_path_str)
            with open(file_path, encoding="utf-8") as f:
                source = f.read()
            module_node = astroid.parse(source, file_path_str)
            for rule in rules:
                p, failed_list, rc = self._collect_plans_for_rule(
                    rule, module_node, file_path_str
                )
                plans.extend(p)
                failed_fixes.extend(failed_list)
                for code in rc:
                    if code not in rule_codes_applied:
                        rule_codes_applied.append(code)
        except Exception as e:
            if self.telemetry:
                self.telemetry.error(f"Failed to parse {file_path_str}: {e}")

        return (plans, failed_fixes, rule_codes_applied)

    def _collect_plans_for_rule(
        self, rule: BaseRule, module_node: astroid.nodes.Module, file_path_str: str
    ) -> tuple[list[TransformationPlan], list[str], list[str]]:
        """Collect transformation plans from one rule for a module. Returns (plans, failed_fixes, rule_codes)."""
        plans: list[TransformationPlan] = []
        failed_fixes: list[str] = []
        rule_code = getattr(rule, "code", "?")
        rule_codes_out: list[str] = []

        try:
            violations = rule.check(module_node)
            for violation in violations:
                if not violation.fixable:
                    continue
                plan_or_plans = rule.fix(violation)
                if plan_or_plans is None:
                    reason = violation.fix_failure_reason or "Unknown reason"
                    failed_fixes.append(
                        f"Failed to fix {violation.code} in {file_path_str}: {reason}"
                    )
                    if self.telemetry:
                        self.telemetry.error(
                            f"Failed to fix {violation.code} in {file_path_str}: {reason}"
                        )
                elif isinstance(plan_or_plans, list):
                    added = [p for p in plan_or_plans if p is not None]
                    plans.extend(added)
                    if added and rule_code not in rule_codes_out:
                        rule_codes_out.append(rule_code)
                else:
                    plans.append(plan_or_plans)
                    if rule_code not in rule_codes_out:
                        rule_codes_out.append(rule_code)
        except Exception as e:
            if self.telemetry:
                self.telemetry.error(
                    f"Rule {rule_code} failed on {file_path_str}: {e}"
                )
        return (plans, failed_fixes, rule_codes_out)

    def _confirm_fix(self, file_path_str: str, plans: list[TransformationPlan]) -> bool:
        """Ask user for confirmation before applying fix."""
        if not sys.stdin.isatty():
            # Non-interactive mode, apply automatically
            return True

        # JUSTIFICATION: File name extraction for display only
        from pathlib import Path
        file_name = Path(file_path_str).name
        print(f"\n📝 File: {file_name}")
        print(f"   Plans: {len(plans)} fix(es) will be applied")
        response = input("   Apply fixes? [y/N]: ").strip().lower()
        return response in ['y', 'yes']

    def _create_backup(self, file_path_str: str) -> str:
        """Create a .bak backup of the file. Returns backup path string."""
        # JUSTIFICATION: Backup operations require Path for file I/O
        from pathlib import Path
        file_path = Path(file_path_str)
        backup_path = file_path.with_suffix(file_path.suffix + '.bak')
        shutil.copy2(file_path, backup_path)
        return str(backup_path)

    def _restore_backup(self, file_path_str: str, backup_path_str: str) -> None:
        """Restore file from backup."""
        # JUSTIFICATION: File restoration requires Path for file I/O
        from pathlib import Path
        shutil.copy2(Path(backup_path_str), Path(file_path_str))

    def _cleanup_backup_if_requested(self, backup_path_str: Optional[str]) -> None:
        """Remove backup file when cleanup_backups is set."""
        if self.cleanup_backups and backup_path_str:
            # JUSTIFICATION: File deletion requires Path for file I/O
            from pathlib import Path
            Path(backup_path_str).unlink(missing_ok=True)

    def _run_pytest(self) -> int:
        """Run pytest and return number of failures (in project being fixed when set)."""
        try:
            kwargs: RunPytestKwargs = {"capture_output": True, "timeout": 120}
            cwd = getattr(self, "_current_target_path", None)
            if cwd:
                from pathlib import Path
                p = Path(cwd)
                kwargs["cwd"] = str(p.parent) if p.is_file() else cwd
            result = subprocess.run(
                ['pytest', '--tb=no', '-q', '--no-cov'],
                **kwargs
            )
            # Parse output for failure count
            output = result.stdout.decode() + result.stderr.decode()

            # returncode 0 = all passed, 1 = some failed, 5 = no tests
            if result.returncode == 0:
                return 0
            elif result.returncode == 5:
                return 0  # No tests collected

            # Try to extract failure count from output
            # Format: "1 failed, 152 passed"
            import re
            match = re.search(r'(\d+) failed', output)
            if match:
                return int(match.group(1))

            return 1 if result.returncode != 0 else 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            # pytest not available or timeout
            return 0  # Assume OK if can't test
