import ast
import astroid
from pylint.checkers import BaseChecker

class DelegationChecker(BaseChecker):
    name = 'clean-architecture-delegation'
    msgs = {
        'W9005': (
            'Delegation Anti-Pattern: Conditional logic only delegates. Consider refactoring to Strategy, Handler, or Adapter pattern.',
            'delegation-anti-pattern',
            'Used when an if/elif/else block contains branches that only return a function call.'
        ),
    }

    def visit_if(self, node):
        try:
            # We want to check for patterns like:
            # if x: return foo()
            # elif y: return bar()
            # else: return baz()

            # This requires checking the body of the if, and the orelse (which might be another if)

            # Heuristic:
            # 1. Collect all branches of the if/elif chain.
            # 2. Check each branch body.
            # 3. If ALL branches are "simple delegation" (single return statement with a call, or just a single call statement), flag it.

            branches = []
            current = node
            while True:
                branches.append(current.body)
                if not current.orelse:
                    break
                if len(current.orelse) == 1 and isinstance(current.orelse[0], astroid.nodes.If):
                    current = current.orelse[0]
                else:
                    branches.append(current.orelse)
                    break

            # Now verify if every branch is a delegation
            if len(branches) < 2:
                # Single if without else is arguably not a "complex delegation logic" anti-pattern in the same way
                # (could just be a guard clause), so maybe we ignore purely single 'if's?
                # User example was if/elif. Let's stick to multiple branches for safety.
                return

            is_delegation = True
            for branch in branches:
                if not self._is_simple_delegation(branch):
                    is_delegation = False
                    break

            if is_delegation:
                self.add_message('delegation-anti-pattern', node=node)
        except Exception:
            import traceback
            traceback.print_exc()

    def _is_simple_delegation(self, body_stmts):
        """
        Check if a block of statements is just a return or a call.
        """
        # Allow docstrings? Pylint AST usually strips them or we ignore expressions that are strings?
        # Let's keep it strict: 1 meaningful statement.

        if len(body_stmts) != 1:
            return False

        stmt = body_stmts[0]

        # Case 1: return func()
        if isinstance(stmt, astroid.nodes.Return):
            if isinstance(stmt.value, astroid.nodes.Call):
                return True
            # return plain variable isn't really "delegation to logic", it's just return.
            return False

        # Case 2: func() (just a call)
        # In astroid, Expr node wraps the call? Or checking if stmt is Call?
        # astroid nodes often inherit from ast nodes, so isinstance(stmt, ast.Expr) might work.
        if isinstance(stmt, astroid.nodes.Expr) and isinstance(stmt.value, astroid.nodes.Call):
            return True
        # astroid 2.0+ might represent Call directly as statement? No, still Expr.

        return False
