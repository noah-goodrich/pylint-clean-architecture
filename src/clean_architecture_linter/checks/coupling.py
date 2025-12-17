import ast
import astroid
from pylint.checkers import BaseChecker

class DemeterChecker(BaseChecker):
    name = 'clean-architecture-coupling'
    msgs = {
        'W9006': (
            'Law of Demeter Violation: Object chain access detected (%s). Access should not exceed one level of indirection.',
            'law-of-demeter-violation',
            'Used when property access chain is too deep (e.g. obj.attr.method()).'
        ),
    }

    def visit_call(self, node):
        try:
            # We check the function expression being called.
            # e.g. a.b.c() -> node.func is Attribute(value=Attribute(value=Name(a), attr=b), attr=c)

            if not isinstance(node.func, astroid.nodes.Attribute):
                return

            # We need to count the depth of Attribute nodes in the chain.
            # node.func is depth 0 (the method itself)
            # a.b.c()
            # c is attr of (a.b)
            # b is attr of (a)

            chain = []
            curr = node.func

            # Unwind the attribute chain
            while isinstance(curr, astroid.nodes.Attribute):
                chain.append(curr.attrname)
                curr = curr.expr

            # Now curr is the base object (Name, Call, etc.)
            # chain is [c, b] for a.b.c()

            # If chain length is >= 2, we *might* have a violation.
            # chain length 1: a.b() -> [b]. Safe.
            # chain length 2: a.b.c() -> [c, b]. Unsafe.

            if len(chain) >= 2:
                # Reconstruct string for message
                full_chain = ".".join(reversed(chain))
                self.add_message('law-of-demeter-violation', node=node, args=(full_chain,))
        except Exception:
            import traceback
            traceback.print_exc()

