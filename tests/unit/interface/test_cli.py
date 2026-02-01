"""Unit tests for Typer-based CLI interface."""

from pathlib import Path
from unittest.mock import Mock, patch

from typer.testing import CliRunner

from clean_architecture_linter.domain.config import ConfigurationLoader
from clean_architecture_linter.domain.entities import AuditResult, LinterResult
from clean_architecture_linter.interface.cli import (
    CLIDependencies,
    _resolve_target_path,
    create_app,
)

runner = CliRunner()


def _make_mock_deps(**overrides) -> CLIDependencies:
    """Create CLIDependencies with mock adapters/services for testing."""
    mock_telemetry = Mock()
    mock_reporter = Mock()
    mock_audit_trail = Mock()
    defaults: dict = {
        "telemetry": mock_telemetry,
        "mypy_adapter": Mock(),
        "excelsior_adapter": Mock(),
        "import_linter_adapter": Mock(),
        "ruff_adapter": Mock(),
        "reporter": mock_reporter,
        "audit_trail_service": mock_audit_trail,
        "scaffolder": Mock(),
        "astroid_gateway": Mock(),
        "filesystem": Mock(),
        "fixer_gateway": Mock(),
    }
    defaults.update(overrides)
    return CLIDependencies(**defaults)


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

    @patch("clean_architecture_linter.interface.cli.ConfigurationLoader")
    @patch("clean_architecture_linter.interface.cli.CheckAuditUseCase")
    def test_check_command_executes_gated_audit(
        self,
        mock_use_case_class,
        mock_config_loader_class,
    ) -> None:
        """Test that check command executes gated sequential audit."""
        mock_config_loader = Mock(spec=ConfigurationLoader)
        mock_config_loader.ruff_enabled = True
        mock_config_loader_class.return_value = mock_config_loader

        deps = _make_mock_deps()
        mock_use_case_instance = Mock()
        mock_use_case_instance.execute.return_value = AuditResult(
            ruff_results=[],
            mypy_results=[],
            excelsior_results=[],
            ruff_enabled=True,
            blocked_by=None,
        )
        mock_use_case_class.return_value = mock_use_case_instance

        app = create_app(deps)
        result = runner.invoke(app, ["check", "src"])

        mock_use_case_class.assert_called_once()
        mock_use_case_instance.execute.assert_called_once_with("src")
        deps.reporter.report_audit.assert_called_once()
        deps.audit_trail_service.save_audit_trail.assert_called_once()
        deps.telemetry.handshake.assert_called_once()
        assert result.exit_code == 0

    @patch("clean_architecture_linter.interface.cli.ConfigurationLoader")
    @patch("clean_architecture_linter.interface.cli.CheckAuditUseCase")
    def test_check_command_exits_with_error_on_violations(
        self,
        mock_use_case_class,
        mock_config_loader_class,
    ) -> None:
        """Test that check command exits with error code when violations found."""
        mock_config_loader = Mock(spec=ConfigurationLoader)
        mock_config_loader.ruff_enabled = True
        mock_config_loader_class.return_value = mock_config_loader

        deps = _make_mock_deps()
        mock_use_case_instance = Mock()
        mock_use_case_instance.execute.return_value = AuditResult(
            ruff_results=[LinterResult("R001", "Ruff violation", ["file.py:1"])],
            mypy_results=[],
            excelsior_results=[],
            ruff_enabled=True,
            blocked_by="ruff",
        )
        mock_use_case_class.return_value = mock_use_case_instance

        app = create_app(deps)
        result = runner.invoke(app, ["check", "src"])
        assert result.exit_code == 1

    @patch("clean_architecture_linter.interface.cli.ConfigurationLoader")
    @patch("clean_architecture_linter.interface.cli.CheckAuditUseCase")
    def test_check_command_with_default_path(
        self,
        mock_use_case_class,
        mock_config_loader_class,
    ) -> None:
        """Test that check command uses default path resolution."""
        mock_config_loader = Mock(spec=ConfigurationLoader)
        mock_config_loader.ruff_enabled = True
        mock_config_loader_class.return_value = mock_config_loader

        deps = _make_mock_deps()
        mock_use_case_instance = Mock()
        mock_use_case_instance.execute.return_value = AuditResult(
            ruff_results=[],
            mypy_results=[],
            excelsior_results=[],
            ruff_enabled=True,
            blocked_by=None,
        )
        mock_use_case_class.return_value = mock_use_case_instance

        app = create_app(deps)
        result = runner.invoke(app, ["check"])
        mock_use_case_instance.execute.assert_called_once()
        assert result.exit_code == 0


