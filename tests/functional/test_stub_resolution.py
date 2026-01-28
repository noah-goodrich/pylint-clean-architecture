"""Functional tests: Stub-driven LOD resolution.

violation.location.split and node.locals.get must pass (no W9006) only because
of the core stub (astroid.pyi), not nominal matching.
"""

from pathlib import Path
from unittest import mock

import astroid
import pytest

from clean_architecture_linter.infrastructure.di.container import ExcelsiorContainer
from clean_architecture_linter.use_cases.checks.patterns import CouplingChecker


def _run_coupling_checker_on_code(code: str, path: str) -> list:
    """Parse code, run CouplingChecker, return clean-arch-demeter/W9006 messages."""
    node = astroid.parse(code, path=path)
    ExcelsiorContainer.reset()
    container = ExcelsiorContainer.get_instance()
    ast_gateway = container.get("AstroidGateway")
    python_gateway = container.get("PythonGateway")
    linter = mock.MagicMock()
    try:
        linter.release_messages
    except AttributeError:
        linter._msg_store = []

        def _release():
            out = getattr(linter, "_msg_store", [])
            linter._msg_store = []
            return out

        linter.release_messages = _release
    msgs = []

    def _add(*args, **kwargs):
        msgs.append((args, kwargs))

    linter.add_message = _add
    checker = CouplingChecker(linter, ast_gateway, python_gateway)
    checker._is_test_file = lambda n: False

    def walk(n):
        name = "visit_" + n.__class__.__name__.lower()
        if hasattr(checker, name):
            getattr(checker, name)(n)
        for ch in n.get_children():
            walk(ch)
        lname = "leave_" + n.__class__.__name__.lower()
        if hasattr(checker, lname):
            getattr(checker, lname)(n)

    walk(node)
    demeter = [
        m for m in msgs
        if len(m[0]) > 0 and m[0][0] in ("clean-arch-demeter", "W9006")
    ]
    return demeter


class TestViolationLocationStubResolution:
    """violation.location.split must pass via core stub (Violation.location: str)."""

    def test_violation_location_split_no_lod_violation(self, tmp_path) -> None:
        code = """
from __future__ import annotations
from clean_architecture_linter.domain.rules import Violation

def parse_location(v: Violation) -> list[str]:
    return v.location.split(":")
"""
        path = str(tmp_path / "example.py")
        (tmp_path / "example.py").write_text(code)
        msgs = _run_coupling_checker_on_code(code, path)
        assert len(msgs) == 0, "Expected no LoD for violation.location.split; got %s" % (msgs,)


class TestClassDefLocalsGetStubResolution:
    """node.locals.get must pass via core stub (ClassDef.locals: dict)."""

    def test_classdef_locals_get_no_lod_violation(self, tmp_path) -> None:
        # Use top-level import so the param annotation resolves to astroid.nodes.ClassDef
        code = """
from astroid.nodes import ClassDef

def get_local_nodes(node: ClassDef, key: str) -> list:
    return list(node.locals.get(key, []))
"""
        path = str(tmp_path / "example.py")
        (tmp_path / "example.py").write_text(code)
        msgs = _run_coupling_checker_on_code(code, path)
        assert len(msgs) == 0, "Expected no LoD for node.locals.get; got %s" % (msgs,)


class TestStubResolutionOnExistingBenchmarks:
    """Existing benchmark files that rely on stubs must pass."""

    def test_lod_astroid_api_passes(self) -> None:
        """lod-astroid-api.py: ClassDef.locals.get and FunctionDef.name.startswith must not violate."""
        p = Path(__file__).resolve().parent / "source-data" / "lod-astroid-api.py"
        if not p.exists():
            pytest.skip("lod-astroid-api.py not found")
        code = p.read_text()
        msgs = _run_coupling_checker_on_code(code, str(p))
        assert len(msgs) == 0, "lod-astroid-api.py must have no LoD; got %s" % (msgs,)
