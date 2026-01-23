from typing import Dict, Any, TypeVar, Optional
from clean_architecture_linter.interface.telemetry import ProjectTelemetry
from clean_architecture_linter.infrastructure.gateways.astroid_gateway import AstroidGateway
from clean_architecture_linter.infrastructure.gateways.python_gateway import PythonGateway

T = TypeVar("T")


class ExcelsiorContainer:
    """Dependency Injection Container for the Excelsior Linter."""

    _instance: Optional["ExcelsiorContainer"] = None

    def __init__(self) -> None:
        self._singletons: Dict[str, Any] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register default implementations for protocols."""
        self.register_singleton("TelemetryPort", ProjectTelemetry("EXCELSIOR", "red", "Command Cruiser Online"))
        self.register_singleton("AstroidGateway", AstroidGateway())
        self.register_singleton("PythonGateway", PythonGateway())

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
