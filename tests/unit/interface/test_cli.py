"""Unit tests for Typer-based CLI interface."""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from clean_architecture_linter.domain.config import ConfigurationLoader
from clean_architecture_linter.domain.entities import AuditResult, LinterResult
from clean_architecture_linter.interface.cli import app, _resolve_target_path

runner = CliRunner()


class TestResolveTargetPath:
    """Test path resolution logic."""

    def test_resolve_with_explicit_path(self) -> None:
        """Test that explicit path is returned as-is."""
        result = _resolve_target_path(Path("custom/path"))
        assert result == "custom/path"

    def test_resolve_defaults_to_src_when_exists(self, tmp_path: Path) -> None:
        """Test that src/ is used when it exists."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        original_cwd = Path.cwd()
        try:
            import os

            os.chdir(tmp_path)
            result = _resolve_target_path(None)
            assert result == "src"
        finally:
            os.chdir(original_cwd)

    def test_resolve_defaults_to_dot_when_src_missing(self, tmp_path: Path) -> None:
        """Test that . is used when src/ doesn't exist."""
        original_cwd = Path.cwd()
        try:
            import os

            os.chdir(tmp_path)
            result = _resolve_target_path(None)
            assert result == "."
        finally:
            os.chdir(original_cwd)


class TestCheckCommand:
    """Test the check command."""

    @patch("clean_architecture_linter.interface.cli.ExcelsiorContainer")
    @patch("clean_architecture_linter.interface.cli.ConfigurationLoader")
    @patch("clean_architecture_linter.interface.cli.CheckAuditUseCase")
    def test_check_command_executes_gated_audit(
        self,
        mock_use_case_class,
        mock_config_loader_class,
        mock_container_class,
    ) -> None:
        """Test that check command executes gated sequential audit."""
        # Setup mocks
        mock_container = Mock()
        mock_container_class.return_value = mock_container

        mock_config_loader = Mock(spec=ConfigurationLoader)
        mock_config_loader.ruff_enabled = True
        mock_config_loader_class.return_value = mock_config_loader

        # Mock adapters and services
        mock_mypy = Mock()
        mock_excelsior = Mock()
        mock_import_linter = Mock()
        mock_ruff = Mock()
        mock_reporter = Mock()
        mock_audit_trail = Mock()
        mock_telemetry = Mock()

        mock_container.get.side_effect = lambda key: {
            "MypyAdapter": mock_mypy,
            "ExcelsiorAdapter": mock_excelsior,
            "ImportLinterAdapter": mock_import_linter,
            "RuffAdapter": mock_ruff,
            "AuditReporter": mock_reporter,
            "AuditTrailService": mock_audit_trail,
            "TelemetryPort": mock_telemetry,
        }[key]

        # Mock use case instance
        mock_use_case_instance = Mock()
        mock_use_case_instance.execute.return_value = AuditResult(
            ruff_results=[],
            mypy_results=[],
            excelsior_results=[],
            ruff_enabled=True,
            blocked_by=None,
        )
        mock_use_case_class.return_value = mock_use_case_instance

        # Execute
        result = runner.invoke(app, ["check", "src"])

        # Verify use case was created correctly
        mock_use_case_class.assert_called_once()
        mock_use_case_instance.execute.assert_called_once_with("src")

        # Verify reporter and audit trail were called
        mock_reporter.report_audit.assert_called_once()
        mock_audit_trail.save_audit_trail.assert_called_once()

        # Verify telemetry handshake was called
        mock_telemetry.handshake.assert_called_once()

        # Should exit with 0 (no violations)
        assert result.exit_code == 0

    @patch("clean_architecture_linter.interface.cli.ExcelsiorContainer")
    @patch("clean_architecture_linter.interface.cli.ConfigurationLoader")
    @patch("clean_architecture_linter.interface.cli.CheckAuditUseCase")
    def test_check_command_exits_with_error_on_violations(
        self,
        mock_use_case_class,
        mock_config_loader_class,
        mock_container_class,
    ) -> None:
        """Test that check command exits with error code when violations found."""
        # Setup mocks
        mock_container = Mock()
        mock_container_class.return_value = mock_container

        mock_config_loader = Mock(spec=ConfigurationLoader)
        mock_config_loader.ruff_enabled = True
        mock_config_loader_class.return_value = mock_config_loader

        mock_telemetry = Mock()
        mock_reporter = Mock()
        mock_audit_trail = Mock()

        mock_container.get.side_effect = lambda key: {
            "MypyAdapter": Mock(),
            "ExcelsiorAdapter": Mock(),
            "ImportLinterAdapter": Mock(),
            "RuffAdapter": Mock(),
            "AuditReporter": mock_reporter,
            "AuditTrailService": mock_audit_trail,
            "TelemetryPort": mock_telemetry,
        }[key]

        # Mock use case with violations
        mock_use_case_instance = Mock()
        mock_use_case_instance.execute.return_value = AuditResult(
            ruff_results=[LinterResult("R001", "Ruff violation", ["file.py:1"])],
            mypy_results=[],
            excelsior_results=[],
            ruff_enabled=True,
            blocked_by="ruff",
        )
        mock_use_case_class.return_value = mock_use_case_instance

        # Execute
        result = runner.invoke(app, ["check", "src"])

        # Should exit with 1 (violations found)
        assert result.exit_code == 1

    @patch("clean_architecture_linter.interface.cli.ExcelsiorContainer")
    @patch("clean_architecture_linter.interface.cli.ConfigurationLoader")
    @patch("clean_architecture_linter.interface.cli.CheckAuditUseCase")
    def test_check_command_with_default_path(
        self,
        mock_use_case_class,
        mock_config_loader_class,
        mock_container_class,
    ) -> None:
        """Test that check command uses default path resolution."""
        # Setup mocks
        mock_container = Mock()
        mock_container_class.return_value = mock_container

        mock_config_loader = Mock(spec=ConfigurationLoader)
        mock_config_loader.ruff_enabled = True
        mock_config_loader_class.return_value = mock_config_loader

        mock_telemetry = Mock()
        mock_reporter = Mock()
        mock_audit_trail = Mock()

        mock_container.get.side_effect = lambda key: {
            "MypyAdapter": Mock(),
            "ExcelsiorAdapter": Mock(),
            "ImportLinterAdapter": Mock(),
            "RuffAdapter": Mock(),
            "AuditReporter": mock_reporter,
            "AuditTrailService": mock_audit_trail,
            "TelemetryPort": mock_telemetry,
        }[key]

        mock_use_case_instance = Mock()
        mock_use_case_instance.execute.return_value = AuditResult(
            ruff_results=[],
            mypy_results=[],
            excelsior_results=[],
            ruff_enabled=True,
            blocked_by=None,
        )
        mock_use_case_class.return_value = mock_use_case_instance

        # Execute without path argument
        result = runner.invoke(app, ["check"])

        # Verify path resolution was called (will use default)
        mock_use_case_instance.execute.assert_called_once()
        assert result.exit_code == 0


