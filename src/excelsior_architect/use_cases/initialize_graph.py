"""
Hydrates the Knowledge Graph with static knowledge (Violations and Patterns).

Uses GraphGatewayProtocol and FileSystemProtocol so it can run with any
supported adapter (local filesystem, Snowflake stages, S3, etc.).
"""
import csv
import io
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from excelsior_architect.domain.protocols import FileSystemProtocol, GraphGatewayProtocol


class InitializeGraphUseCase:
    """Loads violation/pattern registries from a storage abstraction and hydrates the graph."""

    def __init__(
        self,
        gateway: "GraphGatewayProtocol",
        filesystem: "FileSystemProtocol",
    ) -> None:
        self.gateway = gateway
        self.filesystem = filesystem

    def execute(
        self,
        patterns_csv: str,
        violations_csv_paths: list[str],
    ) -> None:
        """
        Load patterns and violations from the given paths (or identifiers).
        Paths are resolved by the filesystem implementation (local path, stage, S3, etc.).
        """
        # 1. Ensure every violation code from each registry exists first (violations before patterns)
        # Use Description (canonical summary) for graph; Name is short identifier.
        for violations_csv in violations_csv_paths:
            violations_content = self.filesystem.read_text(violations_csv)
            for row in csv.DictReader(io.StringIO(violations_content)):
                canonical = row.get("Description", "").strip() or row.get("Name", "").strip()
                self.gateway.ensure_violation(
                    code=row["Code"],
                    message=canonical,
                )

        # 2. Load patterns and link to violations (add_strategy matches existing Violations by code)
        patterns_content = self.filesystem.read_text(patterns_csv)
        for row in csv.DictReader(io.StringIO(patterns_content)):
            codes = [c.strip() for c in row["Violations"].split(",")]
            steps = [s.strip() for s in row["Implementation"].split(",")]
            self.gateway.add_strategy(
                strat_id=row["ID"],
                pattern=row["Pattern"],
                rationale=row["Rationale"],
                steps=steps,
                codes=codes,
            )
