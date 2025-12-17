import ast
from pylint.checkers import BaseChecker
from clean_architecture_linter.config import ConfigurationLoader

class VisibilityChecker(BaseChecker):
    name = 'clean-architecture-visibility'
    msgs = {
        'W9003': (
            'Access to protected member "%s" detected outside of its defining scope.',
            'protected-member-access',
            'Used when a protected member (starting with _) is accessed from outside its module or class.'
        ),
    }

    def __init__(self, linter=None):
        super().__init__(linter)
        self.config_loader = ConfigurationLoader()

    def visit_attribute(self, node: ast.Attribute):
        try:
            if not self.config_loader.visibility_enforcement:
                return

            if node.attrname.startswith('_') and not node.attrname.startswith('__'):
                # It's a protected member

                # Simple heuristic: AST structure
                # node.expr is the object being accessed
                is_self_access = False
                # astroid Name node has 'name' attribute
                if hasattr(node.expr, 'name') and node.expr.name in ('self', 'cls'):
                    is_self_access = True

                # If it's not self/cls access, we flag it.
                if not is_self_access:
                        self.add_message('protected-member-access', node=node, args=(node.attrname,))
        except Exception:
            import traceback
            traceback.print_exc()
