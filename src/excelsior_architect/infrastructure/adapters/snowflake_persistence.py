"""Snowflake persistence for ArchitecturalHealthReport.

Implements AnalysisPersistenceProtocol for writing to Snowflake tables. Requires excelsior[snowflake].
This module is a stub; full implementation requires snowflake-connector-python and snowarch-core.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from excelsior_architect.domain.entities import ArchitecturalHealthReport


class SnowflakePersistence:
    """Persists ArchitecturalHealthReport to Snowflake tables. Stub for excelsior[snowflake]."""

    def save_report(self, report: "ArchitecturalHealthReport") -> None:
        """Save full health report to Snowflake (e.g. table or stage)."""
        try:
            import snowflake.connector  # noqa: F401
        except ImportError as e:
            raise RuntimeError(
                "snowflake-connector-python is required for SnowflakePersistence. "
                "Install with: pip install excelsior[snowflake]"
            ) from e
        raise NotImplementedError(
            "SnowflakePersistence.save_report is a stub. "
            "Full implementation in excelsior[snowflake] or snowarch-audit."
        )

    def save_ai_handover(self, report: "ArchitecturalHealthReport") -> str:
        """Generate and save AI handover to Snowflake. Returns table/stage path."""
        raise NotImplementedError(
            "SnowflakePersistence.save_ai_handover is a stub."
        )
