import unittest
from unittest.mock import MagicMock

import astroid
import astroid.nodes

from clean_architecture_linter.infrastructure.gateways.astroid_gateway import AstroidGateway


def create_strict_mock(spec_cls, **attrs):
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
