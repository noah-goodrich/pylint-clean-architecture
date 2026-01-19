"""Contract Integrity checks (W9201)."""

from typing import TYPE_CHECKING, Optional

import astroid  # type: ignore[import-untyped]

if TYPE_CHECKING:
    from pylint.lint import PyLinter
from pylint.checkers import BaseChecker

from clean_architecture_linter.config import ConfigurationLoader
from clean_architecture_linter.helpers import get_node_layer
from clean_architecture_linter.layer_registry import LayerRegistry


class ContractChecker(BaseChecker):
    """W9201: Expert-Grade Contract Integrity enforcement."""

    name = "clean-arch-contracts"

    def __init__(self, linter: Optional["PyLinter"] = None) -> None:
        self.msgs = {
            "W9201": (
                "Contract Integrity Violation: Infrastructure class %s "
                "must inherit from a Domain Protocol. Clean Fix: Define a Protocol in Domain and inherit from it.",
                "contract-integrity-violation",
                "Infrastructure classes must inherit from a Domain Protocol "
                "(module path contains '.domain.' and name ends with 'Protocol').",
            ),
            "W9202": (
                "Concrete Method Stub: Method %s is a stub. Implement the logic. Clean Fix: Implement the method or "
                "remove it if not needed.",
                "concrete-method-stub",
                "Concrete methods in infrastructure should not be empty stubs.",
            ),
        }
        super().__init__(linter)
        self.config_loader = ConfigurationLoader()

    def visit_classdef(self, node: astroid.nodes.ClassDef) -> None:
        """
        Check if infrastructure classes implement domain protocols.
        Uses node.ancestors() for semantic enforcement.
        """
        layer = get_node_layer(node, self.config_loader)

        # Only enforce on Infrastructure layer
        if layer != LayerRegistry.LAYER_INFRASTRUCTURE:
            return

        # Skip base classes/interfaces if they are in infrastructure but are generic
        if node.name.endswith("Base") or node.name.startswith("Base"):
            return

        # Skip private helper classes
        if node.name.startswith("_") or node.name.startswith("Test"):
            return

        # Skip Exceptions
        # Logic: Check if any ancestor is named 'Exception'
        # Note: In a real AST, we might want to resolve to builtins.Exception
        # but name-based check is safer for linter speed/robustness.
        if any(ancestor.name == "Exception" for ancestor in node.ancestors()):
            return

        # 1. Must have a Domain Protocol ancestor
        if not self._has_domain_protocol_ancestor(node):
            self.add_message("contract-integrity-violation", node=node, args=(node.name,))
            return

        # 2. Expert-Grade: Public methods must be defined in the Protocol
        protocol_methods = self._get_protocol_methods(node)
        for member in node.methods():
            member_name: str = member.name
            if member_name.startswith("_"):
                continue

            # Common exclusions for constructors
            if member_name in ("__init__", "__post_init__"):
                continue

            if member_name not in protocol_methods:
                self.add_message(
                    "contract-integrity-violation",
                    node=member,
                    args=(f"{node.name}.{member.name} (not in Protocol)",),
                )

    def visit_functiondef(self, node: astroid.nodes.FunctionDef) -> None:
        """W9202: Detect stubs in concrete classes."""
        # Only check methods in classes
        if not isinstance(node.parent, astroid.nodes.ClassDef):
            return

        # Skip protocols and base classes
        if any(getattr(b, "name", "") == "Protocol" for b in node.parent.bases) or node.parent.name.endswith(
            "Protocol"
        ):
            return

        if node.name.startswith("_") and node.name not in ("__init__", "__post_init__"):
            return

        # Skip abstract methods
        if node.decorators:
            for decorator in node.decorators.nodes:
                # Handle @abstractmethod and @abc.abstractmethod
                name = ""
                if isinstance(decorator, astroid.nodes.Name):
                    name = decorator.name
                elif isinstance(decorator, astroid.nodes.Attribute):
                    name = decorator.attrname

                if name == "abstractmethod":
                    return

        if self._is_stub(node):
            self.add_message("concrete-method-stub", node=node, args=(node.name,))

    def _is_stub(self, node: astroid.nodes.FunctionDef) -> bool:
        """Check if a function body is just a stub (pass, ..., return None)."""
        body = node.body
        if not body:
            return True

        for stmt in body:
            if isinstance(stmt, astroid.nodes.Pass):
                continue
            if (
                isinstance(stmt, astroid.nodes.Expr)
                and isinstance(stmt.value, astroid.nodes.Const)
                and stmt.value.value is Ellipsis
            ):
                continue
            if isinstance(stmt, astroid.nodes.Return) and (
                stmt.value is None or (isinstance(stmt.value, astroid.nodes.Const) and stmt.value.value is None)
            ):
                continue
            # If we find anything else (like an IF that might be a stub, or a real call)
            # we need to decide if it's a stub.
            # The legacy tests had a 'sneaky nested branch stub':
            # if False: pass; return None
            if (
                isinstance(stmt, astroid.nodes.If)
                and all(self._is_stmt_stub(s) for s in stmt.body)
                and (not stmt.orelse or all(self._is_stmt_stub(s) for s in stmt.orelse))
            ):
                continue
            return False
        return True

    def _is_stmt_stub(self, stmt: astroid.nodes.NodeNG) -> bool:
        if isinstance(stmt, astroid.nodes.Pass):
            return True
        if isinstance(stmt, astroid.nodes.Expr) and isinstance(stmt.value, astroid.nodes.Const):
            return stmt.value.value is Ellipsis
        if isinstance(stmt, astroid.nodes.Return):
            return stmt.value is None or (isinstance(stmt.value, astroid.nodes.Const) and stmt.value.value is None)
        return False

    def _get_protocol_methods(self, node: astroid.nodes.ClassDef) -> set[str]:
        """Collect public method names from all Domain Protocol ancestors."""
        methods = set()
        for ancestor in node.ancestors():
            if self._is_domain_protocol(ancestor):
                for method in ancestor.methods():
                    method_name: str = method.name
                    if not method_name.startswith("_"):
                        methods.add(method_name)
        return methods

    def _has_domain_protocol_ancestor(self, node: astroid.nodes.ClassDef) -> bool:
        """Check if any ancestor is a domain protocol."""
        return any(self._is_domain_protocol(ancestor) for ancestor in node.ancestors())

    def _is_domain_protocol(self, ancestor: astroid.nodes.ClassDef) -> bool:
        """Identify if an ancestor class is a Domain Protocol."""
        try:
            # Check for Protocol inheritance directly if possible
            is_protocol = any(getattr(b, "name", "") == "Protocol" for b in ancestor.bases)

            ancestor_module = ancestor.root().name
            # Rule: module path contains '.domain.' and name ends with 'Protocol'
            # OR it inherits from Protocol and is in a domain module
            in_domain = ".domain." in f".{ancestor_module}."

            ancestor_name: str = ancestor.name
            if in_domain and (ancestor_name.endswith("Protocol") or is_protocol):
                return True
        except (AttributeError, ValueError):
            pass
        return False