class TestFixCommand:
    """Test the fix command."""

    @patch("clean_architecture_linter.interface.cli._run_fix_excelsior")
    @patch("clean_architecture_linter.interface.cli.ExcelsiorContainer")
    def test_fix_command_calls_excelsior_fixer(
        self, mock_container_class, mock_run_fix_excelsior
    ) -> None:
        """Test that fix command calls excelsior fixer by default."""
        mock_container = Mock()
        mock_telemetry = Mock()
        mock_container.get.return_value = mock_telemetry
        mock_container_class.return_value = mock_container

        result = runner.invoke(app, ["fix", "src"])

        # Should call excelsior fixer
        mock_run_fix_excelsior.assert_called_once()
        mock_telemetry.handshake.assert_called_once()

    @patch("clean_architecture_linter.interface.cli._run_fix_ruff")
    @patch("clean_architecture_linter.interface.cli.ExcelsiorContainer")
    def test_fix_command_with_ruff_linter(
        self, mock_container_class, mock_run_fix_ruff
    ) -> None:
        """Test that fix command calls ruff fixer when linter=ruff."""
        mock_container = Mock()
        mock_telemetry = Mock()
        mock_container.get.return_value = mock_telemetry
        mock_container_class.return_value = mock_container

        result = runner.invoke(app, ["fix", "src", "--linter", "ruff"])

        # Should call ruff fixer
        mock_run_fix_ruff.assert_called_once()

    @patch("clean_architecture_linter.interface.cli._run_fix_manual_only")
    @patch("clean_architecture_linter.interface.cli.ExcelsiorContainer")
    def test_fix_command_with_manual_only(
        self, mock_container_class, mock_run_fix_manual_only
    ) -> None:
        """Test that fix command shows manual suggestions when --manual-only is set."""
        mock_container = Mock()
        mock_telemetry = Mock()
        mock_container.get.return_value = mock_telemetry
        mock_container_class.return_value = mock_container

        result = runner.invoke(app, ["fix", "src", "--manual-only"])

        # Should call manual only handler
        mock_run_fix_manual_only.assert_called_once()


