"""Test coupling checks (W9101, W9102)."""

from collections.abc import Mapping
from typing import TYPE_CHECKING

import astroid

if TYPE_CHECKING:
    from pylint.lint import PyLinter

from pylint.checkers import BaseChecker

from excelsior_architect.domain.registry_types import RuleRegistryEntry
from excelsior_architect.domain.rule_msgs import RuleMsgBuilder
from excelsior_architect.domain.rules import StatefulRule
from excelsior_architect.domain.rules.testing_coupling import TestingCouplingRule


class CleanArchTestingChecker(BaseChecker):
    """W9101, W9102: Test coupling. Thin: delegates to StatefulRule; checker holds state."""

    name: str = "clean-arch-testing"
    CODES = ["W9101", "W9102"]

    def __init__(
        self, linter: "PyLinter", registry: Mapping[str, RuleRegistryEntry]
    ) -> None:
        self.msgs = RuleMsgBuilder.build_msgs_for_codes(
            registry, self.CODES)  # type: ignore[assignment]
        super().__init__(linter)
        self._testing_rule: StatefulRule = TestingCouplingRule()
        self._current_function: astroid.nodes.FunctionDef | None = None
        self._mock_count: int = 0

    def visit_functiondef(self, node: astroid.nodes.FunctionDef) -> None:
        """Track function entry; state lives in checker."""
        tracked = self._testing_rule.record_functiondef(node)
        self._current_function = tracked
        if tracked is not None:
            self._mock_count = 0

    def leave_functiondef(self, node: astroid.nodes.FunctionDef) -> None:
        """Emit W9101 if mock count exceeded; report each violation."""
        for v in self._testing_rule.leave_functiondef(
            self._current_function, self._mock_count
        ):
            self.add_message(
                v.code,
                node=v.node,
                args=v.message_args or (),
            )
        self._current_function = None

    def visit_call(self, node: astroid.nodes.Call) -> None:
        """Delegate W9102 to domain rule; report each violation."""
        if self._testing_rule.record_mock_only(node, self._current_function):
            self._mock_count += 1
        for v in self._testing_rule.record_call(node, self._current_function):
            self.add_message(
                v.code,
                node=v.node,
                args=v.message_args or (),
            )

    # Test compatibility: tests assert on checker state.
    def _count_mocks(self, node: astroid.nodes.Call) -> None:
        """Test compatibility: increment mock count only."""
        if self._testing_rule.record_mock_only(node, self._current_function):
            self._mock_count += 1

    def _check_private_method_call(self, node: astroid.nodes.Call, call_name: str) -> None:
        """Test compatibility: check W9102 and add_message."""
        for v in self._testing_rule.check_private_method(
            node, call_name, self._current_function
        ):
            self.add_message(v.code, node=v.node, args=v.message_args or ())