class TestFixCommand:
    """Test the fix command."""

    @patch("clean_architecture_linter.interface.cli.ApplyFixesUseCase")
    @patch("clean_architecture_linter.interface.cli.CheckAuditUseCase")
    @patch("clean_architecture_linter.interface.cli.ConfigurationLoader")
    @patch("clean_architecture_linter.domain.rules.type_hints.MissingTypeHintRule")
    @patch("clean_architecture_linter.domain.rules.immutability.DomainImmutabilityRule")
    def test_fix_command_calls_excelsior_fixer(
        self,
        mock_immutability_rule,
        mock_type_hint_rule,
        mock_config_loader,
        mock_check_audit,
        mock_apply_fixes,
    ) -> None:
        """Test that fix command calls excelsior fixer by default."""
        deps = _make_mock_deps()
        mock_apply_fixes_instance = Mock()
        mock_apply_fixes_instance.execute_multi_pass.return_value = 0
        mock_apply_fixes.return_value = mock_apply_fixes_instance

        mock_check_audit_instance = Mock()
        mock_check_audit_instance.execute.return_value = AuditResult()
        mock_check_audit.return_value = mock_check_audit_instance

        app = create_app(deps)
        runner.invoke(app, ["fix", "src"])

        mock_apply_fixes.assert_called_once()
        deps.telemetry.handshake.assert_called_once()

    def test_fix_command_with_ruff_linter(self) -> None:
        """Test that fix command calls ruff fixer when linter=ruff."""
        mock_ruff = Mock()
        mock_ruff.apply_fixes.return_value = True
        deps = _make_mock_deps(ruff_adapter=mock_ruff)

        app = create_app(deps)
        result = runner.invoke(app, ["fix", "src", "--linter", "ruff"])
        mock_ruff.apply_fixes.assert_called_once()
        assert result.exit_code == 0

    def test_fix_command_with_manual_only(self) -> None:
        """Test that fix command shows manual suggestions when --manual-only is set."""
        deps = _make_mock_deps()
        for adapter in (deps.ruff_adapter, deps.mypy_adapter, deps.excelsior_adapter, deps.import_linter_adapter):
            adapter.gather_results.return_value = []

        app = create_app(deps)
        runner.invoke(app, ["fix", "src", "--manual-only"])
        deps.telemetry.handshake.assert_called_once()


class TestInitCommand:
    """Test the init command."""

    @patch("clean_architecture_linter.interface.cli.InitProjectUseCase")
    def test_init_command_executes_use_case(self, mock_use_case_class) -> None:
        """Test that init command executes InitProjectUseCase."""
        deps = _make_mock_deps()
        mock_use_case_instance = Mock()
        mock_use_case_class.return_value = mock_use_case_instance

        app = create_app(deps)
        runner.invoke(app, ["init"])

        mock_use_case_class.assert_called_once_with(deps.scaffolder, deps.telemetry)
        mock_use_case_instance.execute.assert_called_once_with(template=None, check_layers=False)
        deps.telemetry.handshake.assert_called_once()

    @patch("clean_architecture_linter.interface.cli.InitProjectUseCase")
    def test_init_command_with_options(self, mock_use_case_class) -> None:
        """Test that init command passes options to use case."""
        deps = _make_mock_deps()
        mock_use_case_instance = Mock()
        mock_use_case_class.return_value = mock_use_case_instance

        app = create_app(deps)
        runner.invoke(app, ["init", "--template", "fastapi", "--check-layers"])
        mock_use_case_instance.execute.assert_called_once_with(template="fastapi", check_layers=True)

    @patch("clean_architecture_linter.interface.cli.InitProjectUseCase")
    def test_init_command_with_template_only(self, mock_use_case_class) -> None:
        """Test init command with template option only."""
        deps = _make_mock_deps()
        mock_use_case_instance = Mock()
        mock_use_case_class.return_value = mock_use_case_instance

        app = create_app(deps)
        runner.invoke(app, ["init", "--template", "sqlalchemy"])
        mock_use_case_instance.execute.assert_called_once_with(template="sqlalchemy", check_layers=False)

    @patch("clean_architecture_linter.interface.cli.InitProjectUseCase")
    def test_init_command_with_check_layers_only(self, mock_use_case_class) -> None:
        """Test init command with check-layers option only."""
        deps = _make_mock_deps()
        mock_use_case_instance = Mock()
        mock_use_case_class.return_value = mock_use_case_instance

        app = create_app(deps)
        runner.invoke(app, ["init", "--check-layers"])
        mock_use_case_instance.execute.assert_called_once_with(template=None, check_layers=True)


