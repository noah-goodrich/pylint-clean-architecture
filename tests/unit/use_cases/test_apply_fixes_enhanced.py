"""Unit tests for enhanced ApplyFixesUseCase with confirmation, rollback, and testing.

All tests patch subprocess at the use case module so no real pytest is invoked.
"""

from unittest.mock import MagicMock, patch

from clean_architecture_linter.infrastructure.gateways.filesystem_gateway import FileSystemGateway
from clean_architecture_linter.use_cases.apply_fixes import ApplyFixesUseCase

# Patch target so apply_fixes._run_pytest() uses mock, not real pytest
_SUBPROCESS_RUN = "clean_architecture_linter.use_cases.apply_fixes.subprocess.run"


class TestApplyFixesEnhanced:
    """Test enhanced fix functionality."""

    def test_backup_created_before_fix(self, tmp_path) -> None:
        """Test that .bak file is created before applying fixes."""
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

        use_case = ApplyFixesUseCase(
            fixer_gateway, filesystem, create_backups=True, validate_with_tests=False
        )
        with patch(_SUBPROCESS_RUN):
            use_case.execute([mock_rule], str(test_file))

        backup_file = tmp_path / "example.py.bak"
        assert backup_file.exists()
        assert backup_file.read_text() == "x = 1\n"

    def test_confirmation_prompt_shown(self, tmp_path) -> None:
        """Test that confirmation is requested before applying fix."""
        test_file = tmp_path / "example.py"
        test_file.write_text("x = 1\n")

        fixer_gateway = MagicMock()
        filesystem = FileSystemGateway()
        use_case = ApplyFixesUseCase(fixer_gateway, filesystem, require_confirmation=True)

        with patch('sys.stdin.isatty', return_value=True), patch(
            'builtins.input', return_value='n'
        ):
            result = use_case.execute([], str(test_file))

        # Should not apply if user says no
        fixer_gateway.apply_fixes.assert_not_called()
        assert result == 0

    def test_confirmation_yes_applies_fix(self, tmp_path) -> None:
        """Test that 'yes' confirmation proceeds with fix."""
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

        use_case = ApplyFixesUseCase(
            fixer_gateway, filesystem, require_confirmation=True, validate_with_tests=False
        )

        with patch(_SUBPROCESS_RUN), patch("sys.stdin.isatty", return_value=True), patch(
            "builtins.input", return_value="y"
        ):
            result = use_case.execute([mock_rule], str(test_file))

        fixer_gateway.apply_fixes.assert_called_once()
        assert result == 1

    def test_pytest_validation_runs_before_fix(self, tmp_path) -> None:
        """Test that pytest would run before applying fixes (subprocess mocked)."""
        test_file = tmp_path / "example.py"
        test_file.write_text("x = 1\n")

        fixer_gateway = MagicMock()
        fixer_gateway.apply_fixes.return_value = True
        filesystem = FileSystemGateway()

        use_case = ApplyFixesUseCase(fixer_gateway, filesystem, validate_with_tests=True)

        with patch(_SUBPROCESS_RUN) as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout=b"", stderr=b""
            )
            use_case.execute([], str(test_file))

        mock_run.assert_called()
        (call_args,) = mock_run.call_args[0]
        assert "pytest" in str(call_args)

    def test_pytest_validation_rollback_on_new_failures(self, tmp_path) -> None:
        """Test rollback when pytest reports new failures after fix (subprocess mocked)."""
        test_file = tmp_path / "example.py"
        test_file.write_text("x = 1\n")

        fixer_gateway = MagicMock()
        fixer_gateway.apply_fixes.return_value = True

        filesystem = FileSystemGateway()
        use_case = ApplyFixesUseCase(
            fixer_gateway,
            filesystem,
            validate_with_tests=True,
            create_backups=True,
        )

        mock_rule = MagicMock()
        mock_violation = MagicMock()
        mock_violation.fixable = True
        mock_violation.location = str(test_file)
        mock_transformer = MagicMock()
        mock_rule.check.return_value = [mock_violation]
        mock_rule.fix.return_value = mock_transformer

        with patch(_SUBPROCESS_RUN) as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout=b"", stderr=b""),  # Baseline
                MagicMock(
                    returncode=1,
                    stdout=b"1 failed, 0 passed",
                    stderr=b"",
                ),  # After fix - regression
            ]

            use_case.execute([mock_rule], str(test_file))

        assert test_file.read_text() == "x = 1\n"

    def test_skip_tests_flag_bypasses_validation(self, tmp_path) -> None:
        """Test validate_with_tests=False skips pytest (subprocess not called)."""
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

        use_case = ApplyFixesUseCase(
            fixer_gateway,
            filesystem,
            validate_with_tests=False,
        )

        with patch(_SUBPROCESS_RUN) as mock_run:
            use_case.execute([mock_rule], str(test_file))

        mock_run.assert_not_called()

    def test_backup_cleanup_on_success(self, tmp_path) -> None:
        """Test .bak files can be cleaned up after successful fix."""
        test_file = tmp_path / "example.py"
        test_file.write_text("x = 1\n")

        fixer_gateway = MagicMock()
        fixer_gateway.apply_fixes.return_value = True

        filesystem = FileSystemGateway()
        use_case = ApplyFixesUseCase(
            fixer_gateway,
            filesystem,
            create_backups=True,
            cleanup_backups=True,
            validate_with_tests=False,
        )

        with patch(_SUBPROCESS_RUN):
            use_case.execute([], str(test_file))

        backup_file = tmp_path / "example.py.bak"
        # Should be cleaned up automatically
        assert not backup_file.exists()

    def test_manual_fix_suggestions_returned(self, tmp_path) -> None:
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

        filesystem = FileSystemGateway()
        use_case = ApplyFixesUseCase(fixer_gateway, filesystem)
        manual_suggestions = use_case.get_manual_fixes(str(test_file))

        assert len(manual_suggestions) == 1
        assert manual_suggestions[0]["linter"] == "mypy"
        assert "type hint" in manual_suggestions[0]["suggestion"]


