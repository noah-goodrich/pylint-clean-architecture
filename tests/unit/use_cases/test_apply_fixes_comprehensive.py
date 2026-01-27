"""Comprehensive unit tests for ApplyFixesUseCase covering all high-impact methods.

These tests focus on methods identified as high-priority in TEST_PRIORITIES.md:
- Backup operations (_create_backup, _restore_backup, _cleanup_backup_if_requested)
- Confirmation flow (_skip_confirmation, _confirm_fix)
- Pytest validation (_run_pytest, _run_baseline_if_enabled)
- Fix handling (_handle_successful_fix)
- Transformer collection (_collect_transformers_from_rules)
- Multi-pass execution (execute_multi_pass, _execute_pass1_ruff, etc.)
- File modification workflows

These tests use mocks to avoid subprocess calls and are NOT marked as slow.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from clean_architecture_linter.infrastructure.gateways.filesystem_gateway import FileSystemGateway
from clean_architecture_linter.use_cases.apply_fixes import ApplyFixesUseCase


class TestBackupOperations:
    """Test backup creation, restoration, and cleanup operations."""

    def test_create_backup_creates_bak_file(self, tmp_path) -> None:
        """Test _create_backup creates a .bak file with correct content."""
        test_file = tmp_path / "example.py"
        test_file.write_text("original content\n")

        fixer_gateway = MagicMock()
        filesystem = FileSystemGateway()
        use_case = ApplyFixesUseCase(fixer_gateway, filesystem)

        backup_path = use_case._create_backup(str(test_file))

        backup_file = Path(backup_path)
        assert backup_file.exists()
        assert backup_file.read_text() == "original content\n"
        assert backup_file.suffix == ".bak"

    def test_restore_backup_restores_file_content(self, tmp_path) -> None:
        """Test _restore_backup restores file from backup."""
        test_file = tmp_path / "example.py"
        backup_file = tmp_path / "example.py.bak"
        
        test_file.write_text("modified content\n")
        backup_file.write_text("original content\n")

        fixer_gateway = MagicMock()
        filesystem = FileSystemGateway()
        use_case = ApplyFixesUseCase(fixer_gateway, filesystem)

        use_case._restore_backup(str(test_file), str(backup_file))

        assert test_file.read_text() == "original content\n"

    def test_cleanup_backup_removes_file_when_enabled(self, tmp_path) -> None:
        """Test _cleanup_backup_if_requested removes backup when cleanup_backups=True."""
        backup_file = tmp_path / "example.py.bak"
        backup_file.write_text("backup content\n")

        fixer_gateway = MagicMock()
        filesystem = FileSystemGateway()
        use_case = ApplyFixesUseCase(fixer_gateway, filesystem, cleanup_backups=True)

        use_case._cleanup_backup_if_requested(str(backup_file))

        assert not backup_file.exists()

    def test_cleanup_backup_keeps_file_when_disabled(self, tmp_path) -> None:
        """Test _cleanup_backup_if_requested keeps backup when cleanup_backups=False."""
        backup_file = tmp_path / "example.py.bak"
        backup_file.write_text("backup content\n")

        fixer_gateway = MagicMock()
        filesystem = FileSystemGateway()
        use_case = ApplyFixesUseCase(fixer_gateway, filesystem, cleanup_backups=False)

        use_case._cleanup_backup_if_requested(str(backup_file))

        assert backup_file.exists()

    def test_cleanup_backup_handles_none(self) -> None:
        """Test _cleanup_backup_if_requested handles None backup path."""
        fixer_gateway = MagicMock()
        filesystem = FileSystemGateway()
        use_case = ApplyFixesUseCase(fixer_gateway, filesystem, cleanup_backups=True)

        # Should not raise
        use_case._cleanup_backup_if_requested(None)

    def test_no_backup_created_when_flag_disabled(self, tmp_path) -> None:
        """Test backup is not created when create_backups=False."""
        test_file = tmp_path / "example.py"
        test_file.write_text("x = 1\n")

        fixer_gateway = MagicMock()
        fixer_gateway.apply_fixes.return_value = True
        filesystem = FileSystemGateway()

        mock_rule = MagicMock()
        mock_violation = MagicMock()
        mock_violation.fixable = True
        mock_violation.location = str(test_file)
        mock_transformer = MagicMock()
        mock_rule.check.return_value = [mock_violation]
        mock_rule.fix.return_value = mock_transformer

        use_case = ApplyFixesUseCase(fixer_gateway, filesystem, create_backups=False, validate_with_tests=False)
        use_case.execute([mock_rule], str(test_file))

        backup_file = tmp_path / "example.py.bak"
        assert not backup_file.exists()


class TestConfirmationFlow:
    """Test confirmation prompt and skip logic."""

    def test_skip_confirmation_returns_false_when_not_required(self) -> None:
        """Test _skip_confirmation returns False when require_confirmation=False."""
        fixer_gateway = MagicMock()
        filesystem = FileSystemGateway()
        use_case = ApplyFixesUseCase(fixer_gateway, filesystem, require_confirmation=False)

        result = use_case._skip_confirmation("test.py", [MagicMock()])

        assert result is False

    def test_skip_confirmation_skips_when_user_says_no(self) -> None:
        """Test _skip_confirmation returns True when user declines."""
        fixer_gateway = MagicMock()
        filesystem = FileSystemGateway()
        telemetry = MagicMock()
        use_case = ApplyFixesUseCase(fixer_gateway, filesystem, require_confirmation=True, telemetry=telemetry)

        with patch('sys.stdin.isatty', return_value=True), patch(
            'builtins.input', return_value='n'
        ):
            result = use_case._skip_confirmation("test.py", [MagicMock()])

        assert result is True
        telemetry.step.assert_called()

    def test_skip_confirmation_proceeds_when_user_says_yes(self) -> None:
        """Test _skip_confirmation returns False when user confirms."""
        fixer_gateway = MagicMock()
        filesystem = FileSystemGateway()
        use_case = ApplyFixesUseCase(fixer_gateway, filesystem, require_confirmation=True)

        with patch('sys.stdin.isatty', return_value=True), patch(
            'builtins.input', return_value='y'
        ):
            result = use_case._skip_confirmation("test.py", [MagicMock()])

        assert result is False

    def test_confirm_fix_auto_approves_in_non_interactive_mode(self) -> None:
        """Test _confirm_fix returns True in non-interactive mode."""
        fixer_gateway = MagicMock()
        filesystem = FileSystemGateway()
        use_case = ApplyFixesUseCase(fixer_gateway, filesystem)

        with patch('sys.stdin.isatty', return_value=False):
            result = use_case._confirm_fix("test.py", [MagicMock()])

        assert result is True

    def test_confirm_fix_prompts_in_interactive_mode(self) -> None:
        """Test _confirm_fix prompts user in interactive mode."""
        fixer_gateway = MagicMock()
        filesystem = FileSystemGateway()
        use_case = ApplyFixesUseCase(fixer_gateway, filesystem)

        with patch('sys.stdin.isatty', return_value=True), patch(
            'builtins.input', return_value='yes'
        ) as mock_input:
            result = use_case._confirm_fix("test.py", [MagicMock()])

        assert result is True
        mock_input.assert_called_once()


class TestPytestValidation:
    """Test pytest validation and baseline logic."""

    def test_run_baseline_if_enabled_sets_baseline(self) -> None:
        """Test _run_baseline_if_enabled sets _test_baseline when enabled."""
        fixer_gateway = MagicMock()
        filesystem = FileSystemGateway()
        telemetry = MagicMock()
        use_case = ApplyFixesUseCase(fixer_gateway, filesystem, validate_with_tests=True, telemetry=telemetry)

        with patch.object(use_case, '_run_pytest', return_value=5):
            use_case._run_baseline_if_enabled()

        assert use_case._test_baseline == 5
        telemetry.step.assert_called()

    def test_run_baseline_if_enabled_skips_when_disabled(self) -> None:
        """Test _run_baseline_if_enabled does nothing when validate_with_tests=False."""
        fixer_gateway = MagicMock()
        filesystem = FileSystemGateway()
        use_case = ApplyFixesUseCase(fixer_gateway, filesystem, validate_with_tests=False)

        with patch.object(use_case, '_run_pytest') as mock_pytest:
            use_case._run_baseline_if_enabled()

        mock_pytest.assert_not_called()
        assert use_case._test_baseline is None

    def test_run_pytest_returns_zero_on_success(self) -> None:
        """Test _run_pytest returns 0 when all tests pass."""
        fixer_gateway = MagicMock()
        filesystem = FileSystemGateway()
        use_case = ApplyFixesUseCase(fixer_gateway, filesystem)

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=b'', stderr=b'')
            result = use_case._run_pytest()

        assert result == 0

    def test_run_pytest_returns_zero_on_no_tests(self) -> None:
        """Test _run_pytest returns 0 when no tests collected (returncode 5)."""
        fixer_gateway = MagicMock()
        filesystem = FileSystemGateway()
        use_case = ApplyFixesUseCase(fixer_gateway, filesystem)

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=5, stdout=b'', stderr=b'')
            result = use_case._run_pytest()

        assert result == 0

    def test_run_pytest_parses_failure_count(self) -> None:
        """Test _run_pytest parses failure count from output."""
        fixer_gateway = MagicMock()
        filesystem = FileSystemGateway()
        use_case = ApplyFixesUseCase(fixer_gateway, filesystem)

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout=b'3 failed, 10 passed',
                stderr=b''
            )
            result = use_case._run_pytest()

        assert result == 3

    def test_run_pytest_handles_timeout(self) -> None:
        """Test _run_pytest returns 0 on timeout."""
        fixer_gateway = MagicMock()
        filesystem = FileSystemGateway()
        use_case = ApplyFixesUseCase(fixer_gateway, filesystem)

        with patch('subprocess.run') as mock_run:
            import subprocess
            mock_run.side_effect = subprocess.TimeoutExpired('pytest', 120)
            result = use_case._run_pytest()

        assert result == 0

    def test_run_pytest_handles_file_not_found(self) -> None:
        """Test _run_pytest returns 0 when pytest not found."""
        fixer_gateway = MagicMock()
        filesystem = FileSystemGateway()
        use_case = ApplyFixesUseCase(fixer_gateway, filesystem)

        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = FileNotFoundError()
            result = use_case._run_pytest()

        assert result == 0


class TestHandleSuccessfulFix:
    """Test _handle_successful_fix logic including rollback scenarios."""

    def test_handle_successful_fix_increments_count_when_no_regression(self, tmp_path) -> None:
        """Test _handle_successful_fix increments count when tests pass."""
        test_file = tmp_path / "example.py"
        test_file.write_text("modified\n")

        fixer_gateway = MagicMock()
        filesystem = FileSystemGateway()
        telemetry = MagicMock()
        use_case = ApplyFixesUseCase(fixer_gateway, filesystem, validate_with_tests=True, telemetry=telemetry)
        use_case._test_baseline = 5

        with patch.object(use_case, '_run_pytest', return_value=5):
            count, did_rollback = use_case._handle_successful_fix(
                str(test_file), None, 0, False
            )

        assert count == 1
        assert did_rollback is False
        telemetry.step.assert_called()

    def test_handle_successful_fix_rolls_back_on_regression(self, tmp_path) -> None:
        """Test _handle_successful_fix rolls back when tests regress."""
        test_file = tmp_path / "example.py"
        backup_file = tmp_path / "example.py.bak"
        test_file.write_text("modified\n")
        backup_file.write_text("original\n")

        fixer_gateway = MagicMock()
        filesystem = FileSystemGateway()
        telemetry = MagicMock()
        use_case = ApplyFixesUseCase(fixer_gateway, filesystem, validate_with_tests=True, telemetry=telemetry)
        use_case._test_baseline = 5

        with patch.object(use_case, '_run_pytest', return_value=6):
            count, did_rollback = use_case._handle_successful_fix(
                str(test_file), str(backup_file), 0, False
            )

        assert count == 0
        assert did_rollback is True
        assert test_file.read_text() == "original\n"
        telemetry.step.assert_called()

    def test_handle_successful_fix_skips_validation_when_disabled(self) -> None:
        """Test _handle_successful_fix skips validation when validate_with_tests=False."""
        fixer_gateway = MagicMock()
        filesystem = FileSystemGateway()
        telemetry = MagicMock()
        use_case = ApplyFixesUseCase(fixer_gateway, filesystem, validate_with_tests=False, telemetry=telemetry)

        with patch.object(use_case, '_run_pytest') as mock_pytest:
            count, did_rollback = use_case._handle_successful_fix(
                "test.py", None, 0, False
            )

        mock_pytest.assert_not_called()
        assert count == 1
        assert did_rollback is False
        telemetry.step.assert_called()

    def test_handle_successful_fix_handles_no_baseline(self) -> None:
        """Test _handle_successful_fix handles case when baseline is None."""
        fixer_gateway = MagicMock()
        filesystem = FileSystemGateway()
        telemetry = MagicMock()
        use_case = ApplyFixesUseCase(fixer_gateway, filesystem, validate_with_tests=True, telemetry=telemetry)
        use_case._test_baseline = None

        with patch.object(use_case, '_run_pytest', return_value=3):
            count, did_rollback = use_case._handle_successful_fix(
                "test.py", None, 0, False
            )

        # Should not rollback when baseline is None
        assert count == 1
        assert did_rollback is False


class TestCollectTransformersFromRules:
    """Test _collect_transformers_from_rules method."""

    def test_collect_transformers_from_rules_returns_transformers(self, tmp_path) -> None:
        """Test _collect_transformers_from_rules collects transformers from rules."""
        test_file = tmp_path / "example.py"
        test_file.write_text("x = 1\n")

        fixer_gateway = MagicMock()
        filesystem = FileSystemGateway()
        use_case = ApplyFixesUseCase(fixer_gateway, filesystem)

        mock_rule = MagicMock()
        mock_violation = MagicMock()
        mock_violation.fixable = True
        mock_transformer = MagicMock()
        mock_rule.check.return_value = [mock_violation]
        mock_rule.fix.return_value = mock_transformer

        transformers, failed_fixes = use_case._collect_transformers_from_rules(
            [mock_rule], str(test_file)
        )

        assert len(transformers) == 1
        assert len(failed_fixes) == 0

    def test_collect_transformers_from_rules_handles_non_fixable_violations(self, tmp_path) -> None:
        """Test _collect_transformers_from_rules skips non-fixable violations."""
        test_file = tmp_path / "example.py"
        test_file.write_text("x = 1\n")

        fixer_gateway = MagicMock()
        filesystem = FileSystemGateway()
        use_case = ApplyFixesUseCase(fixer_gateway, filesystem)

        mock_rule = MagicMock()
        mock_violation = MagicMock()
        mock_violation.fixable = False
        mock_rule.check.return_value = [mock_violation]

        transformers, failed_fixes = use_case._collect_transformers_from_rules(
            [mock_rule], str(test_file)
        )

        assert len(transformers) == 0
        assert len(failed_fixes) == 0

    def test_collect_transformers_from_rules_handles_fix_returning_none(self, tmp_path) -> None:
        """Test _collect_transformers_from_rules handles fix() returning None."""
        test_file = tmp_path / "example.py"
        test_file.write_text("x = 1\n")

        fixer_gateway = MagicMock()
        filesystem = FileSystemGateway()
        telemetry = MagicMock()
        use_case = ApplyFixesUseCase(fixer_gateway, filesystem, telemetry=telemetry)

        mock_rule = MagicMock()
        mock_violation = MagicMock()
        mock_violation.fixable = True
        mock_violation.code = "TEST001"
        mock_violation.fix_failure_reason = "Cannot fix"
        mock_rule.check.return_value = [mock_violation]
        mock_rule.fix.return_value = None

        transformers, failed_fixes = use_case._collect_transformers_from_rules(
            [mock_rule], str(test_file)
        )

        assert len(transformers) == 0
        assert len(failed_fixes) == 1
        assert "TEST001" in failed_fixes[0]
        telemetry.error.assert_called()

    def test_collect_transformers_from_rules_handles_rule_exception(self, tmp_path) -> None:
        """Test _collect_transformers_from_rules handles exceptions from rule.check()."""
        test_file = tmp_path / "example.py"
        test_file.write_text("x = 1\n")

        fixer_gateway = MagicMock()
        filesystem = FileSystemGateway()
        telemetry = MagicMock()
        use_case = ApplyFixesUseCase(fixer_gateway, filesystem, telemetry=telemetry)

        mock_rule = MagicMock()
        mock_rule.code = "TEST001"
        mock_rule.check.side_effect = Exception("Rule error")

        transformers, failed_fixes = use_case._collect_transformers_from_rules(
            [mock_rule], str(test_file)
        )

        assert len(transformers) == 0
        assert len(failed_fixes) == 0
        telemetry.error.assert_called()

    def test_collect_transformers_from_rules_handles_parse_error(self, tmp_path) -> None:
        """Test _collect_transformers_from_rules handles file parse errors."""
        test_file = tmp_path / "invalid.py"
        test_file.write_text("invalid syntax !!!\n")

        fixer_gateway = MagicMock()
        filesystem = FileSystemGateway()
        telemetry = MagicMock()
        use_case = ApplyFixesUseCase(fixer_gateway, filesystem, telemetry=telemetry)

        mock_rule = MagicMock()

        transformers, failed_fixes = use_case._collect_transformers_from_rules(
            [mock_rule], str(test_file)
        )

        assert len(transformers) == 0
        assert len(failed_fixes) == 0
        telemetry.error.assert_called()


class TestMultiPassExecution:
    """Test multi-pass execution methods."""

    def test_execute_multi_pass_calls_all_passes(self) -> None:
        """Test execute_multi_pass calls all passes including cache clear."""
        fixer_gateway = MagicMock()
        filesystem = FileSystemGateway()
        telemetry = MagicMock()
        use_case = ApplyFixesUseCase(fixer_gateway, filesystem, telemetry=telemetry)

        with patch.object(use_case, '_run_baseline_if_enabled'), \
             patch.object(use_case, '_execute_pass1_ruff', return_value=1), \
             patch.object(use_case, '_execute_pass2_type_hints', return_value=2), \
             patch.object(use_case, '_clear_astroid_cache'), \
             patch.object(use_case, '_execute_pass3_architecture_code', return_value=3), \
             patch.object(use_case, '_execute_pass4_governance_comments', return_value=4):
            result = use_case.execute_multi_pass([], "test_path")

        assert result == 10  # 1 + 2 + 3 + 4
        telemetry.step.assert_called()

    def test_execute_pass1_ruff_returns_zero_when_disabled(self) -> None:
        """Test _execute_pass1_ruff returns 0 when ruff_adapter is None."""
        fixer_gateway = MagicMock()
        filesystem = FileSystemGateway()
        use_case = ApplyFixesUseCase(fixer_gateway, filesystem)

        result = use_case._execute_pass1_ruff("test_path")

        assert result == 0

    def test_execute_pass1_ruff_returns_zero_when_config_disabled(self) -> None:
        """Test _execute_pass1_ruff returns 0 when ruff_enabled is False."""
        fixer_gateway = MagicMock()
        filesystem = FileSystemGateway()
        ruff_adapter = MagicMock()
        config_loader = MagicMock()
        config_loader.ruff_enabled = False
        use_case = ApplyFixesUseCase(fixer_gateway, filesystem, ruff_adapter=ruff_adapter, config_loader=config_loader)

        result = use_case._execute_pass1_ruff("test_path")

        assert result == 0

    def test_execute_pass2_type_hints_filters_w9015_rules(self) -> None:
        """Test _execute_pass2_type_hints filters and applies only W9015 rules."""
        fixer_gateway = MagicMock()
        filesystem = FileSystemGateway()
        telemetry = MagicMock()
        use_case = ApplyFixesUseCase(fixer_gateway, filesystem, telemetry=telemetry)

        with patch.object(use_case, '_get_w9015_rules', return_value=[]), \
             patch.object(use_case, '_apply_rule_fixes', return_value=2):
            result = use_case._execute_pass2_type_hints([], "test_path")

        assert result == 2
        telemetry.step.assert_called()

    def test_execute_pass4_governance_comments_applies_comments(self) -> None:
        """Test _execute_pass4_governance_comments applies governance comments."""
        fixer_gateway = MagicMock()
        filesystem = FileSystemGateway()
        telemetry = MagicMock()
        check_audit = MagicMock()
        # Create a mock result with excelsior_results that has content
        mock_audit_result = MagicMock()
        mock_audit_result.is_blocked = lambda: False
        mock_audit_result.excelsior_results = [MagicMock()]  # Non-empty list
        check_audit.execute.return_value = mock_audit_result
        use_case = ApplyFixesUseCase(
            fixer_gateway, filesystem, telemetry=telemetry, check_audit_use_case=check_audit
        )

        with patch.object(use_case, '_apply_governance_comments', return_value=1):
            result = use_case._execute_pass4_governance_comments([], "test_path")

        assert result == 1
        telemetry.step.assert_called()

    def test_execute_pass4_governance_comments_skips_when_blocked(self) -> None:
        """Test _execute_pass4_governance_comments skips when audit is blocked."""
        fixer_gateway = MagicMock()
        filesystem = FileSystemGateway()
        telemetry = MagicMock()
        check_audit = MagicMock()
        check_audit.execute.return_value = MagicMock(
            is_blocked=lambda: True,
            blocked_by="test_blocker"
        )
        use_case = ApplyFixesUseCase(
            fixer_gateway, filesystem, telemetry=telemetry, check_audit_use_case=check_audit
        )

        result = use_case._execute_pass4_governance_comments([], "test_path")

        assert result == 0
        telemetry.step.assert_called()


class TestRuleHelpers:
    """Test helper methods for rule filtering and selection."""

    def test_get_w9015_rules_filters_from_list(self) -> None:
        """Test _get_w9015_rules filters W9015 rules from list."""
        fixer_gateway = MagicMock()
        filesystem = FileSystemGateway()
        use_case = ApplyFixesUseCase(fixer_gateway, filesystem)

        mock_w9015 = MagicMock()
        mock_w9015.code = "W9015"
        mock_other = MagicMock()
        mock_other.code = "W9001"

        result = use_case._get_w9015_rules([mock_w9015, mock_other])

        assert len(result) == 1
        assert result[0] == mock_w9015

    def test_get_architecture_rules_excludes_w9015(self) -> None:
        """Test _get_architecture_rules excludes W9015 rules."""
        fixer_gateway = MagicMock()
        filesystem = FileSystemGateway()
        use_case = ApplyFixesUseCase(fixer_gateway, filesystem)

        mock_w9015 = MagicMock()
        mock_w9015.code = "W9015"
        mock_other = MagicMock()
        mock_other.code = "W9001"

        result = use_case._get_architecture_rules([mock_w9015, mock_other])

        assert len(result) == 1
        assert result[0] == mock_other

    def test_apply_rule_fixes_processes_all_files(self, tmp_path) -> None:
        """Test _apply_rule_fixes processes all files in target path."""
        test_file = tmp_path / "example.py"
        test_file.write_text("x = 1\n")

        fixer_gateway = MagicMock()
        fixer_gateway.apply_fixes.return_value = True
        filesystem = FileSystemGateway()
        telemetry = MagicMock()
        use_case = ApplyFixesUseCase(fixer_gateway, filesystem, telemetry=telemetry, validate_with_tests=False)

        mock_rule = MagicMock()
        mock_violation = MagicMock()
        mock_violation.fixable = True
        mock_transformer = MagicMock()
        mock_rule.check.return_value = [mock_violation]
        mock_rule.fix.return_value = mock_transformer

        with patch.object(use_case, '_handle_successful_fix', return_value=(1, False)):
            result = use_case._apply_rule_fixes([mock_rule], str(tmp_path))

        assert result == 1
