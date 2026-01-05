"""Contract alignment checks (W9201)."""

# AST checks often violate Demeter by design
# pylint: disable=law-of-demeter-violation
import astroid  # type: ignore[import-untyped]
from pylint.checkers import BaseChecker


class ContractChecker(BaseChecker):
    """Enforce Protocol-based public visibility."""

    name = "clean-arch-contracts"
    msgs = {
        "W9201": (
            "Unjustified public method: %s is not defined in any Protocol. Mark as _private or add to Protocol.",
            "unjustified-public-method",
            "Public methods must be declared in a Protocol or ABC.",
        ),
        "W9210": (
            "Concrete method stub: %s is empty (pass/.../NotImplementedError). Implement it or move to Protocol.",
            "concrete-method-stub",
            "Concrete methods in implementation classes should not be empty stubs.",
        ),
    }

    def __init__(self, linter=None):
        super().__init__(linter)
        self.config_loader = None
        self._protocol_methods = set()
        self._current_class = None
        self._is_protocol = False

    def visit_classdef(self, node):
        """Collect protocol methods from base classes."""
        self._current_class = node
        self._protocol_methods = set()
        self._is_protocol = False

        # Collect methods from all base classes (Protocols, ABCs)
        for base in node.bases:
            # Check if this class itself is a Protocol
            if hasattr(base, "name") and base.name == "Protocol":
                self._is_protocol = True

            # Try to infer the base class
            try:
                for inferred in base.infer():
                    if inferred is astroid.Uninferable:
                        continue
                    if isinstance(inferred, astroid.nodes.ClassDef):
                        # Also check if inferred base is Protocol
                        if inferred.name == "Protocol":
                            self._is_protocol = True
                        for method in inferred.mymethods():
                            self._protocol_methods.add(method.name)
            except astroid.InferenceError:
                continue

    def leave_classdef(self, _node):
        """Reset state when leaving class."""
        self._current_class = None
        self._protocol_methods = set()

    def visit_functiondef(self, node):
        """Check if public method is in protocol."""
        if self._current_class is None or self._is_protocol:
            return  # Skip module-level or Protocol definitions

        # Skip abstract methods
        if node.decorators:
            for decorator in node.decorators.nodes:
                if isinstance(decorator, astroid.nodes.Name) and decorator.name == "abstractmethod":
                    return
                if isinstance(decorator, astroid.nodes.Attribute) and decorator.attrname == "abstractmethod":
                    return

        # Skip private/protected methods
        if node.name.startswith("_"):
            return

        # Skip Pylint visitor methods
        if node.name.startswith("visit_") or node.name.startswith("leave_"):
            return

        # W9210: Check if it's a stub (independent of protocol mapping)
        if self._is_stub(node):
            self.add_message("concrete-method-stub", node=node, args=(node.name,))

        # Skip if we have no protocols to check against (for public method check)
        if not self._protocol_methods:
            return

        # Check if method is defined in a protocol
        if node.name not in self._protocol_methods:
            self.add_message("unjustified-public-method", node=node, args=(node.name,))

    def _is_stub(self, node):
        """
        Check if function body is effectively empty/stubbed.
        Spirit over Letter: Catches return, return None, and nested empty branches.
        """
        # Skip base classes that define the interface defaults
        if self._current_class and self._current_class.name in ("Rule", "BaseRepository", "BaseUseCase"):
            return False

        for stmt in node.body:
            if self._is_ignored_stub_stmt(stmt):
                continue
            if self._is_return_stub(stmt):
                continue
            if self._is_raise_stub(stmt):
                continue
            if isinstance(stmt, astroid.nodes.If):
                if self._is_stub_list(stmt.body) and self._is_stub_list(stmt.orelse):
                    continue
            return False
        return True

    def _is_ignored_stub_stmt(self, stmt):
        """Check for docstrings, pass, or ellipsis."""
        if isinstance(stmt, astroid.nodes.Pass):
            return True
        if isinstance(stmt, astroid.nodes.Expr):
            val = stmt.value
            if isinstance(val, astroid.nodes.Const):
                return isinstance(val.value, str) or val.value is Ellipsis
        return False

    def _is_return_stub(self, stmt):
        """Check for return None or return []."""
        if not isinstance(stmt, astroid.nodes.Return):
            return False
        val = stmt.value
        if val is None:
            return True
        if isinstance(val, astroid.nodes.Const) and val.value is None:
            return True
        # Empty collection stubs
        if isinstance(val, astroid.nodes.List):
            return not val.elts
        if isinstance(val, astroid.nodes.Dict):
            return not val.items

        is_set_call = (
            isinstance(val, astroid.nodes.Call)
            and isinstance(val.func, astroid.nodes.Name)
            and val.func.name == "set"
            and not val.args
        )
        return is_set_call

    def _is_raise_stub(self, stmt):
        """Check for raise NotImplementedError."""
        if not isinstance(stmt, astroid.nodes.Raise):
            return False
        exc = stmt.exc
        if isinstance(exc, astroid.nodes.Name) and exc.name == "NotImplementedError":
            return True
        return (
            isinstance(exc, astroid.nodes.Call)
            and isinstance(exc.func, astroid.nodes.Name)
            and exc.func.name == "NotImplementedError"
        )

    def _is_stub_list(self, nodes):
        """Helper to check if a list of nodes is purely stubs."""
        if not nodes:
            return True
        # Create a mock node to reuse _is_stub logic
        mock_node = type("MockNode", (), {"body": nodes})
        return self._is_stub(mock_node)