class TestInitCommand:
    """Test the init command."""

    @patch("clean_architecture_linter.interface.cli.InitProjectUseCase")
    @patch("clean_architecture_linter.interface.cli.ExcelsiorContainer")
    def test_init_command_executes_use_case(
        self, mock_container_class, mock_use_case_class
    ) -> None:
        """Test that init command executes InitProjectUseCase."""
        mock_container = Mock()
        mock_telemetry = Mock()
        mock_scaffolder = Mock()
        mock_container.get.side_effect = lambda key: {
            "TelemetryPort": mock_telemetry,
            "Scaffolder": mock_scaffolder,
        }[key]
        mock_container_class.return_value = mock_container

        mock_use_case_instance = Mock()
        mock_use_case_class.return_value = mock_use_case_instance

        result = runner.invoke(app, ["init"])

        # Verify use case was created and executed
        mock_use_case_class.assert_called_once_with(mock_scaffolder, mock_telemetry)
        mock_use_case_instance.execute.assert_called_once_with(
            template=None, check_layers=False
        )
        mock_telemetry.handshake.assert_called_once()

    @patch("clean_architecture_linter.interface.cli.InitProjectUseCase")
    @patch("clean_architecture_linter.interface.cli.ExcelsiorContainer")
    def test_init_command_with_options(
        self, mock_container_class, mock_use_case_class
    ) -> None:
        """Test that init command passes options to use case."""
        mock_container = Mock()
        mock_telemetry = Mock()
        mock_scaffolder = Mock()
        mock_container.get.side_effect = lambda key: {
            "TelemetryPort": mock_telemetry,
            "Scaffolder": mock_scaffolder,
        }[key]
        mock_container_class.return_value = mock_container

        mock_use_case_instance = Mock()
        mock_use_case_class.return_value = mock_use_case_instance

        result = runner.invoke(
            app, ["init", "--template", "fastapi", "--check-layers"]
        )

        # Verify use case was called with options
        mock_use_case_instance.execute.assert_called_once_with(
            template="fastapi", check_layers=True
        )

    @patch("clean_architecture_linter.interface.cli.InitProjectUseCase")
    @patch("clean_architecture_linter.interface.cli.ExcelsiorContainer")
    def test_init_command_with_template_only(
        self, mock_container_class, mock_use_case_class
    ) -> None:
        """Test init command with template option only."""
        mock_container = Mock()
        mock_telemetry = Mock()
        mock_scaffolder = Mock()
        mock_container.get.side_effect = lambda key: {
            "TelemetryPort": mock_telemetry,
            "Scaffolder": mock_scaffolder,
        }[key]
        mock_container_class.return_value = mock_container

        mock_use_case_instance = Mock()
        mock_use_case_class.return_value = mock_use_case_instance

        result = runner.invoke(app, ["init", "--template", "sqlalchemy"])

        mock_use_case_instance.execute.assert_called_once_with(
            template="sqlalchemy", check_layers=False
        )

    @patch("clean_architecture_linter.interface.cli.InitProjectUseCase")
    @patch("clean_architecture_linter.interface.cli.ExcelsiorContainer")
    def test_init_command_with_check_layers_only(
        self, mock_container_class, mock_use_case_class
    ) -> None:
        """Test init command with check-layers option only."""
        mock_container = Mock()
        mock_telemetry = Mock()
        mock_scaffolder = Mock()
        mock_container.get.side_effect = lambda key: {
            "TelemetryPort": mock_telemetry,
            "Scaffolder": mock_scaffolder,
        }[key]
        mock_container_class.return_value = mock_container

        mock_use_case_instance = Mock()
        mock_use_case_class.return_value = mock_use_case_instance

        result = runner.invoke(app, ["init", "--check-layers"])

        mock_use_case_instance.execute.assert_called_once_with(
            template=None, check_layers=True
        )


