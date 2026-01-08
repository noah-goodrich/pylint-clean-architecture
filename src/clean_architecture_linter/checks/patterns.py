"""Pattern checks (W9005, W9006)."""

import astroid  # type: ignore[import-untyped]
from pylint.checkers import BaseChecker

from clean_architecture_linter.config import ConfigurationLoader


class PatternChecker(BaseChecker):
    """W9005: Delegation anti-pattern detection with prescriptive advice."""

    name = "clean-arch-delegation"
    msgs = {
        "W9005": (
            "Delegation Anti-Pattern: %s",
            "clean-arch-delegation",
            "If/elif chains that only delegate should use Strategy or Handler patterns.",
        ),
    }

    def visit_if(self, node):
        """Check for delegation chains."""
        # Skip 'if __name__ == "__main__"' blocks
        if isinstance(node.test, astroid.nodes.Compare):
            if (
                isinstance(node.test.left, astroid.nodes.Name)
                and node.test.left.name == "__name__"
            ):
                return

        is_delegation, advice = self._check_delegation_chain(node)
        if is_delegation:
            self.add_message(
                "clean-arch-delegation",
                node=node,
                args=(advice or "Refactor to Strategy, Handler, or Adapter pattern.",),
            )

    def _check_delegation_chain(self, node, depth=0):
        """Check if if/elif chain is purely delegating."""
        if len(node.body) != 1:
            return False, None

        stmt = node.body[0]
        if not self._is_delegation_call(stmt):
            return False, None

        # Generate prescriptive advice based on condition type
        advice = "Refactor to Strategy/Handler pattern."
        if isinstance(node.test, astroid.nodes.Compare):
            if isinstance(node.test.left, astroid.nodes.Name):
                advice = "Refactor to **Strategy Pattern** using a dictionary mapping."

        # If strict guard clause (no else), it is NOT a delegation CHAIN unless deep recursion
        if not node.orelse:
            # Only flag if we are already deep in a chain (depth > 0)
            # This ignores simple 'if x: do_y()' guard clauses
            return depth > 0, advice

        if len(node.orelse) == 1:
            orelse = node.orelse[0]
            if isinstance(orelse, astroid.nodes.If):
                return self._check_delegation_chain(orelse, depth + 1)
            if self._is_delegation_call(orelse):
                # 3 branches: if/elif/else or if/elif/elif
                # Let's require depth >= 1 (so if/elif)
                return depth > 0, advice

        return False, None

    def _is_delegation_call(self, node):
        """Check if node is 'return func(...)' or 'func(...)'."""
        if isinstance(node, astroid.nodes.Return):
            return isinstance(node.value, astroid.nodes.Call)
        if isinstance(node, astroid.nodes.Expr):
            return isinstance(node.value, astroid.nodes.Call)
        return False


