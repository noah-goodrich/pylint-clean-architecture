"""Unit tests for enhanced ApplyFixesUseCase with confirmation, rollback, and testing."""

from unittest.mock import MagicMock, patch

import pytest

from clean_architecture_linter.use_cases.apply_fixes import ApplyFixesUseCase


@pytest.mark.slow
class TestApplyFixesEnhanced:
    """Test enhanced fix functionality."""

    def test_backup_created_before_fix(self, tmp_path):
        """Test that .bak file is created before applying fixes."""
        test_file = tmp_path / "example.py"
        test_file.write_text("x = 1\n")

        fixer_gateway = MagicMock()
        fixer_gateway.apply_fixes.return_value = True

        use_case = ApplyFixesUseCase(fixer_gateway, create_backups=True)
        use_case.execute([], str(test_file))

        backup_file = tmp_path / "example.py.bak"
        assert backup_file.exists()
        assert backup_file.read_text() == "x = 1\n"

    def test_confirmation_prompt_shown(self, tmp_path):
        """Test that confirmation is requested before applying fix."""
        test_file = tmp_path / "example.py"
        test_file.write_text("x = 1\n")

        fixer_gateway = MagicMock()
        use_case = ApplyFixesUseCase(fixer_gateway, require_confirmation=True)

        with patch('sys.stdin.isatty', return_value=True), patch(
            'builtins.input', return_value='n'
        ):
            result = use_case.execute([], str(test_file))

        # Should not apply if user says no
        fixer_gateway.apply_fixes.assert_not_called()
        assert result == 0

    def test_confirmation_yes_applies_fix(self, tmp_path):
        """Test that 'yes' confirmation proceeds with fix."""
        test_file = tmp_path / "example.py"
        test_file.write_text("x = 1\n")

        fixer_gateway = MagicMock()
        fixer_gateway.apply_fixes.return_value = True

        use_case = ApplyFixesUseCase(fixer_gateway, require_confirmation=True)

        with patch('sys.stdin.isatty', return_value=True), patch(
            'builtins.input', return_value='y'
        ):
            result = use_case.execute([], str(test_file))

        fixer_gateway.apply_fixes.assert_called_once()
        assert result == 1

    def test_pytest_validation_runs_before_fix(self, tmp_path):
        """Test that pytest runs before applying fixes."""
        test_file = tmp_path / "example.py"
        test_file.write_text("x = 1\n")

        fixer_gateway = MagicMock()
        fixer_gateway.apply_fixes.return_value = True

        use_case = ApplyFixesUseCase(fixer_gateway, validate_with_tests=True)

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout=b'', stderr=b''
            )
            use_case.execute([], str(test_file))

        # Check pytest was called
        calls = [c for c in mock_run.call_args_list if 'pytest' in str(c)]
        assert len(calls) >= 1

    def test_pytest_validation_rollback_on_new_failures(self, tmp_path):
        """Test rollback when pytest introduces new failures."""
        test_file = tmp_path / "example.py"
        test_file.write_text("x = 1\n")

        fixer_gateway = MagicMock()
        fixer_gateway.apply_fixes.return_value = True

        use_case = ApplyFixesUseCase(
            fixer_gateway,
            validate_with_tests=True,
            create_backups=True
        )

        with patch('subprocess.run') as mock_run:
            # First run: 0 failures, Second run: 1 failed (regression!)
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout=b'', stderr=b''),  # Before fix
                MagicMock(
                    returncode=1,
                    stdout=b'1 failed, 0 passed',
                    stderr=b'',
                ),  # After fix - REGRESSION
            ]

            _ = use_case.execute([], str(test_file))

        # Should detect regression and restore
        assert test_file.read_text() == "x = 1\n"  # Original content restored

    def test_skip_tests_flag_bypasses_validation(self, tmp_path):
        """Test --skip-tests flag skips pytest validation."""
        test_file = tmp_path / "example.py"
        test_file.write_text("x = 1\n")

        fixer_gateway = MagicMock()
        fixer_gateway.apply_fixes.return_value = True

        use_case = ApplyFixesUseCase(
            fixer_gateway,
            validate_with_tests=False  # skip-tests
        )

        with patch('subprocess.run') as mock_run:
            use_case.execute([], str(test_file))

        # Pytest should NOT be called
        pytest_calls = [c for c in mock_run.call_args_list if 'pytest' in str(c)]
        assert len(pytest_calls) == 0

    def test_backup_cleanup_on_success(self, tmp_path):
        """Test .bak files can be cleaned up after successful fix."""
        test_file = tmp_path / "example.py"
        test_file.write_text("x = 1\n")

        fixer_gateway = MagicMock()
        fixer_gateway.apply_fixes.return_value = True

        use_case = ApplyFixesUseCase(
            fixer_gateway,
            create_backups=True,
            cleanup_backups=True
        )

        use_case.execute([], str(test_file))

        backup_file = tmp_path / "example.py.bak"
        # Should be cleaned up automatically
        assert not backup_file.exists()

    def test_manual_fix_suggestions_returned(self, tmp_path):
        """Test manual fix suggestions are returned for non-fixable issues."""
        test_file = tmp_path / "example.py"
        test_file.write_text("x = 1\n")

        fixer_gateway = MagicMock()
        fixer_gateway.apply_fixes.return_value = False  # Cannot auto-fix
        fixer_gateway.get_manual_suggestions.return_value = [
            {
                "linter": "mypy",
                "code": "type-arg",
                "message": "Missing type annotation",
                "file": str(test_file),
                "line": 1,
                "suggestion": "Add type hint: x: int = 1"
            }
        ]

        use_case = ApplyFixesUseCase(fixer_gateway)
        manual_suggestions = use_case.get_manual_fixes(str(test_file))

        assert len(manual_suggestions) == 1
        assert manual_suggestions[0]["linter"] == "mypy"
        assert "type hint" in manual_suggestions[0]["suggestion"]