class TestGatedAuditLogic:
    """Test gated sequential audit logic."""

    @patch("clean_architecture_linter.interface.cli.ExcelsiorContainer")
    @patch("clean_architecture_linter.interface.cli.ConfigurationLoader")
    @patch("clean_architecture_linter.interface.cli.CheckAuditUseCase")
    def test_gated_stop_on_ruff_violations(
        self,
        mock_use_case_class,
        mock_config_loader_class,
        mock_container_class,
    ) -> None:
        """Test that audit stops when Ruff finds violations."""
        mock_container = Mock()
        mock_container_class.return_value = mock_container

        mock_config_loader = Mock(spec=ConfigurationLoader)
        mock_config_loader.ruff_enabled = True
        mock_config_loader_class.return_value = mock_config_loader

        mock_telemetry = Mock()
        mock_reporter = Mock()
        mock_audit_trail = Mock()

        mock_container.get.side_effect = lambda key: {
            "MypyAdapter": Mock(),
            "ExcelsiorAdapter": Mock(),
            "ImportLinterAdapter": Mock(),
            "RuffAdapter": Mock(),
            "AuditReporter": mock_reporter,
            "AuditTrailService": mock_audit_trail,
            "TelemetryPort": mock_telemetry,
        }[key]

        # Mock blocked result from Ruff
        mock_use_case_instance = Mock()
        mock_use_case_instance.execute.return_value = AuditResult(
            ruff_results=[LinterResult("R001", "Ruff violation", ["file.py:1"])],
            mypy_results=[],
            excelsior_results=[],
            ruff_enabled=True,
            blocked_by="ruff",
        )
        mock_use_case_class.return_value = mock_use_case_instance

        result = runner.invoke(app, ["check", "src"])

        # Verify blocked message was shown
        assert "blocked" in result.stdout.lower() or result.exit_code == 1
        # Should exit with error
        assert result.exit_code == 1


class TestFixManualOnly:
    """Test manual-only fix suggestions."""

    @patch("clean_architecture_linter.interface.cli.ExcelsiorContainer")
    def test_manual_only_all_linters(self, mock_container_class) -> None:
        """Test manual-only with all linters."""
        from clean_architecture_linter.interface.cli import _run_fix_manual_only

        mock_container = Mock()
        mock_telemetry = Mock()
        mock_ruff_adapter = Mock()
        mock_mypy_adapter = Mock()
        mock_excelsior_adapter = Mock()
        mock_import_linter_adapter = Mock()

        mock_ruff_adapter.gather_results.return_value = [
            LinterResult("R001", "Ruff issue", ["file.py:1"])
        ]
        mock_ruff_adapter.supports_autofix.return_value = True
        mock_ruff_adapter.get_fixable_rules.return_value = []
        mock_ruff_adapter.get_manual_fix_instructions.return_value = "Fix it"
        mock_mypy_adapter.gather_results.return_value = []
        mock_excelsior_adapter.gather_results.return_value = []
        mock_import_linter_adapter.gather_results.return_value = []

        mock_container.get.side_effect = lambda key: {
            "RuffAdapter": mock_ruff_adapter,
            "MypyAdapter": mock_mypy_adapter,
            "ExcelsiorAdapter": mock_excelsior_adapter,
            "ImportLinterAdapter": mock_import_linter_adapter,
        }[key]
        mock_container_class.return_value = mock_container

        _run_fix_manual_only(mock_telemetry, "src", "all")

        # Verify all adapters were queried
        mock_telemetry.step.assert_called_with("📋 Gathering manual fix suggestions from all linters...")

    @patch("clean_architecture_linter.interface.cli.ExcelsiorContainer")
    def test_manual_only_ruff_only(self, mock_container_class) -> None:
        """Test manual-only with ruff linter only."""
        from clean_architecture_linter.interface.cli import _run_fix_manual_only

        mock_container = Mock()
        mock_telemetry = Mock()
        mock_ruff_adapter = Mock()
        mock_ruff_adapter.gather_results.return_value = []
        mock_container.get.return_value = mock_ruff_adapter
        mock_container_class.return_value = mock_container

        _run_fix_manual_only(mock_telemetry, "src", "ruff")

        mock_telemetry.step.assert_called_with("📋 Gathering manual fix suggestions from Ruff...")

    @patch("clean_architecture_linter.interface.cli.ExcelsiorContainer")
    def test_manual_only_excelsior_suite(self, mock_container_class) -> None:
        """Test manual-only with excelsior suite linters."""
        from clean_architecture_linter.interface.cli import _run_fix_manual_only

        mock_container = Mock()
        mock_telemetry = Mock()
        mock_mypy = Mock()
        mock_excelsior = Mock()
        mock_import_linter = Mock()
        mock_mypy.gather_results.return_value = []
        mock_excelsior.gather_results.return_value = []
        mock_import_linter.gather_results.return_value = []

        mock_container.get.side_effect = lambda key: {
            "RuffAdapter": Mock(),
            "MypyAdapter": mock_mypy,
            "ExcelsiorAdapter": mock_excelsior,
            "ImportLinterAdapter": mock_import_linter,
        }[key]
        mock_container_class.return_value = mock_container

        _run_fix_manual_only(mock_telemetry, "src", "excelsior")

        mock_telemetry.step.assert_called_with("📋 Gathering manual fix suggestions from Excelsior suite...")

    @patch("clean_architecture_linter.interface.cli.ExcelsiorContainer")
    def test_manual_only_with_results(self, mock_container_class) -> None:
        """Test manual-only displays results correctly."""
        from clean_architecture_linter.interface.cli import _run_fix_manual_only

        mock_container = Mock()
        mock_telemetry = Mock()
        mock_adapter = Mock()
        results = [
            LinterResult("R001", "Test violation", ["file.py:1", "file.py:2", "file.py:3", "file.py:4", "file.py:5", "file.py:6"])
        ]
        mock_adapter.gather_results.return_value = results
        mock_adapter.supports_autofix.return_value = False
        mock_adapter.get_fixable_rules.return_value = []
        mock_adapter.get_manual_fix_instructions.return_value = "Manual fix instructions"

        mock_mypy = Mock()
        mock_mypy.gather_results.return_value = []
        mock_excelsior = Mock()
        mock_excelsior.gather_results.return_value = []
        mock_import_linter = Mock()
        mock_import_linter.gather_results.return_value = []

        mock_container.get.side_effect = lambda key: {
            "RuffAdapter": mock_adapter,
            "MypyAdapter": mock_mypy,
            "ExcelsiorAdapter": mock_excelsior,
            "ImportLinterAdapter": mock_import_linter,
        }[key]
        mock_container_class.return_value = mock_container

        _run_fix_manual_only(mock_telemetry, "src", "all")

        # Verify adapter was called
        mock_adapter.gather_results.assert_called_once_with("src")


