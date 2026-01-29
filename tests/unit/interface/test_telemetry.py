"""Unit tests for ProjectTelemetry."""
from unittest.mock import MagicMock
from clean_architecture_linter.interface.telemetry import ProjectTelemetry


def test_handshake_prints_banner():
    tel = ProjectTelemetry("Test", "blue", "Hello")
    tel.console = MagicMock()
    tel.logger = MagicMock()
    tel.handshake()
    tel.console.print.assert_called()
    tel.logger.info.assert_called()


def test_step_prints_and_logs():
    tel = ProjectTelemetry("Test", "blue", "Hello")
    tel.console = MagicMock()
    tel.logger = MagicMock()
    tel.step("Done")
    tel.console.print.assert_called_once()
    tel.logger.info.assert_called_once_with("Done")


def test_error_prints_and_logs():
    tel = ProjectTelemetry("Test", "blue", "Hello")
    tel.console = MagicMock()
    tel.logger = MagicMock()
    tel.error("Failed")
    tel.logger.error.assert_called_once_with("Failed")


def test_warning_prints_and_logs():
    tel = ProjectTelemetry("Test", "blue", "Hello")
    tel.console = MagicMock()
    tel.logger = MagicMock()
    tel.warning("Careful")
    tel.logger.warning.assert_called_once_with("Careful")


def test_debug_logs():
    tel = ProjectTelemetry("Test", "blue", "Hello")
    tel.logger = MagicMock()
    tel.debug("Detail")
    tel.logger.debug.assert_called_once_with("Detail")
