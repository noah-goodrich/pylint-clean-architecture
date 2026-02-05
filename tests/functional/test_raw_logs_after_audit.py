"""Functional test: raw subprocess logs are generated when linter adapters run."""

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def test_mypy_adapter_reports_error_when_output_unparseable(tmp_path: Path) -> None:
    """When mypy fails with unparseable output (e.g. config error), MypyAdapter returns MYPY_ERROR.

    This prevents silent failures where mypy exits non-zero but the adapter returns
    an empty list because the output doesn't match the expected error line pattern.

    Regression test for: "Source file found twice under different module names" silent failure.
    """
    from clean_architecture_linter.infrastructure.adapters.mypy_adapter import MypyAdapter

    # Mock subprocess.run to return mypy's "found twice" error
    mock_result = MagicMock()
    mock_result.returncode = 2
    mock_result.stdout = (
        "src/stubs/astroid.pyi: error: Source file found twice under different "
        "module names: \"package.stubs.astroid\" and \"astroid\"\n"
        "Found 1 error in 1 file (errors prevented further checking)\n"
    )
    mock_result.stderr = ""

    with patch("subprocess.run", return_value=mock_result):
        adapter = MypyAdapter(raw_log_port=MagicMock(),
                              guidance_service=MagicMock())
        results = adapter.gather_results("src")

    # Must NOT return empty list - this was the silent failure bug
    assert len(
        results) == 1, "Unparseable mypy errors must be reported, not silently ignored"
    assert results[0].code == "MYPY_ERROR"
    assert "Source file found twice" in results[0].message


def test_raw_logs_generated_when_mypy_adapter_runs(tmp_path: Path) -> None:
    """MypyAdapter with raw_log_port writes raw_mypy.log when gather_results runs."""
    (tmp_path / "foo.py").write_text("x: int = 1\n")
    log_dir = str(tmp_path / "logs")
    os.makedirs(log_dir, exist_ok=True)

    from clean_architecture_linter.infrastructure.adapters.mypy_adapter import MypyAdapter
    from clean_architecture_linter.infrastructure.services.subprocess_logging import (
        SubprocessLoggingService,
    )

    svc = SubprocessLoggingService(log_dir=log_dir)
    guidance_service = MagicMock()
    adapter = MypyAdapter(raw_log_port=svc, guidance_service=guidance_service)
    adapter.gather_results(str(tmp_path))

    raw_mypy = Path(log_dir) / "raw_mypy.log"
    assert raw_mypy.exists(), "raw_mypy.log should exist after MypyAdapter.gather_results"
    assert raw_mypy.stat().st_size > 0
    content = raw_mypy.read_text()
    assert "stdout" in content or "stderr" in content or "mypy" in content.lower()


@pytest.mark.slow
def test_raw_logs_generated_after_full_audit() -> None:
    """Running 'excelsior check' writes raw tool output to .excelsior/logs/ when tools run."""
    root = Path(__file__).resolve().parent.parent.parent
    src = root / "src"
    log_dir = root / ".excelsior" / "logs"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(src)

    subprocess.run(
        [sys.executable, "-m", "clean_architecture_linter", "check", str(src)],
        cwd=str(root),
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )

    if log_dir.is_dir():
        raw_logs = list(log_dir.glob("raw_*.log"))
        with_content = [p for p in raw_logs if p.stat().st_size > 0]
        assert len(with_content) >= 1, (
            f"After full audit, expected at least one non-empty raw_*.log in {log_dir}"
        )