class TestFixRuff:
    """Test Ruff-only fixer."""

    @patch("clean_architecture_linter.interface.cli.sys.exit")
    @patch("clean_architecture_linter.interface.cli.ExcelsiorContainer")
    def test_fix_ruff_success(self, mock_container_class, mock_exit) -> None:
        """Test successful Ruff fix."""
        from clean_architecture_linter.interface.cli import _run_fix_ruff

        mock_container = Mock()
        mock_telemetry = Mock()
        mock_ruff_adapter = Mock()
        mock_ruff_adapter.apply_fixes.return_value = True

        mock_container.get.return_value = mock_ruff_adapter
        mock_container_class.return_value = mock_container

        _run_fix_ruff(mock_telemetry, "src")

        mock_telemetry.step.assert_any_call("🔧 Applying Ruff fixes...")
        mock_telemetry.step.assert_any_call("✅ Ruff fixes complete. Run 'excelsior check' to verify.")
        mock_ruff_adapter.apply_fixes.assert_called_once_with(Path("src"))
        mock_exit.assert_called_once_with(0)

    @patch("clean_architecture_linter.interface.cli.sys.exit")
    @patch("clean_architecture_linter.interface.cli.ExcelsiorContainer")
    def test_fix_ruff_failure(self, mock_container_class, mock_exit) -> None:
        """Test failed Ruff fix."""
        from clean_architecture_linter.interface.cli import _run_fix_ruff

        mock_container = Mock()
        mock_telemetry = Mock()
        mock_ruff_adapter = Mock()
        mock_ruff_adapter.apply_fixes.return_value = False

        mock_container.get.return_value = mock_ruff_adapter
        mock_container_class.return_value = mock_container

        _run_fix_ruff(mock_telemetry, "src")

        mock_exit.assert_called_once_with(1)


