"""Architectural entropy rule (W9030)."""

from collections import defaultdict

import astroid

from excelsior_architect.domain.rules import Checkable, Violation


class EntropyRule(Checkable):
    """
    Rule for W9030: Architectural entropy - same identifier in multiple places.
    Stateful: holds _entropy_map and _emitted across modules.
    """

    code: str = "W9030"
    description: str = "Architectural entropy: same identifier in multiple places."
    fix_type: str = "code"

    def __init__(self) -> None:
        self._entropy_map: defaultdict[str,
                                       list[tuple[str, int]]] = defaultdict(list)
        self._emitted: set[str] = set()

    def check(self, node: astroid.nodes.NodeNG) -> list[Violation]:
        """Process a module node; return new violations."""
        violations: list[Violation] = []
        if not hasattr(node, "nodes_of_class"):
            return violations
        current_file = getattr(node, "file", "") or ""
        if not current_file:
            return violations
        try:
            for const in node.nodes_of_class(astroid.nodes.Const):
                val = getattr(const, "value", None)
                if not isinstance(val, str):
                    continue
                if not self._is_definition_context(const):
                    continue
                line = getattr(const, "lineno", 0) or 0
                self._entropy_map[val].append((current_file, line))
                if val in self._emitted:
                    continue
                files_seen = {fp for fp, _ in self._entropy_map[val]}
                if len(files_seen) < 2:
                    continue
                self._emitted.add(val)
                file_list_str = ", ".join(sorted(files_seen))
                violations.append(
                    Violation.from_node(
                        code=self.code,
                        message=f"Scatter: {val} in {len(files_seen)} files.",
                        node=const,
                        message_args=(val, str(len(files_seen)),
                                      file_list_str),
                    )
                )
        except Exception:
            pass
        return violations

    def _is_definition_context(self, node: astroid.nodes.NodeNG) -> bool:
        parent = getattr(node, "parent", None)
        if not parent:
            return False
        if hasattr(parent, "elts") and node in getattr(parent, "elts", []):
            return True
        if hasattr(parent, "items"):
            for key, _ in getattr(parent, "items", []):
                if key is node:
                    return True
        if hasattr(parent, "elts") and node in getattr(parent, "elts", []):
            grandparent = getattr(parent, "parent", None)
            if grandparent and hasattr(grandparent, "items"):
                return True
        return False