class CouplingChecker(BaseChecker):
    """W9006: Law of Demeter violation detection."""

    name = "clean-arch-demeter"
    msgs = {
        "W9006": (
            "Law of Demeter: Chain access (%s) exceeds one level. Create delegated method.",
            "clean-arch-demeter",
            "Object chains like a.b.c() indicate tight coupling.",
        ),
    }

    # Common patterns that are acceptable despite chain depth
    ALLOWED_TERMINAL_METHODS = {
        # Dict/data access
        "get",
        "items",
        "keys",
        "values",
        "pop",
        "setdefault",
        "clear",
        "copy",
        "update",
        # Logging/output (common façade patterns)
        "print",
        "debug",
        "info",
        "warning",
        "error",
        "critical",
        # String operations
        "format",
        "join",
        "split",
        "strip",
        "lstrip",
        "rstrip",
        "replace",
        "upper",
        "lower",
        "capitalize",
        "title",
        "startswith",
        "endswith",
        "count",
        "index",
        "find",
        # Path operations
        "exists",
        "is_dir",
        "is_file",
        "read_text",
        "write_text",
        # Common Repository/API patterns
        "save",
        "delete",
        "list",
        "iter",
        "create",
        "create_or_alter",
        "modify",
        "append",
        "extend",
        "insert",
        "remove",
        "add",
        "discard",
        "sort",
        "reverse",
        "union",
        "intersection",
        "difference",
        "symmetric_difference",
        # Fluent Builders & UI
        "add_column",
        "add_row",
        "build",
        # DB/Snowflake
        "execute",
        "fetchall",
        "cursor",
        # Crypto
        "private_bytes",
        "public_bytes",
        "public_key",
    }

    def __init__(self, linter=None):
        super().__init__(linter)
        self._locals_map = {}  # Map[variable_name] -> is_stranger (bool)

    # Common Repository/API patterns
    ALLOWED_TERMINAL_METHODS.add("modify")

    def visit_functiondef(self, _node):
        """Reset locals map for each function."""
        # Simple local tracking scope (not handling nested scopes perfectly, but sufficient for this rule)
        self._locals_map = {}

    def visit_assign(self, node):
        """Track if a local variable is created from a method call (likely a stranger)."""
        if not isinstance(node.value, astroid.nodes.Call):
            return

        # If x = obj.method(), then x is a potential stranger.
        # Unless it's a safe root/type/internal.

        # We assume stranger until proven otherwise for method returns.
        # (This is strict LoD: return values of strangers are strangers)
        for target in node.targets:
            if isinstance(target, astroid.nodes.AssignName):
                self._locals_map[target.name] = True

    def visit_call(self, node):
        """Check for Law of Demeter violations."""
        # Skip checks for test files
        root = node.root()
        file_path = getattr(root, "file", "")
        if "tests" in file_path.split("/") or "test_" in file_path.split("/")[-1]:
            return

        if self._is_method_chain_violation(node):
            return

        # Case 2: Method called on a 'stranger' variable
        # x = obj.get_thing()
        # x.do_something()  <-- Violation
        if isinstance(node.func, astroid.nodes.Attribute):
            expr = node.func.expr
            if isinstance(expr, astroid.nodes.Name):
                var_name = expr.name
                if self._locals_map.get(var_name, False):
                    # It's a method call on a variable derived from another call.
                    # We accept "Allowed Terminal Methods" on strangers (e.g. string manipulation)
                    if node.func.attrname in self.ALLOWED_TERMINAL_METHODS:
                        return

                    self.add_message(
                        "clean-arch-demeter",
                        node=node,
                        args=(f"{var_name}.{node.func.attrname} (Stranger)",),
                    )

    def _is_method_chain_violation(self, node):
        """Check direct method chains like a.b.c()"""
        # pylint: disable=too-many-return-statements
        if not isinstance(node.func, astroid.nodes.Attribute):
            return False

        chain = []
        curr = node.func
        while isinstance(curr, astroid.nodes.Attribute):
            chain.append(curr.attrname)
            curr = curr.expr

        if len(chain) >= 2:
            # 1. Check if terminal method is allowed
            terminal_method = chain[0]
            if terminal_method in self.ALLOWED_TERMINAL_METHODS:
                return False

            # 2. Relax Demeter for 'self' access (allow self.friend.method())
            if isinstance(curr, astroid.nodes.Name) and curr.name in ("self", "cls"):
                if len(chain) == 2:
                    return False

            # 3. Exempt Safe Roots and Safe Types
            config_loader = ConfigurationLoader()
            safe_roots = config_loader.allowed_lod_roots
            safe_types = {"str", "int", "list", "dict", "set"}

            # Check if root is a Name (variable/module)
            if isinstance(curr, astroid.nodes.Name):
                if curr.name in safe_roots or curr.name in safe_types:
                    return False

            # 4. Entity/DTO Exemption via Inference (simplified)
            if self._is_allowed_by_inference(curr, config_loader):
                return False

            full_chain = ".".join(reversed(chain))
            self.add_message("clean-arch-demeter", node=node, args=(full_chain,))
            return True
        return False

    def _is_allowed_by_inference(self, node, config_loader):
        """Check if inferred type is allowed (e.g. Domain Entity)."""
        try:
            for inferred in node.infer():
                if inferred is astroid.Uninferable:
                    continue
                definition_root = inferred.root()
                if hasattr(definition_root, "name"):
                    module_name = definition_root.name
                    layer = config_loader.get_layer_for_module(module_name)
                    if layer and ("domain" in layer.lower() or "dto" in layer.lower()):
                        return True
        except astroid.InferenceError:
            pass
        return False
