from typing import TYPE_CHECKING, Any, Optional, TypeVar

from clean_architecture_linter.infrastructure.adapters.linter_adapters import (
    ExcelsiorAdapter,
    ImportLinterAdapter,
    MypyAdapter,
)
from clean_architecture_linter.infrastructure.adapters.ruff_adapter import RuffAdapter
from clean_architecture_linter.infrastructure.gateways.astroid_gateway import AstroidGateway
from clean_architecture_linter.infrastructure.gateways.filesystem_gateway import FileSystemGateway
from clean_architecture_linter.infrastructure.gateways.python_gateway import PythonGateway
from clean_architecture_linter.infrastructure.reporters import TerminalAuditReporter
from clean_architecture_linter.infrastructure.services.audit_trail import AuditTrailService
from clean_architecture_linter.infrastructure.services.rule_analysis import RuleFixabilityService
from clean_architecture_linter.infrastructure.services.scaffolder import Scaffolder
from clean_architecture_linter.infrastructure.services.subprocess_logging import (
    SubprocessLoggingService,
)
from clean_architecture_linter.interface.telemetry import ProjectTelemetry

if TYPE_CHECKING:
    from clean_architecture_linter.domain.protocols import (
        AstroidProtocol,
        AuditTrailServiceProtocol,
        FileSystemProtocol,
        FixerGatewayProtocol,
        LinterAdapterProtocol,
        PythonProtocol,
        ScaffolderProtocol,
        TelemetryPort,
    )
    from clean_architecture_linter.interface.reporters import AuditReporter

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

        # Raw subprocess logging (Ruff, Mypy, Pylint stdout/stderr -> .excelsior/logs/)
        raw_log_service = SubprocessLoggingService()
        self.register_singleton("SubprocessLoggingService", raw_log_service)

        # Linter adapters
        self.register_singleton("MypyAdapter", MypyAdapter(raw_log_port=raw_log_service))
        self.register_singleton(
            "ExcelsiorAdapter", ExcelsiorAdapter(raw_log_port=raw_log_service)
        )
        self.register_singleton("ImportLinterAdapter", ImportLinterAdapter())
        self.register_singleton(
            "RuffAdapter",
            RuffAdapter(telemetry=telemetry, raw_log_port=raw_log_service),
        )

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
        """Retrieve a dependency by key. Prefer explicit get_* methods for type safety."""
        if key in self._singletons:
            return self._singletons[key]
        raise ValueError(f"Dependency '{key}' not registered.")

    def get_telemetry_port(self) -> "TelemetryPort":
        """Return the telemetry/UI port."""
        return self.get("TelemetryPort")

    def get_astroid_gateway(self) -> "AstroidProtocol":
        """Return the Astroid gateway."""
        return self.get("AstroidGateway")

    def get_python_gateway(self) -> "PythonProtocol":
        """Return the Python gateway."""
        return self.get("PythonGateway")

    def get_filesystem_gateway(self) -> "FileSystemProtocol":
        """Return the filesystem gateway."""
        return self.get("FileSystemGateway")

    def get_scaffolder(self) -> "ScaffolderProtocol":
        """Return the project scaffolder."""
        return self.get("Scaffolder")

    def get_mypy_adapter(self) -> "LinterAdapterProtocol":
        """Return the Mypy linter adapter."""
        return self.get("MypyAdapter")

    def get_excelsior_adapter(self) -> "LinterAdapterProtocol":
        """Return the Excelsior (Pylint) linter adapter."""
        return self.get("ExcelsiorAdapter")

    def get_import_linter_adapter(self) -> "LinterAdapterProtocol":
        """Return the Import-Linter adapter."""
        return self.get("ImportLinterAdapter")

    def get_ruff_adapter(self) -> "LinterAdapterProtocol":
        """Return the Ruff linter adapter."""
        return self.get("RuffAdapter")

    def get_audit_trail_service(self) -> "AuditTrailServiceProtocol":
        """Return the audit trail service."""
        return self.get("AuditTrailService")

    def get_reporter(self) -> "AuditReporter":
        """Return the audit reporter."""
        return self.get("AuditReporter")

    def get_fixer_gateway(self) -> "FixerGatewayProtocol":
        """Return the LibCST fixer gateway."""
        return self.get("LibCSTFixerGateway")

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
