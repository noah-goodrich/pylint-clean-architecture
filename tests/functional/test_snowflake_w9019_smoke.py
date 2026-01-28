"""Smoke tests: W9019 Unstable Dependency for snowflake 3-level chain.

- snowflake_unstable: no stubs -> W9019 (clean-arch-unstable-dep).
- snowflake_stable: stubs/snowflake/connector.pyi present -> no W9019.
"""

from pathlib import Path
from unittest import mock

import astroid
import pytest

from clean_architecture_linter.infrastructure.di.container import ExcelsiorContainer
from clean_architecture_linter.use_cases.checks.patterns import CouplingChecker

_SNOWFLAKE_CODE = '''
import snowflake.connector

def run_query() -> None:
    conn = snowflake.connector.connect(account="x", user="y", password="z")
    conn.cursor().execute("SELECT 1")
'''

_SNOWFLAKE_STUB_PYI = '''# EXCELSIOR GENERATED STUB: Snowflake Connector
from typing import Any, List, Optional

class SnowflakeConnection:
    def cursor(self) -> "SnowflakeCursor": ...
    def close(self) -> None: ...

class SnowflakeCursor:
    def execute(self, command: str, params: Optional[Any] = None) -> "SnowflakeCursor": ...
    def fetchall(self) -> List[tuple]: ...
    def fetchone(self) -> Optional[tuple]: ...
    @property
    def rowcount(self) -> int: ...

def connect(**kwargs: Any) -> SnowflakeConnection: ...
'''


def _run_checker_on_file(file_path: str, code: str) -> list:
    """Run CouplingChecker on code, return all (msg_id, args, kwargs) from add_message."""
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)
    Path(file_path).write_text(code)
    node = astroid.parse(code, path=file_path)
    # Ensure Module has .file for _get_project_root
    if not getattr(node, "file", None):
        node.file = file_path  # type: ignore[attr-defined]

    ExcelsiorContainer.reset()
    container = ExcelsiorContainer.get_instance()
    ast_gateway = container.get("AstroidGateway")
    python_gateway = container.get("PythonGateway")
    linter = mock.MagicMock()
    if not hasattr(linter, "release_messages"):
        linter.release_messages = lambda: []

    msgs: list = []

    def _add(msg_id: str, *args: object, **kwargs: object) -> None:
        msgs.append((msg_id, args, kwargs))

    linter.add_message = _add
    checker = CouplingChecker(linter, ast_gateway=ast_gateway, python_gateway=python_gateway)
    checker._is_test_file = lambda _: False

    def walk(n: astroid.nodes.NodeNG) -> None:
        name = "visit_" + n.__class__.__name__.lower()
        if hasattr(checker, name):
            getattr(checker, name)(n)
        for ch in n.get_children():
            walk(ch)
        lname = "leave_" + n.__class__.__name__.lower()
        if hasattr(checker, lname):
            getattr(checker, lname)(n)

    walk(node)
    return msgs


def _has_w9019(msgs: list) -> bool:
    return any(m[0] in ("clean-arch-unstable-dep", "W9019") for m in msgs)


class TestSnowflakeUnstableW9019:
    """Without stubs/snowflake/connector.pyi, 3-level chain must report W9019."""

    def test_snowflake_unstable_reports_w9019(self, tmp_path: Path) -> None:
        """snowflake.connector.connect().cursor().execute with no stub -> W9019."""
        # No pyproject, no stubs: _get_project_root may return None; get_stub_path returns None
        file_path = str(tmp_path / "snowflake_unstable.py")
        msgs = _run_checker_on_file(file_path, _SNOWFLAKE_CODE)
        assert _has_w9019(msgs), (
            "Expected W9019 (clean-arch-unstable-dep) for snowflake chain without stubs; got %s"
            % ([m[0] for m in msgs],)
        )


class TestSnowflakeStableNoW9019:
    """With stubs/snowflake/connector.pyi, W9019 must not fire."""

    def test_snowflake_stable_no_w9019(self, tmp_path: Path) -> None:
        """With stubs/snowflake/connector.pyi, W9019 must not be reported."""
        # Project root with pyproject.toml and stubs
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'smoke'\n")
        stub_dir = tmp_path / "stubs" / "snowflake"
        stub_dir.mkdir(parents=True)
        (stub_dir / "connector.pyi").write_text(_SNOWFLAKE_STUB_PYI)

        file_path = str(tmp_path / "snowflake_stable.py")
        msgs = _run_checker_on_file(file_path, _SNOWFLAKE_CODE)
        assert not _has_w9019(msgs), (
            "Expected no W9019 when stubs/snowflake/connector.pyi exists; got %s"
            % ([m[0] for m in msgs],)
        )