class TestGatedAuditLogic:
    """Test gated sequential audit logic."""

    @patch("clean_architecture_linter.interface.cli.ConfigurationLoader")
    @patch("clean_architecture_linter.interface.cli.CheckAuditUseCase")
    def test_gated_stop_on_ruff_violations(
        self,
        mock_use_case_class,
        mock_config_loader_class,
    ) -> None:
        """Test that audit stops when Ruff finds violations."""
        mock_config_loader = Mock(spec=ConfigurationLoader)
        mock_config_loader.ruff_enabled = True
        mock_config_loader_class.return_value = mock_config_loader

        deps = _make_mock_deps()
        mock_use_case_instance = Mock()
        mock_use_case_instance.execute.return_value = AuditResult(
            ruff_results=[LinterResult("R001", "Ruff violation", ["file.py:1"])],
            mypy_results=[],
            excelsior_results=[],
            ruff_enabled=True,
            blocked_by="ruff",
        )
        mock_use_case_class.return_value = mock_use_case_instance

        app = create_app(deps)
        result = runner.invoke(app, ["check", "src"])
        assert "blocked" in result.stdout.lower() or result.exit_code == 1
        assert result.exit_code == 1


class TestFixManualOnly:
    """Test manual-only fix suggestions."""

    def test_manual_only_all_linters(self) -> None:
        """Test manual-only with all linters."""
        mock_ruff = Mock()
        mock_ruff.gather_results.return_value = [LinterResult("R001", "Ruff issue", ["file.py:1"])]
        mock_ruff.supports_autofix.return_value = True
        mock_ruff.get_fixable_rules.return_value = []
        mock_ruff.get_manual_fix_instructions.return_value = "Fix it"

        deps = _make_mock_deps(
            ruff_adapter=mock_ruff,
            mypy_adapter=Mock(gather_results=Mock(return_value=[])),
            excelsior_adapter=Mock(gather_results=Mock(return_value=[])),
            import_linter_adapter=Mock(gather_results=Mock(return_value=[])),
        )

        app = create_app(deps)
        runner.invoke(app, ["fix", "src", "--manual-only"])
        deps.telemetry.step.assert_any_call(
            "📋 Gathering manual fix suggestions from all linters...")

    def test_manual_only_ruff_only(self) -> None:
        """Test manual-only with ruff linter only."""
        mock_ruff = Mock()
        mock_ruff.gather_results.return_value = []

        deps = _make_mock_deps(ruff_adapter=mock_ruff)
        app = create_app(deps)
        runner.invoke(app, ["fix", "src", "--manual-only", "--linter", "ruff"])

    def test_manual_only_excelsior_suite(self) -> None:
        """Test manual-only with excelsior suite linters."""
        deps = _make_mock_deps(
            mypy_adapter=Mock(gather_results=Mock(return_value=[])),
            excelsior_adapter=Mock(gather_results=Mock(return_value=[])),
            import_linter_adapter=Mock(gather_results=Mock(return_value=[])),
        )

        app = create_app(deps)
        runner.invoke(app, ["fix", "src", "--manual-only", "--linter", "excelsior"])
        deps.telemetry.step.assert_any_call(
            "📋 Gathering manual fix suggestions from Excelsior suite...")


