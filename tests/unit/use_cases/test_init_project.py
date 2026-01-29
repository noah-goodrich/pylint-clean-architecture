"""Unit tests for InitProjectUseCase."""
from unittest.mock import MagicMock

from clean_architecture_linter.use_cases.init_project import InitProjectUseCase


def test_execute_calls_scaffolder_init_project():
    """execute() delegates to scaffolder.init_project with template and check_layers."""
    scaffolder = MagicMock()
    telemetry = MagicMock()
    use_case = InitProjectUseCase(scaffolder, telemetry)

    use_case.execute(template="snowflake", check_layers=True)

    scaffolder.init_project.assert_called_once_with(
        template="snowflake",
        check_layers=True,
    )
