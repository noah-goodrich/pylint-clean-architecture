"""Functional test: raw subprocess logs are generated when linter adapters run."""

import os
import subprocess
import sys
from pathlib import Path

import pytest


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
    adapter = MypyAdapter(raw_log_port=svc)
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
