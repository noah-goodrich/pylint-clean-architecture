"""Interface Segregation rule (W9033): protocols with too many methods."""

from typing import ClassVar

import astroid

from excelsior_architect.domain.rules import Checkable, Violation


class InterfaceSegregationRule(Checkable):
    """Rule for W9033: Protocol with more than N methods suggests ISP violation; split into focused sub-protocols."""

    code: str = "W9033"
    description: str = "Interface Segregation: protocol has too many methods; consider splitting."
    fix_type: str = "code"

    DEFAULT_METHOD_LIMIT: ClassVar[int] = 7

    def __init__(self, method_limit: int | None = None) -> None:
        self._method_limit = method_limit if method_limit is not None else self.DEFAULT_METHOD_LIMIT

    def check(self, node: astroid.nodes.NodeNG) -> list[Violation]:
        """Check a ClassDef that is a Protocol for method count. Returns violation if over limit."""
        if not hasattr(node, "bases") or not hasattr(node, "name"):
            return []
        class_node = node
        if not self._is_protocol(class_node):
            return []
        method_count = self._count_protocol_methods(class_node)
        if method_count <= self._method_limit:
            return []
        name = getattr(class_node, "name", "?")
        return [
            Violation.from_node(
                code=self.code,
                message=f"Protocol '{name}' has {method_count} methods (limit {self._method_limit}). Consider splitting into focused sub-protocols.",
                node=node,
                message_args=(name, str(method_count),
                              str(self._method_limit)),
            )
        ]

    def _is_protocol(self, class_node: astroid.nodes.NodeNG) -> bool:
        """True if this class is a typing.Protocol (or has Protocol in bases)."""
        if not hasattr(class_node, "bases"):
            return False
        for base in class_node.bases:
            if isinstance(base, astroid.nodes.Name):
                if getattr(base, "name", "") == "Protocol":
                    return True
            if isinstance(base, astroid.nodes.Attribute):
                if getattr(base, "attrname", "") == "Protocol":
                    return True
        try:
            for ancestor in class_node.ancestors():
                if hasattr(ancestor, "name") and getattr(ancestor, "name", "") == "Protocol":
                    return True
                qname = getattr(ancestor, "qname", lambda: "")()
                if qname and "Protocol" in qname:
                    return True
        except astroid.InferenceError:
            pass
        return False

    def _count_protocol_methods(self, class_node: astroid.nodes.NodeNG) -> int:
        """Count method definitions (excluding dunder except __init_subclass__, __protocol_attrs__)."""
        if not hasattr(class_node, "body"):
            return 0
        count = 0
        for stmt in class_node.body:
            if isinstance(stmt, astroid.nodes.FunctionDef):
                name = getattr(stmt, "name", "")
                if name.startswith("__") and name.endswith("__") and name not in (
                    "__init_subclass__",
                    "__protocol_attrs__",
                ):
                    continue
                count += 1
        return count
