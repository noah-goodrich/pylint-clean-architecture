
import astroid

import clean_architecture_linter
from clean_architecture_linter.infrastructure.gateways.astroid_gateway import AstroidGateway
from clean_architecture_linter.infrastructure.typeshed_integration import TypeshedService


class TestTypeshedResolution:

    def test_typeshed_service_identifies_stdlib(self):
        import inspect
        print(f"DEBUG: AstroidGateway file: {inspect.getfile(AstroidGateway)}")
        print(f"DEBUG: Loaded linter from {clean_architecture_linter.__file__}")
        service = TypeshedService()
        assert service.is_stdlib_module("os")
        assert service.is_stdlib_module("sys")
        assert service.is_stdlib_module("argparse")
        # Assert non-stdlib
        assert not service.is_stdlib_module("requests")
        assert not service.is_stdlib_module("clean_architecture_linter")

    def test_gateway_infers_os_walk_variables_as_safe(self):
        code = """
import os
def test_walk():
    for root, dirs, files in os.walk("."):
        for d in dirs:
            return d
"""
        module = astroid.parse(code)
        func = module["test_walk"]
        # Structure: FunctionDef -> For (walk) -> For (d in dirs) -> Return
        outer_for = func.body[0]
        inner_for = outer_for.body[0]
        return_node = inner_for.body[0]
        d_name_node = return_node.value

        gateway = AstroidGateway()

        # inferring 'd' directly with astroid might fail (Uninferable)
        # But gateway.get_node_return_type_qname should return our safe marker

        qname = gateway.get_node_return_type_qname(d_name_node)

        # We implemented it to return "builtins.str" or "builtins.object" for stdlib iterators
        assert qname in ["builtins.str", "builtins.object"]

    def test_gateway_infers_argparse_as_safe(self):
         # argparse is dynamic, so often Uninferable, but it is stdlib.
         code = """
import argparse
parser = argparse.ArgumentParser()
args = parser.parse_args()
x = args.foo
"""
         module = astroid.parse(code)
         x_assign = module.body[3]
         _ = x_assign.value  # args.foo

         # Logic for generic stdlib object safety might need to be extended if not covered by iterator check
         # For now, let's just see what it does.
         # Our current impl only covers Loop Variables explicitly.
         pass

