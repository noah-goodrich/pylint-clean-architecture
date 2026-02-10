"""Package entry point - composition root. Wire dependencies and run the CLI app."""

import os

from excelsior_architect.infrastructure.di.container import ExcelsiorContainer
from excelsior_architect.infrastructure.gateways.libcst_fixer_gateway import (
    LibCSTFixerGateway,
)
from excelsior_architect.interface.cli import CLIAppFactory, CLIDependencies


def main() -> None:
    """Entry point: wire dependencies at composition root, create app, run."""
    import sys
    # Debug: confirm subprocess runs this module (for functional test diagnostics)
    if os.environ.get("EXCELSIOR_DEBUG_LOG"):
        print("[excelsior] main() entered, cwd=%s" % os.getcwd(), file=sys.stderr)
    _log_path = os.environ.get("EXCELSIOR_DEBUG_LOG")
    if _log_path:
        try:
            with open(_log_path, "a") as _f:
                _f.write(f"__main__.py:main() started cwd={os.getcwd()!r}\n")
                _f.flush()
        except Exception as _e:
            import sys
            print(f"[excelsior debug] EXCELSIOR_DEBUG_LOG write failed: {_e}", file=sys.stderr)

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
        sae_bootstrapper=container.get_sae_bootstrapper(),
        graph_gateway=container.get_graph_gateway(),
        graph_ingestor=container.get_graph_ingestor(),
    )

    app = CLIAppFactory.create_app(deps)
    app()