class TestFixRuff:
    """Test Ruff-only fixer."""

    def test_fix_ruff_success(self) -> None:
        """Test successful Ruff fix."""
        mock_ruff = Mock()
        mock_ruff.apply_fixes.return_value = True

        deps = _make_mock_deps(ruff_adapter=mock_ruff)
        app = create_app(deps)
        result = runner.invoke(app, ["fix", "src", "--linter", "ruff"])

        deps.telemetry.step.assert_any_call("🔧 Applying Ruff fixes...")
        mock_ruff.apply_fixes.assert_called_once_with(Path("src"))
        assert result.exit_code == 0

    def test_fix_ruff_failure(self) -> None:
        """Test failed Ruff fix."""
        mock_ruff = Mock()
        mock_ruff.apply_fixes.return_value = False

        deps = _make_mock_deps(ruff_adapter=mock_ruff)
        app = create_app(deps)
        result = runner.invoke(app, ["fix", "src", "--linter", "ruff"])
        assert result.exit_code == 1


class TestFixExcelsior:
    """Test Excelsior multi-pass fixer."""

    @patch("clean_architecture_linter.interface.cli.ApplyFixesUseCase")
    @patch("clean_architecture_linter.domain.rules.type_hints.MissingTypeHintRule")
    @patch("clean_architecture_linter.domain.rules.immutability.DomainImmutabilityRule")
    @patch("clean_architecture_linter.interface.cli.CheckAuditUseCase")
    @patch("clean_architecture_linter.interface.cli.ConfigurationLoader")
    def test_fix_excelsior_executes_multi_pass(
        self,
        mock_config_loader_class,
        mock_check_audit_class,
        mock_immutability_class,
        mock_rule_class,
        mock_use_case_class,
    ) -> None:
        """Test that excelsior fixer executes multi-pass."""
        mock_config_loader = Mock()
        mock_config_loader_class.return_value = mock_config_loader

        mock_check_audit_instance = Mock()
        mock_check_audit_instance.execute.return_value = AuditResult()
        mock_check_audit_class.return_value = mock_check_audit_instance

        deps = _make_mock_deps()
        mock_use_case_instance = Mock()
        mock_use_case_instance.execute_multi_pass.return_value = 5
        mock_use_case_class.return_value = mock_use_case_instance

        app = create_app(deps)
        result = runner.invoke(app, ["fix", "src"])

        mock_use_case_class.assert_called_once()
        mock_use_case_instance.execute_multi_pass.assert_called_once()
        deps.telemetry.step.assert_any_call("✅ Successfully fixed 5 file(s)")
        assert result.exit_code == 0

    @patch("clean_architecture_linter.interface.cli.ApplyFixesUseCase")
    @patch("clean_architecture_linter.domain.rules.type_hints.MissingTypeHintRule")
    @patch("clean_architecture_linter.domain.rules.immutability.DomainImmutabilityRule")
    @patch("clean_architecture_linter.interface.cli.CheckAuditUseCase")
    @patch("clean_architecture_linter.interface.cli.ConfigurationLoader")
    def test_fix_excelsior_with_options(
        self,
        mock_config_loader_class,
        mock_check_audit_class,
        mock_immutability_class,
        mock_rule_class,
        mock_use_case_class,
    ) -> None:
        """Test excelsior fixer with various options."""
        mock_config_loader = Mock()
        mock_config_loader_class.return_value = mock_config_loader

        mock_check_audit_instance = Mock()
        mock_check_audit_instance.execute.return_value = AuditResult()
        mock_check_audit_class.return_value = mock_check_audit_instance

        deps = _make_mock_deps()
        mock_use_case_instance = Mock()
        mock_use_case_instance.execute_multi_pass.return_value = 0
        mock_use_case_class.return_value = mock_use_case_instance

        app = create_app(deps)
        runner.invoke(app, ["fix", "src", "--confirm", "--no-backup", "--skip-tests", "--cleanup-backups"])

        call_kwargs = mock_use_case_class.call_args[1]
        assert call_kwargs["require_confirmation"] is True
        assert call_kwargs["create_backups"] is False
        assert call_kwargs["validate_with_tests"] is False
        assert call_kwargs["cleanup_backups"] is True

        deps.telemetry.step.assert_any_call("ℹ️  No fixes applied")
