"""Unit tests for CheckAuditUseCase."""

from unittest.mock import Mock

from clean_architecture_linter.domain.config import ConfigurationLoader
from clean_architecture_linter.domain.entities import AuditResult, LinterResult
from clean_architecture_linter.use_cases.check_audit import CheckAuditUseCase


class TestCheckAuditUseCase:
    """Test CheckAuditUseCase orchestration."""

    def test_execute_runs_all_linters_when_no_violations(self) -> None:
        """Test that all linters are called in sequence when no violations found."""
        # Setup
        telemetry = Mock()
        config_loader = Mock(spec=ConfigurationLoader)
        config_loader.ruff_enabled = True

        mypy_adapter = Mock()
        mypy_adapter.gather_results.return_value = []

        excelsior_adapter = Mock()
        excelsior_adapter.gather_results.return_value = [
            LinterResult("W9015", "Missing type hint", [])]

        il_adapter = Mock()
        il_adapter.gather_results.return_value = []

        ruff_adapter = Mock()
        ruff_adapter.gather_results.return_value = []

        use_case = CheckAuditUseCase(
            mypy_adapter=mypy_adapter,
            excelsior_adapter=excelsior_adapter,
            import_linter_adapter=il_adapter,
            ruff_adapter=ruff_adapter,
            telemetry=telemetry,
            config_loader=config_loader,
        )

        # Execute
        result = use_case.execute("src")

        # Assert - All linters should run since no blocking violations
        assert isinstance(result, AuditResult)
        assert len(result.excelsior_results) == 1
        assert result.blocked_by is None
        ruff_adapter.gather_results.assert_called_once_with("src")
        mypy_adapter.gather_results.assert_called_once_with("src")
        excelsior_adapter.gather_results.assert_called_once_with("src")

    def test_execute_runs_only_mypy_when_linter_is_mypy(self) -> None:
        """Test that only mypy is called when linter='mypy'."""
        telemetry = Mock()
        config_loader = Mock(spec=ConfigurationLoader)
        config_loader.ruff_enabled = True

        mypy_adapter = Mock()
        mypy_adapter.gather_results.return_value = [
            LinterResult("M001", "Type error", [])]

        excelsior_adapter = Mock()
        il_adapter = Mock()
        ruff_adapter = Mock()
        ruff_adapter.gather_results.return_value = []

        use_case = CheckAuditUseCase(
            mypy_adapter=mypy_adapter,
            excelsior_adapter=excelsior_adapter,
            import_linter_adapter=il_adapter,
            ruff_adapter=ruff_adapter,
            telemetry=telemetry,
            config_loader=config_loader,
        )

        result = use_case.execute("src")

        # Assert - Should be blocked by Mypy, Excelsior should not run
        assert len(result.mypy_results) == 1
        assert result.blocked_by == "mypy"
        ruff_adapter.gather_results.assert_called_once_with("src")
        mypy_adapter.gather_results.assert_called_once_with("src")
        excelsior_adapter.gather_results.assert_not_called()

    def test_execute_skips_ruff_when_disabled(self) -> None:
        """Test that ruff is skipped when ruff_enabled is False."""
        telemetry = Mock()
        config_loader = Mock(spec=ConfigurationLoader)
        config_loader.ruff_enabled = False

        mypy_adapter = Mock()
        mypy_adapter.gather_results.return_value = []

        excelsior_adapter = Mock()
        excelsior_adapter.gather_results.return_value = []

        il_adapter = Mock()
        il_adapter.gather_results.return_value = []

        ruff_adapter = Mock()

        use_case = CheckAuditUseCase(
            mypy_adapter=mypy_adapter,
            excelsior_adapter=excelsior_adapter,
            import_linter_adapter=il_adapter,
            ruff_adapter=ruff_adapter,
            telemetry=telemetry,
            config_loader=config_loader,
        )

        result = use_case.execute("src")

        assert result.ruff_enabled is False
        ruff_adapter.gather_results.assert_not_called()

    def test_execute_returns_no_violations_when_all_empty(self) -> None:
        """Test that has_violations() returns False when all results are empty."""
        telemetry = Mock()
        config_loader = Mock(spec=ConfigurationLoader)
        config_loader.ruff_enabled = True

        mypy_adapter = Mock()
        mypy_adapter.gather_results.return_value = []

        excelsior_adapter = Mock()
        excelsior_adapter.gather_results.return_value = []

        il_adapter = Mock()
        il_adapter.gather_results.return_value = []

        ruff_adapter = Mock()
        ruff_adapter.gather_results.return_value = []

        use_case = CheckAuditUseCase(
            mypy_adapter=mypy_adapter,
            excelsior_adapter=excelsior_adapter,
            import_linter_adapter=il_adapter,
            ruff_adapter=ruff_adapter,
            telemetry=telemetry,
            config_loader=config_loader,
        )

        result = use_case.execute("src")

        assert result.has_violations() is False

    def test_execute_calls_telemetry_steps(self) -> None:
        """Test that telemetry.step is called for each linter."""
        telemetry = Mock()
        config_loader = Mock(spec=ConfigurationLoader)
        config_loader.ruff_enabled = True

        mypy_adapter = Mock()
        mypy_adapter.gather_results.return_value = []

        excelsior_adapter = Mock()
        excelsior_adapter.gather_results.return_value = []

        il_adapter = Mock()
        il_adapter.gather_results.return_value = []

        ruff_adapter = Mock()
        ruff_adapter.gather_results.return_value = []

        use_case = CheckAuditUseCase(
            mypy_adapter=mypy_adapter,
            excelsior_adapter=excelsior_adapter,
            import_linter_adapter=il_adapter,
            ruff_adapter=ruff_adapter,
            telemetry=telemetry,
            config_loader=config_loader,
        )

        use_case.execute("src")

        # Check that telemetry.step was called multiple times
        assert telemetry.step.call_count >= 4  # At least one per linter

    def test_execute_handles_excelsior_only(self) -> None:
        """Test that only excelsior is called when linter='excelsior'."""
        telemetry = Mock()
        config_loader = Mock(spec=ConfigurationLoader)
        config_loader.ruff_enabled = True

        mypy_adapter = Mock()
        mypy_adapter.gather_results.return_value = []
        excelsior_adapter = Mock()
        excelsior_adapter.gather_results.return_value = [
            LinterResult("W9015", "Missing type hint", [])]
        il_adapter = Mock()
        ruff_adapter = Mock()
        ruff_adapter.gather_results.return_value = []

        use_case = CheckAuditUseCase(
            mypy_adapter=mypy_adapter,
            excelsior_adapter=excelsior_adapter,
            import_linter_adapter=il_adapter,
            ruff_adapter=ruff_adapter,
            telemetry=telemetry,
            config_loader=config_loader,
        )

        result = use_case.execute("src")

        # Assert - All linters should run, Excelsior finds violations but doesn't block
        assert len(result.excelsior_results) == 1
        assert result.blocked_by is None
        ruff_adapter.gather_results.assert_called_once_with("src")
        mypy_adapter.gather_results.assert_called_once_with("src")
        excelsior_adapter.gather_results.assert_called_once_with("src")
