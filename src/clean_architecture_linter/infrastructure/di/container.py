from typing import TYPE_CHECKING, Any, Optional, TypeVar, cast

from clean_architecture_linter.domain.config import ConfigurationLoader
from clean_architecture_linter.infrastructure.adapters.linter_adapters import (
    ExcelsiorAdapter,
    ImportLinterAdapter,
    MypyAdapter,
)
from clean_architecture_linter.infrastructure.adapters.ruff_adapter import RuffAdapter
from clean_architecture_linter.infrastructure.config_file_loader import ConfigFileLoader
from clean_architecture_linter.infrastructure.gateways.artifact_storage_gateway import (
    LocalArtifactStorage,
)
from clean_architecture_linter.infrastructure.gateways.astroid_gateway import AstroidGateway
from clean_architecture_linter.infrastructure.gateways.filesystem_gateway import FileSystemGateway
from clean_architecture_linter.infrastructure.gateways.python_gateway import PythonGateway
from clean_architecture_linter.infrastructure.reporters import TerminalAuditReporter
from clean_architecture_linter.infrastructure.services.audit_trail import AuditTrailService
from clean_architecture_linter.infrastructure.services.guidance_service import GuidanceService
from clean_architecture_linter.infrastructure.services.rule_analysis import RuleFixabilityService
from clean_architecture_linter.infrastructure.services.scaffolder import Scaffolder
from clean_architecture_linter.infrastructure.services.stub_authority import StubAuthority
from clean_architecture_linter.infrastructure.services.stub_creator import StubCreatorService
from clean_architecture_linter.infrastructure.services.subprocess_logging import (
    SubprocessLoggingService,
)
from clean_architecture_linter.infrastructure.services.violation_bridge import (
    ViolationBridgeService,
)
from clean_architecture_linter.interface.telemetry import ProjectTelemetry

