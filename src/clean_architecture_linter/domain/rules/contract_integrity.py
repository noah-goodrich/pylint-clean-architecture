"""Contract Integrity Rule (W9201) - Domain interface enforcement for infrastructure classes."""

from typing import TYPE_CHECKING

import astroid  # type: ignore[import-untyped]

from clean_architecture_linter.domain.rules import Checkable, Violation

if TYPE_CHECKING:
    from clean_architecture_linter.domain.config import ConfigurationLoader
    from clean_architecture_linter.domain.protocols import PythonProtocol


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
        if not isinstance(node, astroid.nodes.ClassDef):
            return []

        from clean_architecture_linter.domain.layer_registry import LayerRegistry

        layer = self._python_gateway.get_node_layer(node, self._config_loader)
        if layer != LayerRegistry.LAYER_INFRASTRUCTURE:
            return []

        if self._python_gateway.is_exception_node(node):
            return []

        if not node.bases:
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
        for base in node.ancestors():
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
                    message=f"Infrastructure class {node.name} must inherit from Domain Protocol.",
                    node=node,
                    message_args=(node.name,),
                )
            ]

        return self._check_extra_methods(node, domain_protos)

    def _check_extra_methods(
        self,
        node: astroid.nodes.ClassDef,
        protos: list[astroid.nodes.ClassDef],
    ) -> list[Violation]:
        """Flag public methods that are not defined in any inherited protocol."""
        proto_methods: set[str] = set()
        for proto in protos:
            try:
                for method in proto.methods():
                    proto_methods.add(method.name)
            except AttributeError:
                continue

        violations: list[Violation] = []
        for method in node.methods():
            if method.name.startswith("_") or method.name == "__init__":
                continue
            if method.name not in proto_methods:
                violations.append(
                    Violation.from_node(
                        code=self.code,
                        message=f"Public method {method.name} not in protocol.",
                        node=method,
                        message_args=(node.name,),
                    )
                )
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

        from clean_architecture_linter.domain.layer_registry import LayerRegistry

        try:
            fp = getattr(node.root(), "file", "") or ""
            if "/stubs/" in fp or (fp and fp.endswith(".pyi")):
                return []
        except Exception:
            pass

        is_officially_abstract = False
        if getattr(node, "decorators", None):
            for decorator in node.decorators.nodes:
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
            if isinstance(stmt, astroid.nodes.Expr) and isinstance(
                getattr(stmt, "value", None), astroid.nodes.Const
            ):
                val = stmt.value.value
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
