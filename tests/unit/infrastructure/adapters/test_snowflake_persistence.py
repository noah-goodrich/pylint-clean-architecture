"""Unit tests for SnowflakePersistence adapter."""

import unittest
from unittest.mock import MagicMock, patch

from excelsior_architect.domain.entities import ArchitecturalHealthReport
from excelsior_architect.infrastructure.adapters.snowflake_persistence import (
    SnowflakePersistence,
)


class TestSnowflakePersistence(unittest.TestCase):
    """Test SnowflakePersistence save methods."""

    def setUp(self) -> None:
        self.persistence = SnowflakePersistence()
        self.mock_report = MagicMock(spec=ArchitecturalHealthReport)

    def test_save_report_raises_runtime_error_when_snowflake_not_installed(
        self,
    ) -> None:
        """save_report() raises RuntimeError when snowflake-connector-python is not installed."""
        with patch("builtins.__import__", side_effect=ImportError("No module named 'snowflake'")):
            with self.assertRaises(RuntimeError) as ctx:
                self.persistence.save_report(self.mock_report)
            self.assertIn("snowflake-connector-python is required",
                          str(ctx.exception))
            self.assertIn(
                "pip install excelsior[snowflake]", str(ctx.exception))

    def test_save_report_raises_not_implemented_when_snowflake_installed(
        self,
    ) -> None:
        """save_report() raises NotImplementedError even when snowflake is available."""
        # Mock snowflake.connector as importable
        import sys
        mock_snowflake = MagicMock()
        mock_connector = MagicMock()
        mock_snowflake.connector = mock_connector

        with patch.dict(sys.modules, {"snowflake": mock_snowflake, "snowflake.connector": mock_connector}):
            with self.assertRaises(NotImplementedError) as ctx:
                self.persistence.save_report(self.mock_report)
            self.assertIn(
                "SnowflakePersistence.save_report is a stub", str(ctx.exception))

    def test_save_ai_handover_raises_not_implemented(self) -> None:
        """save_ai_handover() raises NotImplementedError."""
        with self.assertRaises(NotImplementedError) as ctx:
            self.persistence.save_ai_handover(self.mock_report)
        self.assertIn(
            "SnowflakePersistence.save_ai_handover is a stub", str(ctx.exception))

    def test_save_report_error_message_includes_cause(self) -> None:
        """save_report() error includes original ImportError as cause."""
        with patch("builtins.__import__", side_effect=ImportError("test error")):
            try:
                self.persistence.save_report(self.mock_report)
                self.fail("Expected RuntimeError")
            except RuntimeError as e:
                self.assertIsInstance(e.__cause__, ImportError)
                self.assertEqual(str(e.__cause__), "test error")

    def test_save_report_with_none_report(self) -> None:
        """save_report() handles None report gracefully."""
        with patch("builtins.__import__", side_effect=ImportError("No module")):
            with self.assertRaises(RuntimeError):
                self.persistence.save_report(None)  # type: ignore[arg-type]

    def test_save_ai_handover_with_none_report(self) -> None:
        """save_ai_handover() handles None report gracefully."""
        with self.assertRaises(NotImplementedError):
            self.persistence.save_ai_handover(None)  # type: ignore[arg-type]
