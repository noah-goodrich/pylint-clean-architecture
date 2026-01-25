import pytest

from clean_architecture_linter.di.container import ExcelsiorContainer


class TestExcelsiorContainer:
    def test_initialization_registers_telemetry(self) -> None:
        container = ExcelsiorContainer()
        telemetry = container.get("TelemetryPort")
        assert telemetry is not None
        assert telemetry.project_name == "EXCELSIOR"

    def test_register_and_get_singleton(self) -> None:
        container = ExcelsiorContainer()
        mock_dep = {"foo": "bar"}
        container.register_singleton("MockDep", mock_dep)

        retrieved = container.get("MockDep")
        assert retrieved == mock_dep
        assert retrieved is mock_dep  # Same instance

    def test_get_missing_dependency_raises_error(self) -> None:
        container = ExcelsiorContainer()
        with pytest.raises(ValueError, match=r"Dependency 'Missing' not registered\."):
            container.get("Missing")
