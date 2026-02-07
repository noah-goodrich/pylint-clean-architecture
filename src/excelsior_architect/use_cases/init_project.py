"""Use Case: Initialize project scaffolding."""


from excelsior_architect.domain.protocols import ScaffolderProtocol, TelemetryPort


class InitProjectUseCase:
    """Orchestrate project initialization and configuration."""

    def __init__(self, scaffolder: ScaffolderProtocol, telemetry: TelemetryPort) -> None:
        self.scaffolder = scaffolder
        self.telemetry = telemetry

    def execute(self, template: str | None = None, check_layers: bool = False) -> None:
        """Initialize project configuration and artifacts."""
        self.scaffolder.init_project(
            template=template, check_layers=check_layers)
