"""Snowflake/Streamlit renderer for ArchitecturalHealthReport.

Implements AnalysisRendererProtocol for Streamlit. Requires excelsior[snowflake].
This module is a stub; full implementation requires streamlit and snowarch-core.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from excelsior_architect.domain.entities import (
        ArchitecturalHealthReport,
        ViolationWithFixInfo,
    )


class SnowflakeStreamlitRenderer:
    """Renders ArchitecturalHealthReport in a Streamlit app. Stub for excelsior[snowflake]."""

    def render_health_report(
        self,
        report: "ArchitecturalHealthReport",
        format: str = "terminal",
        mode: str = "standard",
    ) -> None:
        """Render full architectural health report in Streamlit."""
        try:
            import streamlit as st  # noqa: F401
        except ImportError as e:
            raise RuntimeError(
                "Streamlit is required for SnowflakeStreamlitRenderer. "
                "Install with: pip install excelsior[snowflake]"
            ) from e
        # Stub: full implementation would use st.metric, st.dataframe, etc.
        raise NotImplementedError(
            "SnowflakeStreamlitRenderer.render_health_report is a stub. "
            "Full implementation in excelsior[snowflake] or snowarch-audit."
        )

    def render_violations(
        self, violations: list["ViolationWithFixInfo"]
    ) -> None:
        """Render violation list in Streamlit."""
        raise NotImplementedError(
            "SnowflakeStreamlitRenderer.render_violations is a stub."
        )

    def render_status(self, message: str, level: str = "info") -> None:
        """Render a status message in Streamlit (e.g. st.info, st.warning)."""
        raise NotImplementedError(
            "SnowflakeStreamlitRenderer.render_status is a stub."
        )
