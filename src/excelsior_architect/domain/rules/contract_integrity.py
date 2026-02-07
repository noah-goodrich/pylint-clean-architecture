"""Contract Integrity Rule (W9201) - Domain interface enforcement for infrastructure classes."""

from typing import TYPE_CHECKING, cast

import astroid

from excelsior_architect.domain.rules import Checkable, Violation

if TYPE_CHECKING:
    from excelsior_architect.domain.config import ConfigurationLoader
    from excelsior_architect.domain.protocols import PythonProtocol


class ContractIntegrityRule(Checkable):
    """
    Rule for W9201: Contract Integrity (Domain Interface) enforcement.

    Infrastructure classes must inherit from a Domain protocol and must not
    expose public methods not defined in that protocol.
    """

    code: str = "W9201"
    description: str = (
        "Contract Integrity: Infrastructure classes must implement domain protocols; "
        "no extra public methods beyond protocol."
    )
    fix_type: str = "code"

    def __init__(
        self,
        python_gateway: "PythonProtocol",
        config_loader: "ConfigurationLoader",
    ) -> None:
        self._python_gateway = python_gateway
        self._config_loader = config_loader

    def check(self, node: astroid.nodes.NodeNG) -> list[Violation]:
        """
        Check a class node for W9201 violations.

        Returns violations for:
        - Infrastructure class with no bases
        - Infrastructure class with no Domain (or Exception) base
        - Infrastructure class with public methods not in any inherited protocol
        """
        # Only ClassDef nodes have 'bases' and 'name' attributes
        if not hasattr(node, "bases") or not hasattr(node, "name"):
            return []
            return []

        from excelsior_architect.domain.layer_registry import LayerRegistry

        layer = self._python_gateway.get_node_layer(node, self._config_loader)
        if layer != LayerRegistry.LAYER_INFRASTRUCTURE:
            return []

        # Cast for type checker after runtime check
        classdef_node = cast(astroid.nodes.ClassDef, node)
        if self._python_gateway.is_exception_node(classdef_node):
            return []

        if not classdef_node.bases:
            return [
                Violation.from_node(
                    code=self.code,
                    message=f"Infrastructure class {node.name} must inherit from Domain Protocol.",
                    node=node,
                    message_args=(node.name,),
                )
            ]

        has_domain_base = False
        domain_protos: list[astroid.nodes.ClassDef] = []
        # Cast for type checker - ClassDef nodes have ancestors()
        classdef_node = cast(astroid.nodes.ClassDef, node)
        for base in classdef_node.ancestors():
            if self._python_gateway.is_exception_node(base):
                has_domain_base = True
                break
            root = base.root()
            if not hasattr(root, "name"):
                continue
            base_layer = self._config_loader.get_layer_for_module(root.name)
            if base_layer == LayerRegistry.LAYER_DOMAIN:
                has_domain_base = True
                domain_protos.append(base)

        if not has_domain_base:
            return [
                Violation.from_node(
                    code=self.code,
                    message=f"Infrastructure class {classdef_node.name} must inherit from Domain Protocol.",
                    node=classdef_node,
                    message_args=(classdef_node.name,),
                )
            ]

        return self._check_extra_methods(classdef_node, domain_protos)

    def _check_extra_methods(
        self,
        node: astroid.nodes.ClassDef,
        protos: list[astroid.nodes.ClassDef],
    ) -> list[Violation]:
        """Flag public methods that are not defined in any inherited protocol."""
        proto_methods: set[str] = set()
        for proto in protos:
            try:
                # Use mymethods() instead of methods()
                for method in proto.mymethods():
                    name = getattr(method, "name", None)
                    if name and isinstance(name, str):
                        proto_methods.add(name)
            except (AttributeError, TypeError):
                continue

        violations: list[Violation] = []
        # Use mymethods() instead of methods()
        try:
            for method in node.mymethods():
                name = getattr(method, "name", None)
                if not name or not isinstance(name, str):
                    continue
                if name.startswith("_") or name == "__init__":
                    continue
                if name not in proto_methods:
                    violations.append(
                        Violation.from_node(
                            code=self.code,
                            message=f"Public method {name} not in protocol.",
                            node=method,
                            message_args=(node.name,),
                        )
                    )
        except (AttributeError, TypeError):
            pass
        return violations


class ConcreteMethodStubRule(Checkable):
    """
    Rule for W9202: Concrete method stubs (non-abstract, non-protocol methods with stub body).
    """

    code: str = "W9202"
    description: str = "Concrete method stub: method body is pass/.../return None."
    fix_type: str = "code"

    def __init__(
        self,
        python_gateway: "PythonProtocol",
        config_loader: "ConfigurationLoader",
    ) -> None:
        self._python_gateway = python_gateway
        self._config_loader = config_loader

    def check(self, node: astroid.nodes.NodeNG) -> list[Violation]:
        """Check a function node for W9202 (concrete method stub). Returns at most one violation."""
        if not isinstance(node, astroid.nodes.FunctionDef):
            return []

        from excelsior_architect.domain.layer_registry import LayerRegistry

        try:
            fp = getattr(node.root(), "file", "") or ""
            if "/stubs/" in fp or (fp and fp.endswith(".pyi")):
                return []
        except Exception:
            pass

        is_officially_abstract = False
        decorators = getattr(node, "decorators", None)
        if decorators:
            for decorator in decorators.nodes:
                if "abstract" in getattr(decorator, "as_string", lambda: "")():
                    is_officially_abstract = True
                    break
        if is_officially_abstract or getattr(node, "name", "").startswith("_") or getattr(node, "is_generator", lambda: False)():
            return []

        parent = getattr(node, "parent", None)
        if isinstance(parent, astroid.nodes.ClassDef):
            if self._python_gateway.is_protocol_node(parent):
                return []
            layer = self._python_gateway.get_node_layer(
                parent, self._config_loader)
            if layer == LayerRegistry.LAYER_DOMAIN:
                return []

        if not self._is_stub(node):
            return []
        return [
            Violation.from_node(
                code=self.code,
                message=f"Concrete method stub: {node.name}.",
                node=node,
                message_args=(node.name,),
            )
        ]

    def _is_stub(self, node: astroid.nodes.FunctionDef) -> bool:
        body = getattr(node, "body", [])
        if not body:
            return True
        for stmt in body:
            if isinstance(stmt, astroid.nodes.Pass):
                continue
            if isinstance(stmt, astroid.nodes.Expr):
                stmt_value = getattr(stmt, "value", None)
                if isinstance(stmt_value, astroid.nodes.Const):
                    val = stmt_value.value
                    if val is Ellipsis or val is None:
                        continue
            if isinstance(stmt, astroid.nodes.Return):
                v = getattr(stmt, "value", None)
                if not v or (isinstance(v, astroid.nodes.Const) and v.value is None):
                    continue
            if isinstance(stmt, astroid.nodes.If):
                t = getattr(stmt, "test", None)
                if isinstance(t, astroid.nodes.Const) and not t.value:
                    continue
            return False
        return True
