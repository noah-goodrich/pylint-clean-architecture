"""Use Case: Initialize project scaffolding."""

from typing import Optional

from clean_architecture_linter.domain.protocols import TelemetryPort
from clean_architecture_linter.infrastructure.services.scaffolder import Scaffolder


class InitProjectUseCase:
    """Orchestrate project initialization and configuration."""

    def __init__(self, scaffolder: Scaffolder, telemetry: TelemetryPort) -> None:
        self.scaffolder = scaffolder
        self.telemetry = telemetry

    def execute(self, template: Optional[str] = None, check_layers: bool = False) -> None:
        """Initialize project configuration and artifacts."""
        self.scaffolder.init_project(template=template, check_layers=check_layers)