class TestAutoFixCapabilityDetection:
    """Test detection of which linters support auto-fixing."""

    def test_ruff_supports_autofix(self):
        """Test Ruff is detected as supporting auto-fix."""
        from clean_architecture_linter.infrastructure.adapters.ruff_adapter import RuffAdapter

        adapter = RuffAdapter()
        assert adapter.supports_autofix() is True
        assert "C901" in adapter.get_fixable_rules()

    def test_mypy_no_autofix(self):
        """Test Mypy does not support auto-fix."""
        from clean_architecture_linter.infrastructure.adapters.linter_adapters import MypyAdapter

        adapter = MypyAdapter()
        assert adapter.supports_autofix() is False

    def test_pylint_limited_autofix(self):
        """Test Pylint (excelsior) has limited auto-fix support."""
        from clean_architecture_linter.infrastructure.adapters.linter_adapters import ExcelsiorAdapter

        adapter = ExcelsiorAdapter()
        # Our custom fixes via LibCST
        assert adapter.supports_autofix() is True

        fixable = adapter.get_fixable_rules()
        assert "clean-arch-immutable" in fixable

    def test_import_linter_no_autofix(self):
        """Test Import-Linter does not support auto-fix."""
        from clean_architecture_linter.infrastructure.adapters.linter_adapters import ImportLinterAdapter

        adapter = ImportLinterAdapter()
        assert adapter.supports_autofix() is False


class TestManualFixInstructions:
    """Test manual fix instructions for each linter."""

    def test_mypy_manual_instructions(self):
        """Test Mypy provides manual fix instructions."""
        from clean_architecture_linter.infrastructure.adapters.linter_adapters import MypyAdapter

        adapter = MypyAdapter()
        instructions = adapter.get_manual_fix_instructions("type-arg")

        assert "type" in instructions.lower()
        assert instructions  # Non-empty

    def test_ruff_manual_instructions_for_non_fixable(self):
        """Test Ruff provides manual instructions for non-fixable rules."""
        from clean_architecture_linter.infrastructure.adapters.ruff_adapter import RuffAdapter

        adapter = RuffAdapter()
        # Some rules like ARG (unused arguments) might need manual review
        instructions = adapter.get_manual_fix_instructions("ARG001")

        assert instructions  # Should provide guidance

    def test_import_linter_manual_instructions(self):
        """Test Import-Linter provides manual fix instructions."""
        from clean_architecture_linter.infrastructure.adapters.linter_adapters import ImportLinterAdapter

        adapter = ImportLinterAdapter()
        instructions = adapter.get_manual_fix_instructions("contract-violation")

        assert "import" in instructions.lower() or "dependency" in instructions.lower()
