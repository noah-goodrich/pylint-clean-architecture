"""Contract Integrity checks (W9201)."""

from typing import TYPE_CHECKING, Optional

import astroid  # type: ignore[import-untyped]

if TYPE_CHECKING:
    from pylint.lint import PyLinter

from pylint.checkers import BaseChecker

from clean_architecture_linter.config import ConfigurationLoader
from clean_architecture_linter.domain.protocols import PythonProtocol
from clean_architecture_linter.layer_registry import LayerRegistry


class ContractChecker(BaseChecker):
    """W9201: Contract Integrity (Domain Interface) enforcement."""

    name: str = "clean-arch-contracts"

    def __init__(self, linter: "PyLinter", python_gateway: Optional[PythonProtocol] = None) -> None:
        self.msgs = {
            "W9201": (
                "Contract Integrity Violation: Class '%s' in infrastructure layer must inherit from a Domain Protocol. "
                "Clean Fix: Define a Protocol in the domain layer and implement it here.",
                "contract-integrity-violation",
                "Ensure infrastructure classes implement a domain-defined interface.",
            ),
            "W9202": (
                "Concrete Method Stub: Method '%s' has no implementation but is not marked as abstract. "
                "Clean Fix: Add implementation or use @abstractmethod.",
                "concrete-method-stub",
                "Methods should not be empty unless explicitly marked as abstract.",
            ),
        }
        super().__init__(linter)
        self.config_loader = ConfigurationLoader()
        self._python_gateway = python_gateway

    def visit_classdef(self, node: astroid.nodes.ClassDef) -> None:
        """Verify infrastructure classes implement domain protocols."""
        layer = self._python_gateway.get_node_layer(node, self.config_loader)

        if layer != LayerRegistry.LAYER_INFRASTRUCTURE:
            return

        # Exempt base classes if they are purely abstract/mixins - detected via naming convention?
        # NO. We only exempt things that are proven to be outside our jurisdiction or are Exceptions.
        if self._python_gateway.is_exception_node(node):
            return

        if not node.bases:
            self.add_message("contract-integrity-violation", node=node, args=(node.name,))
            return

        has_domain_base: bool = False
        domain_protos = []
        for base in node.ancestors():
            # Dynamic Exception Check
            if self._python_gateway.is_exception_node(base):
                has_domain_base: bool = True
                break

            # Check upstream layer dynamically
            root = base.root()
            if not hasattr(root, "name"):
                continue
            base_layer = self.config_loader.get_layer_for_module(root.name)
            if base_layer == LayerRegistry.LAYER_DOMAIN:
                has_domain_base: bool = True
                domain_protos.append(base)

        if not has_domain_base:
            self.add_message("contract-integrity-violation", node=node, args=(node.name,))
        else:
            # Check for public methods NOT in protocol
            self._check_extra_methods(node, domain_protos)

    def _check_extra_methods(self, node: astroid.nodes.ClassDef, protos: list[astroid.nodes.ClassDef]) -> None:
        """Flag public methods that are not defined in any inherited protocol."""
        proto_methods = set()
        for proto in protos:
            try:
                for method in proto.methods():
                    proto_methods.add(method.name)
            except AttributeError:
                continue

        for method in node.methods():
            if method.name.startswith("_") or method.name == "__init__":
                continue
            # Also skip if it's a property or other decorator-based method?
            # For now, just public methods.
            if method.name not in proto_methods:
                self.add_message("contract-integrity-violation", node=method, args=(node.name,))

    def visit_functiondef(self, node: astroid.nodes.FunctionDef) -> None:
        """W9202: Detect concrete method stubs."""
        # Manual check for abstract decorators to avoid being too smart with ellipsis
        is_officially_abstract: bool = False
        if node.decorators:
            for decorator in node.decorators.nodes:
                if "abstract" in decorator.as_string():
                    is_officially_abstract: bool = True
                    break

        if is_officially_abstract or node.name.startswith("_") or node.is_generator():
            return

        # Skip protocols
        if isinstance(node.parent, astroid.nodes.ClassDef):
            parent = node.parent
            # Check by dynamic protocol detection
            if self._python_gateway.is_protocol_node(parent):
                return

            # Check by layer
            layer = self._python_gateway.get_node_layer(parent, self.config_loader)
            if layer == LayerRegistry.LAYER_DOMAIN:
                return

        if self._is_stub(node):
            self.add_message("concrete-method-stub", node=node, args=(node.name,))

    def _is_stub(self, node: astroid.nodes.FunctionDef) -> bool:
        """Check if a function body is a stub (pass, ..., return None)."""
        body = node.body
        if not body:
            return True

        # Functional no-ops
        for stmt in body:
            if isinstance(stmt, astroid.nodes.Pass):
                continue
            if isinstance(stmt, astroid.nodes.Expr) and (
                isinstance(stmt.value, astroid.nodes.Const)
                and (stmt.value.value is Ellipsis or stmt.value.value is None)
            ):
                continue
            if isinstance(stmt, astroid.nodes.Return) and (
                not stmt.value or (isinstance(stmt.value, astroid.nodes.Const) and stmt.value.value is None)
            ):
                continue
            if isinstance(stmt, astroid.nodes.If):
                # Handle 'if False: pass'
                if isinstance(stmt.test, astroid.nodes.Const) and not stmt.test.value:
                    continue
            return False

        return True