class TestFixExcelsior:
    """Test Excelsior multi-pass fixer."""

    @patch("clean_architecture_linter.interface.cli.sys.exit")
    @patch("clean_architecture_linter.interface.cli.ApplyFixesUseCase")
    @patch("clean_architecture_linter.domain.rules.type_hints.MissingTypeHintRule")
    @patch("clean_architecture_linter.interface.cli.CheckAuditUseCase")
    @patch("clean_architecture_linter.interface.cli.ConfigurationLoader")
    @patch("clean_architecture_linter.interface.cli.ExcelsiorContainer")
    def test_fix_excelsior_executes_multi_pass(
        self,
        mock_container_class,
        mock_config_loader_class,
        mock_check_audit_class,
        mock_rule_class,
        mock_use_case_class,
        mock_exit,
    ) -> None:
        """Test that excelsior fixer executes multi-pass."""
        from clean_architecture_linter.interface.cli import _run_fix_excelsior

        mock_container = Mock()
        mock_telemetry = Mock()
        mock_config_loader = Mock()
        mock_config_loader_class.return_value = mock_config_loader

        mock_astroid = Mock()
        mock_ruff = Mock()
        mock_filesystem = Mock()
        mock_mypy = Mock()
        mock_excelsior = Mock()
        mock_import_linter = Mock()

        mock_container.get.side_effect = lambda key: {
            "AstroidGateway": mock_astroid,
            "RuffAdapter": mock_ruff,
            "FileSystemGateway": mock_filesystem,
            "MypyAdapter": mock_mypy,
            "ExcelsiorAdapter": mock_excelsior,
            "ImportLinterAdapter": mock_import_linter,
        }[key]
        mock_container_class.return_value = mock_container

        mock_use_case_instance = Mock()
        mock_use_case_instance.execute_multi_pass.return_value = 5
        mock_use_case_class.return_value = mock_use_case_instance

        mock_rule_instance = Mock()
        mock_rule_class.return_value = mock_rule_instance

        _run_fix_excelsior(mock_telemetry, "src", False, False, False, False)

        # Verify use case was created and executed
        mock_use_case_class.assert_called_once()
        mock_use_case_instance.execute_multi_pass.assert_called_once()
        mock_telemetry.step.assert_any_call("✅ Successfully fixed 5 file(s)")
        mock_exit.assert_called_once_with(0)

    @patch("clean_architecture_linter.interface.cli.sys.exit")
    @patch("clean_architecture_linter.interface.cli.ApplyFixesUseCase")
    @patch("clean_architecture_linter.domain.rules.type_hints.MissingTypeHintRule")
    @patch("clean_architecture_linter.interface.cli.CheckAuditUseCase")
    @patch("clean_architecture_linter.interface.cli.ConfigurationLoader")
    @patch("clean_architecture_linter.interface.cli.ExcelsiorContainer")
    def test_fix_excelsior_with_options(
        self,
        mock_container_class,
        mock_config_loader_class,
        mock_check_audit_class,
        mock_rule_class,
        mock_use_case_class,
        mock_exit,
    ) -> None:
        """Test excelsior fixer with various options."""
        from clean_architecture_linter.interface.cli import _run_fix_excelsior

        mock_container = Mock()
        mock_telemetry = Mock()
        mock_config_loader = Mock()
        mock_config_loader_class.return_value = mock_config_loader

        mock_container.get.side_effect = lambda key: {
            "AstroidGateway": Mock(),
            "RuffAdapter": Mock(),
            "FileSystemGateway": Mock(),
            "MypyAdapter": Mock(),
            "ExcelsiorAdapter": Mock(),
            "ImportLinterAdapter": Mock(),
        }[key]
        mock_container_class.return_value = mock_container

        mock_use_case_instance = Mock()
        mock_use_case_instance.execute_multi_pass.return_value = 0
        mock_use_case_class.return_value = mock_use_case_instance

        mock_rule_class.return_value = Mock()

        # Test with all options enabled
        _run_fix_excelsior(mock_telemetry, "src", True, True, True, True)

        # Verify use case was created with correct options
        call_kwargs = mock_use_case_class.call_args[1]
        assert call_kwargs["require_confirmation"] is True
        assert call_kwargs["create_backups"] is False  # no_backup=True
        assert call_kwargs["validate_with_tests"] is False  # skip_tests=True
        assert call_kwargs["cleanup_backups"] is True

        mock_telemetry.step.assert_any_call("ℹ️  No fixes applied")
