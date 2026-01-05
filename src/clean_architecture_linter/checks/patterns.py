"""Pattern checks (W9005, W9006)."""

import astroid  # type: ignore[import-untyped]
from pylint.checkers import BaseChecker


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
        # Skip 'if __name__ == "__main__"' blocks
        if isinstance(node.test, astroid.nodes.Compare):
            if isinstance(node.test.left, astroid.nodes.Name) and node.test.left.name == "__name__":
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
                # We found the final else: do_z()
                # If depth is 0, we have if/else (2 branches). This might be fine, but let's say >= 2 is a chain?
                # Actually, the user complained about simple checks.
                # Let's require depth >= 1 (so 3 branches: if/elif/else or if/elif/elif)
                # OR if depth is 0, arguably if/else is simple enough.
                # Let's be conservative: require at least one 'elif' (depth > 0) to call it a "chain"
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
        "replace",
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
        "update",
    }

    def visit_call(self, node):
        if not isinstance(node.func, astroid.nodes.Attribute):
            return

        chain = []
        curr = node.func
        while isinstance(curr, astroid.nodes.Attribute):
            chain.append(curr.attrname)
            curr = curr.expr

        if len(chain) >= 2:
            # 1. Check if terminal method is allowed
            terminal_method = chain[0]
            if terminal_method in self.ALLOWED_TERMINAL_METHODS:
                return

            # 2. Relax Demeter for 'self' access (allow self.friend.method())
            if isinstance(curr, astroid.nodes.Name) and curr.name in ("self", "cls"):
                if len(chain) == 2:
                    return

            full_chain = ".".join(reversed(chain))
            self.add_message("clean-arch-demeter", node=node, args=(full_chain,))
