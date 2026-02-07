"""Unit tests for StubAuthority: .pyi loading and attribute resolution."""

import tempfile
from pathlib import Path

from excelsior_architect.infrastructure.services.stub_authority import (
    StubAuthority,
)


class TestStubAuthorityGetStubPath:
    """Tests for StubAuthority.get_stub_path."""

    def test_astroid_resolves_to_bundled_stub(self) -> None:
        """Bundled astroid stub is found (as package: stubs/astroid/__init__.pyi)."""
        sa = StubAuthority()
        p = sa.get_stub_path("astroid", None)
        assert p is not None
        assert "stubs/astroid/__init__.pyi" in p.replace("\\", "/")
        assert Path(p).exists()

    def test_astroid_nodes_resolves_to_bundled_stub(self) -> None:
        """Bundled astroid.nodes stub is found (stubs/astroid/nodes.pyi)."""
        sa = StubAuthority()
        p = sa.get_stub_path("astroid.nodes", None)
        assert p is not None
        assert "stubs/astroid/nodes.pyi" in p.replace("\\", "/")
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
        """Project stubs that don't exist and aren't bundled return None."""
        sa = StubAuthority()
        with tempfile.TemporaryDirectory() as tmp:
            # Use a module that isn't in bundled stubs
            assert sa.get_stub_path(
                "some_unknown_package.submodule", tmp) is None

    def test_bundled_snowflake_connector_stub(self) -> None:
        """Bundled snowflake.connector stub is found."""
        sa = StubAuthority()
        p = sa.get_stub_path("snowflake.connector", None)
        assert p is not None
        assert "stubs/snowflake/connector.pyi" in p.replace("\\", "/")


class TestStubAuthorityGetAttributeType:
    """Tests for StubAuthority.get_attribute_type."""

    def test_wrong_module_returns_none(self) -> None:
        """Unknown module does not resolve."""
        sa = StubAuthority()
        r = sa.get_attribute_type("builtins", "SomeClass", "location", None)
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
        r = sa.get_attribute_type(
            "astroid.nodes", "NonExistentClass", "x", None)
        assert r is None

    def test_nonexistent_attribute_returns_none(self) -> None:
        sa = StubAuthority()
        r = sa.get_attribute_type(
            "astroid.nodes", "ClassDef", "nonexistent_attr", None)
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


class TestStubAuthorityBundledStubExistence:
    """Ensure bundled stubs are present and well-formed via public API only."""

    def test_bundled_astroid_stub_exists(self) -> None:
        """Bundled astroid stub exists: get_stub_path('astroid') returns an existing path."""
        sa = StubAuthority()
        p = sa.get_stub_path("astroid", None)
        assert p is not None, "bundled astroid stub must resolve"
        assert Path(p).exists(), f"stub path must exist: {p}"

    def test_bundled_astroid_nodes_stub_defines_required_classes(self) -> None:
        """Bundled astroid.nodes stub defines NodeNG, ClassDef, FunctionDef."""
        import ast

        sa = StubAuthority()
        p = sa.get_stub_path("astroid.nodes", None)
        assert p is not None
        tree = ast.parse(Path(p).read_text())
        classes = {n.name for n in tree.body if isinstance(n, ast.ClassDef)}
        assert "NodeNG" in classes
        assert "ClassDef" in classes
        assert "FunctionDef" in classes

    def test_bundled_astroid_nodes_classdef_has_locals(self) -> None:
        """Bundled astroid.nodes stub ClassDef has 'locals' attribute."""
        import ast

        sa = StubAuthority()
        p = sa.get_stub_path("astroid.nodes", None)
        assert p is not None
        tree = ast.parse(Path(p).read_text())
        classes = {n.name: n for n in tree.body if isinstance(n, ast.ClassDef)}
        assert "ClassDef" in classes
        cdef = classes["ClassDef"]
        attrs = [
            n.target.id
            for n in cdef.body
            if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name)
        ]
        assert "locals" in attrs
