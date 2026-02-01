"""Subprocess raw output logging - capture Ruff, Mypy, Pylint stdout/stderr to .excelsior/logs."""

import os
from datetime import datetime, timezone


class SubprocessLoggingService:
    """Capture and store raw stdout/stderr of Ruff, Mypy, and Pylint into .excelsior/logs/raw_[tool].log."""

    def __init__(self, log_dir: str = ".excelsior/logs") -> None:
        self._log_dir = log_dir

    def log_raw(self, tool: str, stdout: str, stderr: str) -> None:
        """Append raw tool output to raw_{tool}.log with a run header."""
        os.makedirs(self._log_dir, exist_ok=True)
        log_path = os.path.join(self._log_dir, f"raw_{tool}.log")
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"\n{'='*60}\n[{now}] {tool.upper()} raw output\n{'='*60}\n")
            if stdout:
                f.write("--- stdout ---\n")
                f.write(stdout)
                if not stdout.endswith("\n"):
                    f.write("\n")
            if stderr:
                f.write("--- stderr ---\n")
                f.write(stderr)
                if not stderr.endswith("\n"):
                    f.write("\n")
