"""Unit tests for StubAuthority: .pyi loading and attribute resolution."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from clean_architecture_linter.infrastructure.services.stub_authority import (
    StubAuthority,
)


class TestStubAuthorityGetStubPath:
    """Tests for StubAuthority.get_stub_path."""

    def test_astroid_resolves_to_core_astroid_pyi(self) -> None:
        sa = StubAuthority()
        p = sa.get_stub_path("astroid", None)
        assert p is not None
        assert p.endswith("stubs/core/astroid.pyi")
        assert Path(p).exists()

    def test_astroid_nodes_resolves_to_core_astroid_pyi(self) -> None:
        sa = StubAuthority()
        p = sa.get_stub_path("astroid.nodes", None)
        assert p is not None
        assert "astroid.pyi" in p
        assert Path(p).exists()

    def test_unknown_module_returns_none_without_project_root(self) -> None:
        sa = StubAuthority()
        assert sa.get_stub_path("nonexistent.foo.bar", None) is None

    def test_project_stubs_override_unknown_core(self) -> None:
        sa = StubAuthority()
        with tempfile.TemporaryDirectory() as tmp:
            stubs_dir = Path(tmp) / "stubs"
            stubs_dir.mkdir()
            (stubs_dir / "snowflake").mkdir()
            (stubs_dir / "snowflake" / "connector.pyi").write_text(
                "class SnowflakeConnection:\n    pass\n"
            )
            p = sa.get_stub_path("snowflake.connector", tmp)
            assert p is not None
            assert "snowflake/connector.pyi" in p.replace("\\", "/")
            assert Path(p).exists()

    def test_project_stubs_nonexistent_returns_none(self) -> None:
        sa = StubAuthority()
        with tempfile.TemporaryDirectory() as tmp:
            assert sa.get_stub_path("snowflake.connector", tmp) is None

    def test_project_root_none_skips_project_stubs(self) -> None:
        sa = StubAuthority()
        # Would only find in project; with None we should not look
        assert sa.get_stub_path("snowflake.connector", None) is None


class TestStubAuthorityGetAttributeType:
    """Tests for StubAuthority.get_attribute_type."""

    def test_violation_location_returns_builtins_str(self) -> None:
        sa = StubAuthority()
        r = sa.get_attribute_type(
            "clean_architecture_linter.domain.rules", "Violation", "location", None
        )
        assert r == "builtins.str"

    def test_violation_wrong_module_returns_none(self) -> None:
        """Fully generic: wrong module (builtins) does not resolve; no class-name special-case."""
        sa = StubAuthority()
        r = sa.get_attribute_type("builtins", "Violation", "location", None)
        assert r is None

    def test_classdef_locals_returns_builtins_dict(self) -> None:
        sa = StubAuthority()
        r = sa.get_attribute_type("astroid.nodes", "ClassDef", "locals", None)
        assert r == "builtins.dict"

    def test_classdef_locals_via_astroid_module(self) -> None:
        sa = StubAuthority()
        r = sa.get_attribute_type("astroid", "ClassDef", "locals", None)
        assert r == "builtins.dict"

    def test_functiondef_name_returns_builtins_str(self) -> None:
        sa = StubAuthority()
        r = sa.get_attribute_type("astroid.nodes", "FunctionDef", "name", None)
        assert r == "builtins.str"

    def test_nodeng_qname_via_base_not_in_stub_as_attr(self) -> None:
        """NodeNG has qname() as method, not @property; we only do AnnAssign/@property."""
        sa = StubAuthority()
        r = sa.get_attribute_type("astroid.nodes", "NodeNG", "qname", None)
        # qname is a regular method; _find_attr_in_stub_ast only returns for AnnAssign or @property
        assert r is None

    def test_nonexistent_class_returns_none(self) -> None:
        sa = StubAuthority()
        r = sa.get_attribute_type("astroid.nodes", "NonExistentClass", "x", None)
        assert r is None

    def test_nonexistent_attribute_returns_none(self) -> None:
        sa = StubAuthority()
        r = sa.get_attribute_type("astroid.nodes", "ClassDef", "nonexistent_attr", None)
        assert r is None

    def test_project_stub_attribute_type(self) -> None:
        sa = StubAuthority()
        with tempfile.TemporaryDirectory() as tmp:
            stubs_dir = Path(tmp) / "stubs"
            stubs_dir.mkdir()
            (stubs_dir / "mylib").mkdir()
            (stubs_dir / "mylib" / "api.pyi").write_text(
                "class MyClass:\n    value: str\n"
            )
            r = sa.get_attribute_type("mylib.api", "MyClass", "value", tmp)
            assert r == "builtins.str"

    def test_project_stub_nonexistent_attr_returns_none(self) -> None:
        sa = StubAuthority()
        with tempfile.TemporaryDirectory() as tmp:
            stubs_dir = Path(tmp) / "stubs"
            stubs_dir.mkdir()
            (stubs_dir / "mylib").mkdir()
            (stubs_dir / "mylib" / "api.pyi").write_text(
                "class MyClass:\n    value: str\n"
            )
            r = sa.get_attribute_type("mylib.api", "MyClass", "other", tmp)
            assert r is None

    def test_annotation_dict_str_list_resolves_to_builtins_dict(self) -> None:
        """dict[str, list[X]] in stub -> builtins.dict. Covered by ClassDef.locals."""
        sa = StubAuthority()
        r = sa.get_attribute_type("astroid.nodes", "ClassDef", "locals", None)
        assert r == "builtins.dict"


class TestStubAuthorityCoreStubExistence:
    """Ensure core astroid.pyi is present and well-formed."""

    def test_core_astroid_pyi_exists(self) -> None:
        from clean_architecture_linter.infrastructure.services.stub_authority import (
            _core_stubs_dir,
        )

        core = _core_stubs_dir()
        astroid_pyi = core / "astroid.pyi"
        assert astroid_pyi.exists(), "stubs/core/astroid.pyi must exist"

    def test_core_astroid_pyi_defines_required_classes(self) -> None:
        import ast

        from clean_architecture_linter.infrastructure.services.stub_authority import (
            _core_stubs_dir,
        )

        core = _core_stubs_dir()
        astroid_pyi = core / "astroid.pyi"
        tree = ast.parse(astroid_pyi.read_text())
        classes = {n.name for n in tree.body if isinstance(n, ast.ClassDef)}
        assert "NodeNG" in classes
        assert "ClassDef" in classes
        assert "FunctionDef" in classes

    def test_core_astroid_pyi_classdef_has_locals(self) -> None:
        import ast

        from clean_architecture_linter.infrastructure.services.stub_authority import (
            _core_stubs_dir,
        )

        core = _core_stubs_dir()
        astroid_pyi = core / "astroid.pyi"
        tree = ast.parse(astroid_pyi.read_text())
        classes = {n.name: n for n in tree.body if isinstance(n, ast.ClassDef)}
        assert "ClassDef" in classes
        cdef = classes["ClassDef"]
        attrs = [
            n.target.id
            for n in cdef.body
            if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name)
        ]
        assert "locals" in attrs

    def test_core_rules_pyi_violation_has_location(self) -> None:
        import ast

        from clean_architecture_linter.infrastructure.services.stub_authority import (
            _core_stubs_dir,
        )

        core = _core_stubs_dir()
        rules_pyi = core / "clean_architecture_linter" / "domain" / "rules.pyi"
        assert rules_pyi.exists(), "stubs/core/clean_architecture_linter/domain/rules.pyi must exist"
        tree = ast.parse(rules_pyi.read_text())
        classes = {n.name: n for n in tree.body if isinstance(n, ast.ClassDef)}
        assert "Violation" in classes
        viol = classes["Violation"]
        attrs = [
            n.target.id
            for n in viol.body
            if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name)
        ]
        assert "location" in attrs
