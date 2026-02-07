"""Unit tests for SubprocessLoggingService."""

import os
from pathlib import Path

import pytest

from excelsior_architect.infrastructure.services.subprocess_logging import (
    SubprocessLoggingService,
)


class TestSubprocessLoggingService:
    """Test raw subprocess log capture."""

    def test_log_raw_creates_log_dir(self, tmp_path: Path) -> None:
        """log_raw creates .excelsior/logs if missing."""
        log_dir = str(tmp_path / "logs")
        svc = SubprocessLoggingService(log_dir=log_dir)
        svc.log_raw("ruff", "stdout line", "stderr line")
        assert os.path.isdir(log_dir)

    def test_log_raw_writes_raw_tool_log(self, tmp_path: Path) -> None:
        """log_raw appends to raw_{tool}.log with stdout/stderr."""
        log_dir = str(tmp_path / "logs")
        svc = SubprocessLoggingService(log_dir=log_dir)
        svc.log_raw("mypy", "file:1: error: message", "warning: something")
        log_file = os.path.join(log_dir, "raw_mypy.log")
        assert os.path.isfile(log_file)
        content = open(log_file, encoding="utf-8").read()
        assert "stdout" in content
        assert "stderr" in content
        assert "file:1: error: message" in content
        assert "warning: something" in content

    def test_log_raw_appends_multiple_runs(self, tmp_path: Path) -> None:
        """log_raw appends each run with separator."""
        log_dir = str(tmp_path / "logs")
        svc = SubprocessLoggingService(log_dir=log_dir)
        svc.log_raw("pylint", "first run", "")
        svc.log_raw("pylint", "second run", "")
        content = open(os.path.join(log_dir, "raw_pylint.log"),
                       encoding="utf-8").read()
        assert "first run" in content
        assert "second run" in content
        assert content.count("====") >= 2
