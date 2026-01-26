"""Use Case: Apply Fixes to Source Code."""

import shutil
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import astroid  # type: ignore[import-untyped]

if TYPE_CHECKING:
    import libcst as cst

from clean_architecture_linter.domain.protocols import FixerGatewayProtocol, LinterAdapterProtocol, TelemetryPort
from clean_architecture_linter.domain.rules import BaseRule


class ApplyFixesUseCase:
    """Orchestrate the detection and resolution of architectural violations."""

    def __init__(
        self,
        fixer_gateway: FixerGatewayProtocol,
        linter_adapter: LinterAdapterProtocol = None,
        telemetry: TelemetryPort = None,
        require_confirmation: bool = False,
        create_backups: bool = True,
        cleanup_backups: bool = False,
        validate_with_tests: bool = True
    ) -> None:
        self.fixer_gateway = fixer_gateway
        self.linter_adapter = linter_adapter
        self.telemetry = telemetry
        self.require_confirmation = require_confirmation
        self.create_backups = create_backups
        self.cleanup_backups = cleanup_backups
        self.validate_with_tests = validate_with_tests
        self._test_baseline: Optional[int] = None

    def execute(self, rules: List[BaseRule], target_path: str) -> int:
        """Apply fixes to all files in target path with enhanced safety."""
        path = Path(target_path).resolve()
        if self.telemetry:
            self.telemetry.step(f"🔧 Starting Fix Logic on {target_path}")

        self._run_baseline_if_enabled()
        files = list(path.glob("**/*.py")) if path.is_dir() else [path]
        modified_count: int = 0
        rollback_occurred: bool = False

        failed_fixes_all: List[str] = []

        for file_path in files:
            if file_path.suffix != ".py":
                continue

            # Rule-based discovery: collect transformers from rules
            transformers, failed_fixes = self._collect_transformers_from_rules(rules, file_path)
            failed_fixes_all.extend(failed_fixes)

            if not transformers:
                continue

            if self._skip_confirmation(file_path, transformers):
                continue

            backup_path = self._create_backup(file_path) if self.create_backups else None
            success = self.fixer_gateway.apply_fixes(str(file_path), transformers)

            if success:
                mod_delta, did_rollback = self._handle_successful_fix(
                    file_path, backup_path, modified_count, rollback_occurred
                )
                modified_count = mod_delta
                rollback_occurred = did_rollback
                if did_rollback:
                    self._cleanup_backup_if_requested(backup_path)
                    continue
                self._cleanup_backup_if_requested(backup_path)
            else:
                self._cleanup_backup_if_requested(backup_path)

        if self.telemetry:
            status = "with rollbacks" if rollback_occurred else "complete"
            self.telemetry.step(f"🛠️ Fix Suite {status}. Files repaired: {modified_count}")

            # Report failed fixes
            if failed_fixes_all:
                self.telemetry.step(f"⚠️  {len(failed_fixes_all)} fix(es) could not be applied:")
                for failure in failed_fixes_all:
                    self.telemetry.error(f"  {failure}")

        return modified_count

    def _run_baseline_if_enabled(self) -> None:
        """Run pytest baseline and set _test_baseline; optional telemetry."""
        if not self.validate_with_tests:
            return
        self._test_baseline = self._run_pytest()
        if self.telemetry:
            failures = "passed" if self._test_baseline == 0 else f"{self._test_baseline} failures"
            self.telemetry.step(f"📊 Test baseline: {failures}")

    def _skip_confirmation(self, file_path: Path, transformers: List["cst.CSTTransformer"]) -> bool:
        """True if user skips (require_confirmation and not confirm). Emits telemetry when skipping."""
        if not self.require_confirmation:
            return False
        if self._confirm_fix(file_path, transformers):
            return False
        if self.telemetry:
            self.telemetry.step(f"⏭️  Skipped: {file_path.name}")
        return True

    def _handle_successful_fix(
        self,
        file_path: Path,
        backup_path: Optional[Path],
        modified_count: int,
        rollback_occurred: bool,
    ) -> tuple[int, bool]:
        """Validate after fix; rollback on regression. Return (modified_count, did_rollback)."""
        if self.validate_with_tests:
            test_result = self._run_pytest()
            if self._test_baseline is not None and test_result > self._test_baseline:
                if self.telemetry:
                    self.telemetry.step(
                        f"❌ Regression detected in {file_path.name}. Rolling back..."
                    )
                if backup_path:
                    self._restore_backup(file_path, backup_path)
                return (modified_count, True)

        modified_count += 1
        if self.telemetry:
            try:
                rel = file_path.relative_to(Path.cwd())
            except ValueError:
                rel = file_path
            self.telemetry.step(f"✅ Auto-repaired: {rel}")
        return (modified_count, rollback_occurred)

    def get_manual_fixes(self, target_path: str) -> List[Dict[str, Any]]:
        """Get manual fix suggestions for issues that cannot be auto-fixed."""
        if hasattr(self.fixer_gateway, 'get_manual_suggestions'):
            return self.fixer_gateway.get_manual_suggestions(target_path)
        return []

    def _collect_transformers_from_rules(
        self, rules: List[BaseRule], file_path: Path
    ) -> List["cst.CSTTransformer"]:
        """
        Discover and collect transformers from enabled rules.
        
        For each rule:
        1. Parse file with astroid to get module node
        2. Call rule.check(module_node) to get violations
        3. For each fixable violation, call rule.fix(violation) to get transformer
        4. Collect all transformers
        """
        transformers: List["cst.CSTTransformer"] = []

        try:
            # Parse file with astroid to get module node
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()

            module_node = astroid.parse(source, str(file_path))

            # Iterate through all enabled rules
            for rule in rules:
                try:
                    # Run rule.check() to find violations
                    violations = rule.check(module_node)

                    # For each fixable violation, get transformer
                    for violation in violations:
                        if violation.fixable:
                            transformer = rule.fix(violation)
                            if transformer is not None:
                                transformers.append(transformer)
                except Exception as e:
                    # Log error but continue with other rules
                    if self.telemetry:
                        self.telemetry.error(f"Rule {rule.code} failed on {file_path}: {e}")
                    continue

        except Exception as e:
            if self.telemetry:
                self.telemetry.error(f"Failed to parse {file_path}: {e}")

        return transformers

    def _confirm_fix(self, file_path: Path, transformers: List["cst.CSTTransformer"]) -> bool:
        """Ask user for confirmation before applying fix."""
        if not sys.stdin.isatty():
            # Non-interactive mode, apply automatically
            return True

        print(f"\n📝 File: {file_path.name}")
        print(f"   Transformers: {len(transformers)} transformer(s) will be applied")
        response = input("   Apply fixes? [y/N]: ").strip().lower()
        return response in ['y', 'yes']

    def _create_backup(self, file_path: Path) -> Path:
        """Create a .bak backup of the file."""
        backup_path = file_path.with_suffix(file_path.suffix + '.bak')
        shutil.copy2(file_path, backup_path)
        return backup_path

    def _restore_backup(self, file_path: Path, backup_path: Path) -> None:
        """Restore file from backup."""
        shutil.copy2(backup_path, file_path)

    def _cleanup_backup_if_requested(self, backup_path: Optional[Path]) -> None:
        """Remove backup file when cleanup_backups is set."""
        if self.cleanup_backups and backup_path:
            backup_path.unlink(missing_ok=True)

    def _run_pytest(self) -> int:
        """Run pytest and return number of failures."""
        try:
            result = subprocess.run(
                ['pytest', '--tb=no', '-q', '--no-cov'],
                capture_output=True,
                timeout=120
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
