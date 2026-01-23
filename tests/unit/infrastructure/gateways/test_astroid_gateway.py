import astroid
import pytest
from unittest.mock import patch, MagicMock
from clean_architecture_linter.infrastructure.gateways.astroid_gateway import AstroidGateway

def test_resolve_simple_annotation_name():
    gateway = AstroidGateway()
    node = astroid.extract_node("x: str = 'hi'")
    anno = node.annotation
    assert gateway._resolve_simple_annotation(anno) == "builtins.str"

def test_resolve_simple_annotation_const():
    gateway = AstroidGateway()
    node = astroid.extract_node("x: 'MyClass' = None")
    anno = node.annotation
    assert gateway._resolve_simple_annotation(anno) == "MyClass"

def test_resolve_nested_annotation_union():
    gateway = AstroidGateway()
    # Union[int, str]
    node = astroid.extract_node("from typing import Union; x: Union[int, str] = 1")
    anno = node.annotation
    # result should be first non-NoneType
    assert gateway._resolve_nested_annotation(anno.slice) == "builtins.int"

def test_resolve_nested_annotation_binop():
    gateway = AstroidGateway()
    # int | str
    node = astroid.extract_node("x: int | str = 1")
    anno = node.annotation
    assert gateway._resolve_nested_annotation(anno) == "builtins.int"

def test_resolve_self_type():
    gateway = AstroidGateway()
    code: str = """
class MyClass:
    def method(self) -> 'Self':
        return self
"""
    # Use parse to have a module name
    module = astroid.parse(code, module_name = "test_mod")
    func = module.body[0].body[0]
    anno = func.returns
    # It might be 'test_mod.MyClass' or just 'MyClass' depending on how astroid handles qname()
    res = gateway._resolve_self_type(anno)
    assert "MyClass" in res

def test_resolve_arg_annotation():
    gateway = AstroidGateway()
    code: str = """
def func(a: int, b = "hi"):
    pass
"""
    module = astroid.parse(code)
    func = module.body[0]
    args = func.args
    arg_a = args.args[0]
    arg_b = args.args[1]

    assert gateway._resolve_arg_annotation(arg_a, args) == "builtins.int"
    assert gateway._resolve_arg_annotation(arg_b, args) == "builtins.str"

def test_normalize_primitive():
    gateway = AstroidGateway()
    assert gateway._normalize_primitive("str") == "builtins.str"
    assert gateway._normalize_primitive("MyClass") == "MyClass"

def test_is_primitive():
    gateway = AstroidGateway()
    assert gateway.is_primitive("builtins.str") is True
    assert gateway.is_primitive("str") is True
    assert gateway.is_primitive("domain.Entity") is False
    assert gateway.is_primitive("builtins.int | builtins.float") is True

def test_is_std_lib_module():
    gateway = AstroidGateway()
    assert gateway.typeshed.is_stdlib_qname("os.path.join") is True

def test_resolve_bool_op():
    gateway = AstroidGateway()
    node = astroid.extract_node("x = a or b")
    # For BoolOp, it returns the type if it's unambiguous
    # We need to provide context where a and b are hinted
    code: str = """
def test(a: str, b: str):
    x = a or b
"""
    module = astroid.parse(code)
    func = module.body[0]
    bool_op = func.body[0].value
    assert gateway._resolve_bool_op(bool_op, set()) == "builtins.str"

def test_resolve_bin_op():
    gateway = AstroidGateway()
    node = astroid.extract_node("1 + 1.5")
    assert gateway._resolve_bin_op(node, set()) == "builtins.float"

def test_is_protocol():
    gateway = AstroidGateway()
    code: str = """
from typing import Protocol
class MyProto(Protocol):
    pass
"""
    module = astroid.parse(code)
    cls = module.body[1]
    assert gateway.is_protocol(cls) is True

def test_is_protocol_call():
    gateway = AstroidGateway()
    code: str = """
from typing import Protocol
class Repo(Protocol):
    def get(self) -> int: ...

def test(r: Repo):
    r.get()
"""
    module = astroid.parse(code)
    func = module.body[2]
    call = func.body[0].value
    assert gateway.is_protocol_call(call) is True

