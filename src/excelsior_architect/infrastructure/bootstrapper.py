"""
SAE bootstrap: hydrates the Knowledge Graph with violation/pattern registries.

Use SAEBootstrapper with injected GraphGatewayProtocol and FileSystemProtocol
so the same flow can run against local FS, Snowflake stages, S3, etc.
"""
from typing import TYPE_CHECKING

from excelsior_architect.use_cases.initialize_graph import InitializeGraphUseCase

if TYPE_CHECKING:
    from excelsior_architect.domain.protocols import FileSystemProtocol, GraphGatewayProtocol


# Paths relative to excelsior_architect package (loaded via importlib.resources)
_SAE_DATA_DIR = "resources/data"


class SAEBootstrapper:
    """Implements SAEBootstrapperProtocol: hydrates the graph via InitializeGraphUseCase."""

    def __init__(
        self,
        gateway: "GraphGatewayProtocol",
        filesystem: "FileSystemProtocol",
        data_dir: str | None = None,
    ) -> None:
        self.gateway = gateway
        self.filesystem = filesystem
        self.data_dir = data_dir or _SAE_DATA_DIR

    def bootstrap(self) -> None:
        """Load patterns and all violation registries into the graph."""
        patterns_csv = f"{self.data_dir}/design_patterns_tree.csv"
        violation_registries = [
            f"{self.data_dir}/excelsior_violations.csv",
            f"{self.data_dir}/mypy_violations.csv",
            f"{self.data_dir}/ruff_violations.csv",
        ]
        use_case = InitializeGraphUseCase(self.gateway, self.filesystem)
        use_case.execute(patterns_csv=patterns_csv, violations_csv_paths=violation_registries)
