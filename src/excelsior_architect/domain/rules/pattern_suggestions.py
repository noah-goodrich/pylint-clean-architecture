"""Design pattern suggestion rules (W9041–W9045): INFO-level suggestions, not violations."""

from __future__ import annotations

from typing import ClassVar

import astroid

from excelsior_architect.domain.rules import Checkable, Violation


class BuilderSuggestionRule(Checkable):
    """W9041: __init__ with 6+ parameters suggests Builder pattern."""

    code: str = "W9041"
    description: str = "Consider Builder: __init__ has many parameters."
    fix_type: str = "code"
    PARAM_THRESHOLD: ClassVar[int] = 6

    def check(self, node: astroid.nodes.NodeNG) -> list[Violation]:
        if not isinstance(node, astroid.nodes.FunctionDef) or getattr(node, "name", "") != "__init__":
            return []
        args = getattr(node, "args", None)
        if not args:
            return []
        n = len(getattr(args, "args", []))
        if getattr(node, "is_method", lambda: False)():
            n -= 1  # exclude self
        if n < self.PARAM_THRESHOLD:
            return []
        parent = getattr(node, "parent", None)
        class_name = getattr(parent, "name", "?") if isinstance(
            parent, astroid.nodes.ClassDef) else "?"
        return [
            Violation.from_node(
                code=self.code,
                message=f"__init__ of '{class_name}' has {n} parameters; consider Builder pattern.",
                node=node,
                message_args=(class_name, str(n)),
            )
        ]


class FactorySuggestionRule(Checkable):
    """W9042: if/elif chains instantiating different classes suggest Factory."""

    code: str = "W9042"
    description: str = "Consider Factory: if/elif instantiating different classes."
    fix_type: str = "code"

    def check(self, node: astroid.nodes.NodeNG) -> list[Violation]:
        if not isinstance(node, astroid.nodes.If):
            return []
        classes_in_branches = self._collect_instantiations(node)
        if len(classes_in_branches) < 2:
            return []
        classes_str = ", ".join(sorted(classes_in_branches))
        return [
            Violation.from_node(
                code=self.code,
                message=f"if/elif instantiating different classes ({classes_str}); consider Factory.",
                node=node,
                message_args=(classes_str,),
            )
        ]

    def _collect_instantiations(self, if_node: astroid.nodes.If) -> set[str]:
        """Collect class names from Call nodes (constructors) in this if and its elif chain."""
        seen: set[str] = set()
        current: astroid.nodes.If | None = if_node
        while current:
            for call in current.nodes_of_class(astroid.nodes.Call):
                name = self._call_class_name(call)
                if name:
                    seen.add(name)
            orelse = getattr(current, "orelse", []) or []
            if len(orelse) == 1 and isinstance(orelse[0], astroid.nodes.If):
                current = orelse[0]
            else:
                current = None
        return seen

    def _call_class_name(self, call: astroid.nodes.Call) -> str | None:
        func = getattr(call, "func", None)
        if isinstance(func, astroid.nodes.Name):
            return getattr(func, "name", None)
        if isinstance(func, astroid.nodes.Attribute):
            return getattr(func, "attrname", None)
        return None


class StrategySuggestionRule(Checkable):
    """W9043: if/elif selecting different algorithms for same operation suggests Strategy."""

    code: str = "W9043"
    description: str = "Consider Strategy: if/elif selecting different algorithms."
    fix_type: str = "code"

    def check(self, node: astroid.nodes.NodeNG) -> list[Violation]:
        if not isinstance(node, astroid.nodes.If):
            return []
        branches = self._count_elif_branches(node)
        if branches < 2:
            return []
        return [
            Violation.from_node(
                code=self.code,
                message=f"if/elif chain with {branches + 1} branches selecting behavior; consider Strategy pattern.",
                node=node,
                message_args=(str(branches + 1),),
            )
        ]

    def _count_elif_branches(self, if_node: astroid.nodes.If) -> int:
        count = 0
        current: astroid.nodes.If | None = if_node
        while current:
            count += 1
            orelse = getattr(current, "orelse", []) or []
            if len(orelse) == 1 and isinstance(orelse[0], astroid.nodes.If):
                current = orelse[0]
            else:
                break
        return max(0, count - 1)


