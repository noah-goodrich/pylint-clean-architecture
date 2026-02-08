"""Unit tests for SnowflakeStreamlitRenderer adapter."""

import unittest
from unittest.mock import MagicMock, patch

from excelsior_architect.domain.entities import (
    ArchitecturalHealthReport,
    ViolationWithFixInfo,
)
from excelsior_architect.infrastructure.adapters.snowflake_renderer import (
    SnowflakeStreamlitRenderer,
)


class TestSnowflakeStreamlitRenderer(unittest.TestCase):
    """Test SnowflakeStreamlitRenderer render methods."""

    def setUp(self) -> None:
        self.renderer = SnowflakeStreamlitRenderer()
        self.mock_report = MagicMock(spec=ArchitecturalHealthReport)

    def test_render_health_report_raises_runtime_error_when_streamlit_not_installed(
        self,
    ) -> None:
        """render_health_report() raises RuntimeError when streamlit is not installed."""
        with patch("builtins.__import__", side_effect=ImportError("No module named 'streamlit'")):
            with self.assertRaises(RuntimeError) as ctx:
                self.renderer.render_health_report(self.mock_report)
            self.assertIn("Streamlit is required", str(ctx.exception))
            self.assertIn(
                "pip install excelsior[snowflake]", str(ctx.exception))

    def test_render_health_report_raises_not_implemented_when_streamlit_installed(
        self,
    ) -> None:
        """render_health_report() raises NotImplementedError even when streamlit is available."""
        # Mock streamlit as importable
        with patch.dict("sys.modules", {"streamlit": MagicMock()}):
            with self.assertRaises(NotImplementedError) as ctx:
                self.renderer.render_health_report(self.mock_report)
            self.assertIn(
                "SnowflakeStreamlitRenderer.render_health_report is a stub", str(ctx.exception))

    def test_render_health_report_with_format_parameter(self) -> None:
        """render_health_report() accepts format parameter."""
        with patch.dict("sys.modules", {"streamlit": MagicMock()}):
            with self.assertRaises(NotImplementedError):
                self.renderer.render_health_report(
                    self.mock_report, format="json")

    def test_render_health_report_with_mode_parameter(self) -> None:
        """render_health_report() accepts mode parameter."""
        with patch.dict("sys.modules", {"streamlit": MagicMock()}):
            with self.assertRaises(NotImplementedError):
                self.renderer.render_health_report(
                    self.mock_report, mode="detailed")

    def test_render_health_report_with_both_parameters(self) -> None:
        """render_health_report() accepts both format and mode parameters."""
        with patch.dict("sys.modules", {"streamlit": MagicMock()}):
            with self.assertRaises(NotImplementedError):
                self.renderer.render_health_report(
                    self.mock_report, format="json", mode="detailed")

    def test_render_violations_raises_not_implemented(self) -> None:
        """render_violations() raises NotImplementedError."""
        violations = [MagicMock(spec=ViolationWithFixInfo)]
        with self.assertRaises(NotImplementedError) as ctx:
            self.renderer.render_violations(violations)
        self.assertIn(
            "SnowflakeStreamlitRenderer.render_violations is a stub", str(ctx.exception))

    def test_render_status_raises_not_implemented(self) -> None:
        """render_status() raises NotImplementedError."""
        with self.assertRaises(NotImplementedError) as ctx:
            self.renderer.render_status("Test message")
        self.assertIn(
            "SnowflakeStreamlitRenderer.render_status is a stub", str(ctx.exception))

    def test_render_status_with_level_parameter(self) -> None:
        """render_status() accepts level parameter."""
        with self.assertRaises(NotImplementedError):
            self.renderer.render_status("Test message", level="warning")

    def test_render_violations_with_empty_list(self) -> None:
        """render_violations() handles empty violation list."""
        with self.assertRaises(NotImplementedError):
            self.renderer.render_violations([])

    def test_render_health_report_error_includes_cause(self) -> None:
        """render_health_report() error includes original ImportError as cause."""
        with patch("builtins.__import__", side_effect=ImportError("test error")):
            try:
                self.renderer.render_health_report(self.mock_report)
                self.fail("Expected RuntimeError")
            except RuntimeError as e:
                self.assertIsInstance(e.__cause__, ImportError)
                self.assertEqual(str(e.__cause__), "test error")