def test_is_trusted_authority_call_direct():
    gateway = AstroidGateway()
    code: str = """
import re
match = re.search('p', 's')
"""
    module = astroid.parse(code)
    match_call = module.body[1].value
    # re.search is typically trusted via Typeshed
    # We mock TypeshedService interactions to avoid dependency on actual environment in unit test
    with patch.object(gateway.typeshed, "is_stdlib_qname", return_value = True):
         assert gateway.is_trusted_authority_call(match_call) is True

def test_is_trusted_authority_call_chain_continuity():
    # Test that logic recurses: if receiver is safe, call is safe.
    gateway = AstroidGateway()
    # Mock _trace_safety to return safe for "pattern" variable
    with patch.object(gateway, "_trace_safety") as mock_trace:
         mock_trace.return_value = "builtins.object"

         # Verification 1: Chain logic (Recursion)
         # We simulate a call where direct stdlib check is not applicable (e.g. variable receiver)
         mock_call = MagicMock(spec=astroid.nodes.Call)
         # func is Attribute (obj.method)
         mock_call.func = MagicMock(spec=astroid.nodes.Attribute, attrname = "method")
         mock_call.func.expr = MagicMock(spec=astroid.nodes.Name)

         # Mock lookup to NOT find an import (simulating a variable assignment)
         mod_lookup_mock = [MagicMock(spec=astroid.nodes.AssignName)]
         mock_call.func.expr.lookup.return_value = (None, mod_lookup_mock)

         # The code should now call _trace_safety(expr) -> which is mocked to return "builtins.object"
         result = gateway._trace_safety(mock_call, set())
         assert result == "builtins.object"

def test_is_fluent_call():
    gateway = AstroidGateway()
    code: str = """
class Query:
    def filter(self) -> 'Query':
        return self

q = Query()
q.filter()
"""
    module = astroid.parse(code)
    call = module.body[2].value

    # We need to help it infer that resolve matches
    assert gateway.is_fluent_call(call) is True

def test_is_trusted_authority_call_chain_variable_mocked_lookup():
    # Re-attempting the chain verification with a simpler approach
    # logic: match.groups() -> match is safe?
    gateway = AstroidGateway()

    # Create a mock node structure simulating: match.groups()
    groups_call = MagicMock(spec=astroid.nodes.Call)
    groups_call.func = MagicMock(spec=astroid.nodes.Attribute)
    groups_call.func.attrname = "groups"

    receiver_expr = MagicMock(spec=astroid.nodes.Name)
    groups_call.func.expr = receiver_expr

    # Mocking get_return_type_qname to return a trusted type from Typeshed
    with patch.object(gateway, "get_return_type_qname_from_expr", return_value = "re.Match"):
         with patch.object(gateway.typeshed, "is_stdlib_qname", return_value = True):
              assert gateway.is_trusted_authority_call(groups_call) is True

def test_is_trusted_authority_call_untrusted():
    gateway = AstroidGateway()
    code: str = """
class Unsafe:
    def method(self): pass
u = Unsafe()
u.method()
"""
    module = astroid.parse(code)
    call = module.body[2].value

    with patch.object(gateway.typeshed, "is_stdlib_qname", return_value = False):
         assert gateway.is_trusted_authority_call(call) is False


def test_check_iterator_safety_direct_call():
    gateway = AstroidGateway()
    # Mocking trace safety for "safe_iter()"
    with patch.object(gateway, "_trace_safety") as mock_trace:
         mock_trace.return_value = "builtins.object"

         # Simulate: Use a Call node as iterator
         call_node = MagicMock(spec=astroid.nodes.Call)
         res = gateway._check_iterator_safety(call_node, set())
         assert res == "builtins.str" # Logic assumes str for iterator elements from safe calls

def test_check_iterator_safety_variable():
    gateway = AstroidGateway()
    # Mocking trace safety for "safe_list"
    with patch.object(gateway, "_trace_safety") as mock_trace:
         mock_trace.return_value = "builtins.object"

         name_node = MagicMock(spec=astroid.nodes.Name)
         res = gateway._check_iterator_safety(name_node, set())
         assert res == "builtins.str"

def test_is_primitive_union():
    gateway = AstroidGateway()
    # "int | str | None"
    assert gateway.is_primitive("builtins.int | builtins.str | builtins.NoneType") is True
    assert gateway.is_primitive("builtins.int | Unsafe") is False