if TYPE_CHECKING:
    from clean_architecture_linter.domain.protocols import (
        ArtifactStorageProtocol,
        AstroidProtocol,
        AuditTrailServiceProtocol,
        FileSystemProtocol,
        FixerGatewayProtocol,
        LinterAdapterProtocol,
        PythonProtocol,
        ScaffolderProtocol,
        StubAuthorityProtocol,
        StubCreatorProtocol,
        TelemetryPort,
        ViolationBridgeProtocol,
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
        config_dict, tool_section = ConfigFileLoader.load_config_from_fs()
        config_loader = ConfigurationLoader(config_dict, tool_section)
        self.register_singleton("ConfigurationLoader", config_loader)

        telemetry = ProjectTelemetry(
            "EXCELSIOR", "red", "Command Cruiser Online")
        self.register_singleton("TelemetryPort", telemetry)
        self.register_singleton("AstroidGateway", AstroidGateway())
        self.register_singleton("PythonGateway", PythonGateway())
        self.register_singleton("StubAuthority", StubAuthority())
        # Command Manual: rule registry and guidance service (created before ViolationBridgeService)
        guidance_service = GuidanceService()
        self.register_singleton("GuidanceService", guidance_service)
        astroid_gateway = self.get("AstroidGateway")
        self.register_singleton(
            "ViolationBridgeService",
            ViolationBridgeService(
                astroid_gateway=astroid_gateway,
                guidance_service=guidance_service,
            ),
        )
        self.register_singleton("StubCreatorService", StubCreatorService())
        filesystem = FileSystemGateway()
        self.register_singleton("FileSystemGateway", filesystem)
        artifact_storage = LocalArtifactStorage(
            base_path=".excelsior", filesystem=filesystem)
        self.register_singleton("ArtifactStorage", artifact_storage)
        self.register_singleton(
            "Scaffolder", Scaffolder(telemetry, config_loader))

        # Raw subprocess logging (Ruff, Mypy, Pylint stdout/stderr -> .excelsior/logs/)
        raw_log_service = SubprocessLoggingService()
        self.register_singleton("SubprocessLoggingService", raw_log_service)

        # Linter adapters (use GuidanceService for get_manual_fix_instructions)
        self.register_singleton(
            "MypyAdapter",
            MypyAdapter(raw_log_port=raw_log_service,
                        guidance_service=guidance_service),
        )
        self.register_singleton(
            "ExcelsiorAdapter",
            ExcelsiorAdapter(
                config_loader=config_loader,
                raw_log_port=raw_log_service,
                guidance_service=guidance_service,
            ),
        )
        self.register_singleton(
            "ImportLinterAdapter",
            ImportLinterAdapter(guidance_service=guidance_service),
        )
        self.register_singleton(
            "RuffAdapter",
            RuffAdapter(
                config_loader=config_loader,
                telemetry=telemetry,
                raw_log_port=raw_log_service,
                guidance_service=guidance_service,
            ),
        )

        # Services
        rule_fixability_service = RuleFixabilityService()
        self.register_singleton("RuleFixabilityService",
                                rule_fixability_service)
        self.register_singleton(
            "AuditTrailService",
            AuditTrailService(
                telemetry,
                rule_fixability_service,
                artifact_storage,
                config_loader=config_loader,
                guidance_service=guidance_service,
                raw_log_port=raw_log_service,
            ),
        )

        # Interface
        self.register_singleton(
            "AuditReporter",
            TerminalAuditReporter(
                rule_fixability_service,
                config_loader=config_loader,
                guidance_service=guidance_service,
                raw_log_port=raw_log_service,
                telemetry=telemetry,
            ),
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
        return cast("TelemetryPort", self.get("TelemetryPort"))

    def get_astroid_gateway(self) -> "AstroidProtocol":
        """Return the Astroid gateway."""
        return cast("AstroidProtocol", self.get("AstroidGateway"))

    def get_python_gateway(self) -> "PythonProtocol":
        """Return the Python gateway."""
        return cast("PythonProtocol", self.get("PythonGateway"))

    def get_stub_authority(self) -> "StubAuthorityProtocol":
        """Return the stub resolver (protocol)."""
        return cast("StubAuthorityProtocol", self.get("StubAuthority"))

    def get_violation_bridge(self) -> "ViolationBridgeProtocol":
        """Return the violation bridge (protocol)."""
        return cast("ViolationBridgeProtocol", self.get("ViolationBridgeService"))

    def get_stub_creator(self) -> "StubCreatorProtocol":
        """Return the stub creator (protocol)."""
        return cast("StubCreatorProtocol", self.get("StubCreatorService"))

    def get_filesystem_gateway(self) -> "FileSystemProtocol":
        """Return the filesystem gateway."""
        return cast("FileSystemProtocol", self.get("FileSystemGateway"))

    def get_artifact_storage(self) -> "ArtifactStorageProtocol":
        """Return the artifact storage (handover, fix plans, history)."""
        return cast("ArtifactStorageProtocol", self.get("ArtifactStorage"))

    def get_scaffolder(self) -> "ScaffolderProtocol":
        """Return the project scaffolder."""
        return cast("ScaffolderProtocol", self.get("Scaffolder"))

    def get_mypy_adapter(self) -> "LinterAdapterProtocol":
        """Return the Mypy linter adapter."""
        return cast("LinterAdapterProtocol", self.get("MypyAdapter"))

    def get_excelsior_adapter(self) -> "LinterAdapterProtocol":
        """Return the Excelsior (Pylint) linter adapter."""
        return cast("LinterAdapterProtocol", self.get("ExcelsiorAdapter"))

    def get_import_linter_adapter(self) -> "LinterAdapterProtocol":
        """Return the Import-Linter adapter."""
        return cast("LinterAdapterProtocol", self.get("ImportLinterAdapter"))

    def get_ruff_adapter(self) -> "LinterAdapterProtocol":
        """Return the Ruff linter adapter."""
        return cast("LinterAdapterProtocol", self.get("RuffAdapter"))

    def get_audit_trail_service(self) -> "AuditTrailServiceProtocol":
        """Return the audit trail service."""
        return cast("AuditTrailServiceProtocol", self.get("AuditTrailService"))

    def get_reporter(self) -> "AuditReporter":
        """Return the audit reporter."""
        return cast("AuditReporter", self.get("AuditReporter"))

    def get_guidance_service(self) -> "GuidanceService":
        """Return the guidance service (rule registry)."""
        return cast(GuidanceService, self.get("GuidanceService"))

    def get_config_loader(self) -> ConfigurationLoader:
        """Return the configuration loader (created at composition root)."""
        return cast(ConfigurationLoader, self.get("ConfigurationLoader"))

    def get_fixer_gateway(self) -> "FixerGatewayProtocol":
        """Return the LibCST fixer gateway."""
        return cast("FixerGatewayProtocol", self.get("LibCSTFixerGateway"))

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