class StateSuggestionRule(Checkable):
    """W9044: Repeated conditionals on same state/status attribute across methods suggest State pattern."""

    code: str = "W9044"
    description: str = "Consider State: repeated conditionals on same state attribute."
    fix_type: str = "code"

    def check(self, node: astroid.nodes.NodeNG) -> list[Violation]:
        """Emit once per class: if the class has 3+ methods that branch on the same self.attr."""
        if not isinstance(node, astroid.nodes.ClassDef):
            return []
        state_attrs = self._state_attrs_used_in_conditionals(node)
        for attr, count in state_attrs.items():
            if count >= 3:
                return [
                    Violation.from_node(
                        code=self.code,
                        message=f"Repeated conditionals on '{attr}' in {count} methods; consider State pattern.",
                        node=node,
                        message_args=(attr, str(count)),
                    )
                ]
        return []

    def _state_attrs_used_in_conditionals(self, class_node: astroid.nodes.ClassDef) -> dict[str, int]:
        """Count how many methods use self.attr in If test (one count per method per attr)."""
        # attr -> set of method names that branch on this attr
        methods_per_attr: dict[str, set[str]] = {}
        for stmt in getattr(class_node, "body", []) or []:
            if not isinstance(stmt, astroid.nodes.FunctionDef):
                continue
            method_name = getattr(stmt, "name", "")
            attrs_in_method: set[str] = set()
            for if_node in stmt.nodes_of_class(astroid.nodes.If):
                attr = self._attr_in_compare(if_node.test)
                if attr:
                    attrs_in_method.add(attr)
            for attr in attrs_in_method:
                methods_per_attr.setdefault(attr, set()).add(method_name)
        return {attr: len(methods) for attr, methods in methods_per_attr.items()}

    def _attr_in_compare(self, test: astroid.nodes.NodeNG | None) -> str | None:
        if test is None:
            return None
        if isinstance(test, astroid.nodes.Compare) and getattr(test, "ops", None):
            left = test.left
            if isinstance(left, astroid.nodes.Attribute):
                if isinstance(getattr(left, "expr", None), astroid.nodes.Name):
                    if getattr(left.expr, "name", "") == "self":
                        return getattr(left, "attrname", None)
        if isinstance(test, astroid.nodes.BoolOp):
            for v in getattr(test, "values", []) or []:
                a = self._attr_in_compare(v)
                if a:
                    return a
        return None


class FacadeSuggestionRule(Checkable):
    """W9045: Method calling 5+ distinct dependency objects suggests Facade."""

    code: str = "W9045"
    description: str = "Consider Facade: method calls many distinct dependencies."
    fix_type: str = "code"
    DEPENDENCY_THRESHOLD: ClassVar[int] = 5

    def check(self, node: astroid.nodes.NodeNG) -> list[Violation]:
        if not isinstance(node, astroid.nodes.FunctionDef):
            return []
        distinct = self._distinct_attr_calls(node)
        if distinct < self.DEPENDENCY_THRESHOLD:
            return []
        name = getattr(node, "name", "?")
        return [
            Violation.from_node(
                code=self.code,
                message=f"Method '{name}' calls {distinct} distinct dependency objects; consider Facade.",
                node=node,
                message_args=(name, str(distinct)),
            )
        ]

    def _distinct_attr_calls(self, func: astroid.nodes.FunctionDef) -> int:
        """Count distinct self.attr used as receiver of a call (e.g. self.x.foo(), self.y.bar())."""
        attrs: set[str] = set()
        for call in func.nodes_of_class(astroid.nodes.Call):
            func_part = getattr(call, "func", None)
            if isinstance(func_part, astroid.nodes.Attribute):
                expr = getattr(func_part, "expr", None)
                if isinstance(expr, astroid.nodes.Attribute):
                    if getattr(expr.expr, "name", "") == "self":
                        attrs.add(getattr(expr, "attrname", ""))
                elif isinstance(expr, astroid.nodes.Name):
                    if getattr(expr, "name", "") == "self":
                        attrs.add(getattr(func_part, "attrname", ""))
        return len(attrs)
