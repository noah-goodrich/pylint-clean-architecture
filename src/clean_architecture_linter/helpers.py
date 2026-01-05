"""AST Helper utilities for linter checkers."""

import astroid  # type: ignore[import-untyped]


def get_call_name(node):
    """Extract the name of the function or method being called from a Call node."""
    if not isinstance(node, astroid.nodes.Call):
        return None

    if isinstance(node.func, astroid.nodes.Name):
        return node.func.name
    if isinstance(node.func, astroid.nodes.Attribute):
        return node.func.attrname
    return None
