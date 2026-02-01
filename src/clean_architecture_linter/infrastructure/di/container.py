from typing import Any, Optional, TypeVar

from clean_architecture_linter.infrastructure.adapters.linter_adapters import (
    ExcelsiorAdapter,
    ImportLinterAdapter,
    MypyAdapter,
)
from clean_architecture_linter.infrastructure.adapters.ruff_adapter import RuffAdapter
from clean_architecture_linter.infrastructure.gateways.astroid_gateway import AstroidGateway
from clean_architecture_linter.infrastructure.gateways.filesystem_gateway import FileSystemGateway
from clean_architecture_linter.infrastructure.gateways.python_gateway import PythonGateway
from clean_architecture_linter.infrastructure.services.audit_trail import AuditTrailService
from clean_architecture_linter.infrastructure.services.rule_analysis import RuleFixabilityService
from clean_architecture_linter.infrastructure.services.scaffolder import Scaffolder
from clean_architecture_linter.interface.reporters import TerminalAuditReporter
from clean_architecture_linter.interface.telemetry import ProjectTelemetry

T = TypeVar("T")


class ExcelsiorContainer:
    """Dependency Injection Container for the Excelsior Linter."""

    _instance: Optional["ExcelsiorContainer"] = None

    def __init__(self) -> None:
        self._singletons: dict[str, Any] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register default implementations for protocols."""
        telemetry = ProjectTelemetry("EXCELSIOR", "red", "Command Cruiser Online")
        self.register_singleton("TelemetryPort", telemetry)
        self.register_singleton("AstroidGateway", AstroidGateway())
        self.register_singleton("PythonGateway", PythonGateway())
        filesystem = FileSystemGateway()
        self.register_singleton("FileSystemGateway", filesystem)
        self.register_singleton("Scaffolder", Scaffolder(telemetry))

        # Linter adapters
        self.register_singleton("MypyAdapter", MypyAdapter())
        self.register_singleton("ExcelsiorAdapter", ExcelsiorAdapter())
        self.register_singleton("ImportLinterAdapter", ImportLinterAdapter())
        self.register_singleton("RuffAdapter", RuffAdapter(telemetry=telemetry))

        # Services
        rule_fixability_service = RuleFixabilityService()
        self.register_singleton("RuleFixabilityService", rule_fixability_service)
        self.register_singleton(
            "AuditTrailService",
            AuditTrailService(telemetry, rule_fixability_service, filesystem)
        )

        # Interface
        self.register_singleton(
            "AuditReporter",
            TerminalAuditReporter(rule_fixability_service)
        )

    # JUSTIFICATION: DI Container must handle any type of service
    def register_singleton(self, key: str, instance: Any) -> None:  # pylint: disable=banned-any-usage
        """Register a singleton instance."""
        self._singletons[key] = instance

    # JUSTIFICATION: DI Container must return any type of service
    def get(self, key: str) -> Any:  # pylint: disable=banned-any-usage
        """Retrieve a dependency by key."""
        if key in self._singletons:
            return self._singletons[key]
        raise ValueError(f"Dependency '{key}' not registered.")

    @classmethod
    def get_instance(cls) -> "ExcelsiorContainer":
        """Get or create global container instance."""
        if cls._instance is None:
            cls._instance = ExcelsiorContainer()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton instance (primarily for testing)."""
        cls._instance = None
