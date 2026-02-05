"""Delegation anti-pattern rule (W9005)."""

from typing import Optional

import astroid  # type: ignore[import-untyped]

from clean_architecture_linter.domain.rules import Checkable, Violation


class DelegationRule(Checkable):
    """Rule for W9005: Delegation anti-pattern (if/elif chains that delegate)."""

    code: str = "W9005"
    description: str = "Delegation anti-pattern: refactor to Strategy/Handler/Adapter."
    fix_type: str = "code"

    def __init__(self) -> None:
        pass

    def check(self, node: astroid.nodes.NodeNG) -> list[Violation]:
        """Check an If node for W9005. Returns at most one violation."""
        if not hasattr(node, "body") or not hasattr(node, "orelse"):
            return []
        if self._is_main_block(node):
            return []
        is_delegation, advice = self._check_delegation_chain(node, 0)
        if not is_delegation:
            return []
        msg = advice or "Refactor to Strategy, Handler, or Adapter pattern."
        return [
            Violation.from_node(
                code=self.code,
                message=msg,
                node=node,
                message_args=(msg,),
            )
        ]

    def _is_main_block(self, node: astroid.nodes.NodeNG) -> bool:
        test = getattr(node, "test", None)
        if not test or not hasattr(test, "left"):
            return False
        left = getattr(test, "left", None)
        if left and getattr(left, "name", None) == "__name__":
            return True
        return False

    def _check_delegation_chain(self, node: astroid.nodes.NodeNG, depth: int) -> tuple[bool, Optional[str]]:
        body = getattr(node, "body", None)
        orelse = getattr(node, "orelse", None)
        if body is None or orelse is None:
            return False, None
        try:
            body_list = list(body) if body is not None else []
            orelse_list = list(orelse) if orelse is not None else []
        except (TypeError, ValueError):
            return False, None
        if len(body_list) != 1:
            return False, None
        stmt = body_list[0]
        if not self._is_delegation_call(stmt):
            return False, None
        advice = "Refactor to Strategy/Handler pattern."
        test = getattr(node, "test", None)
        if test and hasattr(test, "left") and getattr(getattr(test, "left", None), "name", None):
            advice = "Refactor to **Strategy Pattern** using a dictionary mapping."
        if not orelse_list:
            return depth > 0, advice
        if len(orelse_list) == 1:
            orelse_node = orelse_list[0]
            # Prefer single-statement branch (Return/Expr with Call) over recursing into nested If
            if self._is_delegation_call(orelse_node):
                return depth > 0, advice
            # Recurse only when orelse is another If (has body/orelse that are real sequences)
            if hasattr(orelse_node, "body") and hasattr(orelse_node, "orelse"):
                sub_body = getattr(orelse_node, "body", None)
                sub_orelse = getattr(orelse_node, "orelse", None)
                if isinstance(sub_body, list) and isinstance(sub_orelse, list):
                    return self._check_delegation_chain(orelse_node, depth + 1)
        return False, None

    def _is_delegation_call(self, node: astroid.nodes.NodeNG) -> bool:
        if node is None:
            return False
        val = getattr(node, "value", None)
        if val is None:
            return False
        return hasattr(val, "func")  # Call has .func
