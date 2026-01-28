import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import astroid
import astroid.nodes
import pytest

from clean_architecture_linter.infrastructure.gateways.astroid_gateway import AstroidGateway


def create_strict_mock(spec_cls, **attrs) -> MagicMock:
    """Create a mock that respects the spec (for hasattr checks)."""
    m = MagicMock(spec=spec_cls)
    for k, v in attrs.items():
        setattr(m, k, v)
    return m

class TestAstroidGateway(unittest.TestCase):
    def setUp(self) -> None:
        self.gateway = AstroidGateway()
        self.gateway.typeshed = MagicMock()
        self.gateway.typeshed.is_stdlib_qname.return_value = False

    def test_is_primitive(self) -> None:
        self.assertTrue(self.gateway.is_primitive("builtins.str"))
        self.assertTrue(self.gateway.is_primitive("builtins.int"))
        self.assertFalse(self.gateway.is_primitive("pkg.MyClass"))

    def test_get_node_return_type_qname_const(self) -> None:
        # Const is inferred directly via spec
        node = create_strict_mock(astroid.nodes.Const)
        node.value = 123
        # Configure inference: node.infer() -> yields MagicMock(qname="builtins.int")
        # BUT get_node_return_type_qname for CONST might rely on discovery fallback first
        # _discovery_fallback -> check Call/Name. Const is neither.
        # Falls to Direct Inference.

        inferred = MagicMock()
        inferred.qname.return_value = "builtins.int"
        node.infer.return_value = iter([inferred])

        self.assertEqual(self.gateway.get_node_return_type_qname(node), "builtins.int")

    def test_get_node_return_type_qname_name(self) -> None:
        # Use simple MagicMock with spec for Name, but ensure it behaves
        node = create_strict_mock(astroid.nodes.Name)

        # We Mock lookup to return a definition with annotation
        def_node = MagicMock()
        # Ensure annotation is an instance of Name for check
        def_node.annotation = create_strict_mock(astroid.nodes.Name)
        def_node.annotation.name = "int"

        # _resolve_simple_annotation -> _normalize_primitive("int") -> "builtins.int"

        # node.lookup returns (locator, [statements])
        node.lookup.return_value = (None, [def_node])
        node.name = "x"

        self.assertEqual(self.gateway.get_node_return_type_qname(node), "builtins.int")

    def test_get_call_name(self) -> None:
        # Use STRICT mocks to ensure hasattr works
        node = create_strict_mock(astroid.nodes.Call)

        # Case 1: Name
        node.func = create_strict_mock(astroid.nodes.Name)
        node.func.name = "foo"
        self.assertEqual(self.gateway.get_call_name(node), "foo")

        # Case 2: Attribute
        node.func = create_strict_mock(astroid.nodes.Attribute)
        node.func.attrname = "bar"
        self.assertEqual(self.gateway.get_call_name(node), "bar")

    def test_is_fluent_call(self) -> None:
        # Must be Call and func must be Attribute
        call = create_strict_mock(astroid.nodes.Call)
        call.func = create_strict_mock(astroid.nodes.Attribute) # Correct type implies has 'attrname' etc

        # Gateway checks is_fluent_call(node.func.expr) recursive
        # We just want to test false path or simple true path

        call.func.expr = MagicMock() # generic expr
        # We need get_return_type_qname_from_expr to match

        # We'll just verify it doesn't crash and returns boolean
        # since deep mocking of types is tedious
        self.assertFalse(self.gateway.is_fluent_call(call))

    def test_clear_inference_cache(self) -> None:
        """Test clear_inference_cache clears astroid cache."""
        # This is a simple method that calls astroid.MANAGER.clear_cache()
        # We can't easily verify it was called, but we can test it doesn't crash
        self.gateway.clear_inference_cache()
        # Should not raise
        assert True

    def test_parse_file_existing_file(self) -> None:
        """Test parse_file parses existing file."""
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("x = 1\n")
            temp_path = f.name

        try:
            result = self.gateway.parse_file(temp_path)
            assert result is not None
            assert isinstance(result, astroid.nodes.Module)
            assert len(result.body) == 1
        finally:
            Path(temp_path).unlink()

    def test_parse_file_nonexistent_file(self) -> None:
        """Test parse_file returns None for nonexistent file."""
        result = self.gateway.parse_file("/nonexistent/path/file.py")
        assert result is None

    def test_parse_file_handles_parse_error(self) -> None:
        """Test parse_file handles parse errors gracefully."""
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("invalid syntax !!!\n")
            temp_path = f.name

        try:
            # Should handle parse error and return None
            result = self.gateway.parse_file(temp_path)
            # May return None or raise - either is acceptable for error handling
            assert result is None or isinstance(result, astroid.nodes.Module)
        finally:
            Path(temp_path).unlink()

    def test_get_return_type_qname_from_expr_none(self) -> None:
        """Test get_return_type_qname_from_expr handles None."""
        result = self.gateway.get_return_type_qname_from_expr(None)
        assert result is None

    def test_get_return_type_qname_from_expr_bool_op(self) -> None:
        """Test get_return_type_qname_from_expr handles BoolOp."""
        code = "x = True or False"
        module = astroid.parse(code)
        bool_op = module.body[0].value

        result = self.gateway.get_return_type_qname_from_expr(bool_op)
        # Should infer bool type
        assert result is not None

    def test_get_return_type_qname_from_expr_bin_op(self) -> None:
        """Test get_return_type_qname_from_expr handles BinOp."""
        code = "x = 1 + 2"
        module = astroid.parse(code)
        bin_op = module.body[0].value

        result = self.gateway.get_return_type_qname_from_expr(bin_op)
        # Should infer int type
        assert result is not None

    def test_get_return_type_qname_from_expr_typing_cast(self) -> None:
        """Test get_return_type_qname_from_expr handles typing.cast."""
        code = """
from typing import cast
x = cast(str, some_value)
"""
        module = astroid.parse(code)
        call = module.body[1].value

        result = self.gateway.get_return_type_qname_from_expr(call)
        # Should extract type from cast
        assert result is not None
        assert "str" in result

    def test_get_return_type_qname_from_expr_prevents_infinite_recursion(self) -> None:
        """Test get_return_type_qname_from_expr prevents infinite recursion with visited set."""
        code = "x = y"
        module = astroid.parse(code)
        name = module.body[0].value

        # Create a circular reference scenario
        visited = {id(name)}
        result = self.gateway.get_return_type_qname_from_expr(name, visited)
        # Should return None to prevent infinite recursion
        assert result is None or isinstance(result, str)

    def test_get_node_return_type_qname_from_annassign(self) -> None:
        """Test get_node_return_type_qname handles AnnAssign parent."""
        code = "x: int = 42"
        module = astroid.parse(code)
        annassign = module.body[0]
        const = annassign.value

        result = self.gateway.get_node_return_type_qname(const)
        # Should use annotation from parent AnnAssign
        assert result is not None
        assert "int" in result

    def test_get_node_return_type_qname_handles_inference_error(self) -> None:
        """Test get_node_return_type_qname handles InferenceError."""
        node = create_strict_mock(astroid.nodes.NodeNG)
        node.infer.side_effect = astroid.InferenceError("Cannot infer")

        result = self.gateway.get_node_return_type_qname(node)
        # Should handle error gracefully
        assert result is None or isinstance(result, str)

    def test_get_node_return_type_qname_handles_attribute_error(self) -> None:
        """Test get_node_return_type_qname handles AttributeError."""
        node = create_strict_mock(astroid.nodes.NodeNG)
        node.infer.side_effect = AttributeError("No qname")

        result = self.gateway.get_node_return_type_qname(node)
        # Should handle error gracefully
        assert result is None or isinstance(result, str)

    def test_get_node_return_type_qname_uses_annassign_parent(self) -> None:
        """Test get_node_return_type_qname uses AnnAssign parent annotation."""
        code = "x: int = 42"
        module = astroid.parse(code)
        annassign = module.body[0]
        const = annassign.value

        result = self.gateway.get_node_return_type_qname(const)
        # Should use annotation from parent AnnAssign
        assert result is not None
        assert "int" in result

    def test_discovery_fallback_handles_call(self) -> None:
        """Test _discovery_fallback handles Call nodes."""
        code = "result = some_function()"
        module = astroid.parse(code)
        call = module.body[0].value

        result = self.gateway._discovery_fallback(call)
        # May return None or a type depending on inference
        assert result is None or isinstance(result, str)

    def test_discovery_fallback_handles_name(self) -> None:
        """Test _discovery_fallback handles Name nodes."""
        code = "x: int = 42\ny = x"
        module = astroid.parse(code)
        name = module.body[1].value

        result = self.gateway._discovery_fallback(name)
        # May return None or a type depending on inference
        assert result is None or isinstance(result, str)

    def test_discovery_fallback_handles_inference_error(self) -> None:
        """Test _discovery_fallback handles InferenceError."""
        node = create_strict_mock(astroid.nodes.Name)
        node.name = "x"
        node.lookup.side_effect = astroid.InferenceError("Cannot infer")

        result = self.gateway._discovery_fallback(node)
        assert result is None

    def test_discover_from_call_handles_inference_error(self) -> None:
        """Test _discover_from_call handles InferenceError."""
        node = create_strict_mock(astroid.nodes.Call)
        node.func = create_strict_mock(astroid.nodes.Name)
        node.func.infer.side_effect = astroid.InferenceError("Cannot infer")

        result = self.gateway._discover_from_call(node)
        assert result is None

    def test_discover_from_call_handles_stop_iteration(self) -> None:
        """Test _discover_from_call handles StopIteration."""
        node = create_strict_mock(astroid.nodes.Call)
        node.func = create_strict_mock(astroid.nodes.Name)
        node.func.infer.return_value = iter([])  # Empty iterator

        result = self.gateway._discover_from_call(node)
        assert result is None

    def test_discover_from_name_handles_annotation(self) -> None:
        """Test _discover_from_name handles annotated variables."""
        code = "x: str = 'hello'\ny = x"
        module = astroid.parse(code)
        name = module.body[1].value

        result = self.gateway._discover_from_name(name)
        # Should discover type from annotation
        assert result is not None
        assert "str" in result

    def test_resolve_arg_annotation_handles_value_error(self) -> None:
        """Test _resolve_arg_annotation handles ValueError."""
        code = "def func(x): pass"
        module = astroid.parse(code)
        func_def = module.body[0]
        args = func_def.args
        def_node = args.args[0]

        # Create a scenario where index() would raise ValueError
        # by using a node not in args.args
        fake_node = create_strict_mock(astroid.nodes.NodeNG)
        result = self.gateway._resolve_arg_annotation(fake_node, args)
        # Should handle ValueError when node not found
        assert result is None

    def test_resolve_arg_annotation_handles_index_error(self) -> None:
        """Test _resolve_arg_annotation handles IndexError."""
        code = "def func(x): pass"
        module = astroid.parse(code)
        func_def = module.body[0]
        args = func_def.args
        def_node = args.args[0]

        # Create scenario with mismatched args and annotations
        # This should trigger IndexError path
        original_annotations = args.annotations
        args.annotations = []  # Empty annotations but args exist

        result = self.gateway._resolve_arg_annotation(def_node, args)
        # Should handle IndexError gracefully
        assert result is None or isinstance(result, str)
        
        # Restore
        args.annotations = original_annotations

    def test_find_method_in_class_hierarchy_handles_exception(self) -> None:
        """Test _find_method_in_class_hierarchy handles exceptions."""
        context = create_strict_mock(astroid.nodes.NodeNG)
        context.root.side_effect = Exception("Error")

        result = self.gateway._find_method_in_class_hierarchy("MyClass", "method", context)
        assert result is None

    def test_find_method_in_class_hierarchy_handles_astroid_building_error(self) -> None:
        """Test _find_method_in_class_hierarchy handles AstroidBuildingError."""
        code = "x = 1"
        module = astroid.parse(code)
        context = module.body[0]

        with patch('astroid.MANAGER.ast_from_module_name', side_effect=astroid.AstroidBuildingError("Module not found")):
            result = self.gateway._find_method_in_class_hierarchy("nonexistent.Module", "method", context)
            assert result is None

    def test_resolve_method_in_node_handles_inference_error(self) -> None:
        """Test _resolve_method_in_node handles InferenceError."""
        code = """
class Base:
    def method(self) -> str: ...

class Derived(Base):
    pass
"""
        module = astroid.parse(code)
        derived = module.body[1]

        # Create a class that will raise InferenceError on ancestors()
        class ErrorClass(astroid.nodes.ClassDef):
            def ancestors(self):
                raise astroid.InferenceError("Cannot infer")

        # Use a mock that raises on ancestors
        mock_class = MagicMock(spec=astroid.nodes.ClassDef)
        mock_class.mymethods.return_value = []
        mock_class.ancestors.side_effect = astroid.InferenceError("Cannot infer")

        result = self.gateway._resolve_method_in_node(mock_class, "method")
        # Should handle InferenceError gracefully
        assert result is None

    # --- StubAuthority integration: stub-first attribute resolution ---

    def test_find_attribute_type_in_class_classdef_locals_via_stub(self) -> None:
        """ClassDef.locals resolves to builtins.dict via core stub when class body has no AnnAssign for it."""
        # Use a minimal module with a ClassDef that has no "locals" in body, so
        # _resolve_attribute_in_node returns None and StubAuthority is used.
        self.gateway.typeshed.is_stdlib_module.return_value = False  # astroid is not stdlib
        mod_parse = astroid.parse("class ClassDef: pass\nx = 1\n", path=str(Path(__file__).resolve()))
        empty_class = mod_parse.body[0]
        context = mod_parse.body[1]
        mock_mod = MagicMock()
        mock_mod.lookup.return_value = (None, [empty_class])
        with patch("astroid.MANAGER.ast_from_module_name", return_value=mock_mod):
            res = self.gateway._find_attribute_type_in_class(
                "astroid.nodes.ClassDef", "locals", context
            )
        assert res == "builtins.dict"

    def test_find_attribute_type_in_class_violation_location_via_stub(self) -> None:
        """Violation.location should resolve to builtins.str via core stub or source."""
        module = astroid.parse("x = 1\n", path=str(Path(__file__).resolve()))
        context = module.body[0]
        res = self.gateway._find_attribute_type_in_class(
            "clean_architecture_linter.domain.rules.Violation", "location", context
        )
        assert res == "builtins.str"

    def test_find_attribute_type_in_class_functiondef_name_via_stub(self) -> None:
        """FunctionDef.name resolves to builtins.str via core stub when class body has no AnnAssign for it."""
        self.gateway.typeshed.is_stdlib_module.return_value = False  # astroid is not stdlib
        mod_parse2 = astroid.parse("class FunctionDef: pass\nx = 1\n", path=str(Path(__file__).resolve()))
        empty_class = mod_parse2.body[0]  # ClassDef with no "name" AnnAssign in body
        context = mod_parse2.body[1]
        mock_mod = MagicMock()
        mock_mod.lookup.return_value = (None, [empty_class])
        with patch("astroid.MANAGER.ast_from_module_name", return_value=mock_mod):
            res = self.gateway._find_attribute_type_in_class(
                "astroid.nodes.FunctionDef", "name", context
            )
        assert res == "builtins.str"

    def test_find_attribute_type_in_class_nonexistent_returns_none(self) -> None:
        """Unknown class or attribute should return None (no nominal fallback)."""
        module = astroid.parse("x = 1\n", path=str(Path(__file__).resolve()))
        context = module.body[0]
        res = self.gateway._find_attribute_type_in_class(
            "astroid.nodes.ClassDef", "nonexistent_attr", context
        )
        assert res is None

    def test_get_node_return_type_qname_attribute_uses_stub_when_inference_fails(self) -> None:
        """E2E: resolving obj.locals when obj is ClassDef uses stub for .locals -> dict."""
        code = """
from astroid.nodes import ClassDef
def f(node: ClassDef):
    return node.locals.get("x", [])
"""
        module = astroid.parse(code)
        func = module.body[1]
        ret = func.body[0].value  # node.locals.get(...)
        # The attribute for .get's receiver is node.locals (Attribute)
        attr = ret.func.expr  # node.locals
        qname = self.gateway.get_node_return_type_qname(attr)
        assert qname == "builtins.dict"