class TestAutoFixCapabilityDetection:
    """Test detection of which linters support auto-fixing."""

    def test_ruff_supports_autofix(self) -> None:
        """Test Ruff is detected as supporting auto-fix."""
        from clean_architecture_linter.infrastructure.adapters.ruff_adapter import RuffAdapter

        adapter = RuffAdapter()
        assert adapter.supports_autofix() is True
        assert "C901" in adapter.get_fixable_rules()

    def test_mypy_no_autofix(self) -> None:
        """Test Mypy does not support auto-fix."""
        from clean_architecture_linter.infrastructure.adapters.linter_adapters import MypyAdapter

        adapter = MypyAdapter()
        assert adapter.supports_autofix() is False

    def test_pylint_limited_autofix(self) -> None:
        """Test Pylint (excelsior) has limited auto-fix support."""
        from clean_architecture_linter.infrastructure.adapters.linter_adapters import ExcelsiorAdapter

        adapter = ExcelsiorAdapter()
        # Our custom fixes via LibCST
        assert adapter.supports_autofix() is True

        fixable = adapter.get_fixable_rules()
        assert "clean-arch-immutable" in fixable

    def test_import_linter_no_autofix(self) -> None:
        """Test Import-Linter does not support auto-fix."""
        from clean_architecture_linter.infrastructure.adapters.linter_adapters import ImportLinterAdapter

        adapter = ImportLinterAdapter()
        assert adapter.supports_autofix() is False


class TestManualFixInstructions:
    """Test manual fix instructions for each linter."""

    def test_mypy_manual_instructions(self) -> None:
        """Test Mypy provides manual fix instructions."""
        from clean_architecture_linter.infrastructure.adapters.linter_adapters import MypyAdapter

        adapter = MypyAdapter()
        instructions = adapter.get_manual_fix_instructions("type-arg")

        assert "type" in instructions.lower()
        assert instructions  # Non-empty

    def test_ruff_manual_instructions_for_non_fixable(self) -> None:
        """Test Ruff provides manual instructions for non-fixable rules."""
        from clean_architecture_linter.infrastructure.adapters.ruff_adapter import RuffAdapter

        adapter = RuffAdapter()
        # Some rules like ARG (unused arguments) might need manual review
        instructions = adapter.get_manual_fix_instructions("ARG001")

        assert instructions  # Should provide guidance

    def test_import_linter_manual_instructions(self) -> None:
        """Test Import-Linter provides manual fix instructions."""
        from clean_architecture_linter.infrastructure.adapters.linter_adapters import ImportLinterAdapter

        adapter = ImportLinterAdapter()
        instructions = adapter.get_manual_fix_instructions(
            "contract-violation")

        assert "import" in instructions.lower() or "dependency" in instructions.lower()
