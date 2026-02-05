"""Package entry point - composition root. Wire dependencies and run the CLI app."""

from clean_architecture_linter.infrastructure.di.container import ExcelsiorContainer
from clean_architecture_linter.infrastructure.gateways.libcst_fixer_gateway import (
    LibCSTFixerGateway,
)
from clean_architecture_linter.interface.cli import CLIAppFactory, CLIDependencies


def main() -> None:
    """Entry point: wire dependencies at composition root, create app, run."""
    container = ExcelsiorContainer()
    container.register_singleton("LibCSTFixerGateway", LibCSTFixerGateway())

    deps = CLIDependencies(
        config_loader=container.get_config_loader(),
        telemetry=container.get_telemetry_port(),
        mypy_adapter=container.get_mypy_adapter(),
        excelsior_adapter=container.get_excelsior_adapter(),
        import_linter_adapter=container.get_import_linter_adapter(),
        ruff_adapter=container.get_ruff_adapter(),
        reporter=container.get_reporter(),
        audit_trail_service=container.get_audit_trail_service(),
        scaffolder=container.get_scaffolder(),
        astroid_gateway=container.get_astroid_gateway(),
        filesystem=container.get_filesystem_gateway(),
        artifact_storage=container.get_artifact_storage(),
        fixer_gateway=container.get_fixer_gateway(),
        guidance_service=container.get_guidance_service(),
        stub_creator=container.get_stub_creator(),
        violation_bridge=container.get_violation_bridge(),
    )

    app = CLIAppFactory.create_app(deps)
    app()
