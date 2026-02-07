"""Design pattern suggestion checks (W9041–W9045). INFO-level suggestions."""

from collections.abc import Mapping
from typing import TYPE_CHECKING

import astroid
from pylint.checkers import BaseChecker

if TYPE_CHECKING:
    from pylint.lint import PyLinter

from excelsior_architect.domain.registry_types import RuleRegistryEntry
from excelsior_architect.domain.rule_msgs import RuleMsgBuilder
from excelsior_architect.domain.rules.pattern_suggestions import (
    BuilderSuggestionRule,
    FacadeSuggestionRule,
    FactorySuggestionRule,
    StateSuggestionRule,
    StrategySuggestionRule,
)


class PatternSuggestionChecker(BaseChecker):
    """W9041–W9045: Builder, Factory, Strategy, State, Facade suggestions (INFO-level)."""

    name: str = "clean-arch-pattern-suggestions"
    CODES = ["W9041", "W9042", "W9043", "W9044", "W9045"]

    def __init__(
        self,
        linter: "PyLinter",
        registry: Mapping[str, RuleRegistryEntry],
    ) -> None:
        self.msgs = RuleMsgBuilder.build_msgs_for_codes(
            registry, self.CODES)  # type: ignore[assignment]
        super().__init__(linter)
        self._builder_rule = BuilderSuggestionRule()
        self._factory_rule = FactorySuggestionRule()
        self._strategy_rule = StrategySuggestionRule()
        self._state_rule = StateSuggestionRule()
        self._facade_rule = FacadeSuggestionRule()

    def visit_functiondef(self, node: astroid.nodes.FunctionDef) -> None:
        for v in self._builder_rule.check(node):
            self.add_message(v.code, node=v.node, args=v.message_args or ())
        for v in self._facade_rule.check(node):
            self.add_message(v.code, node=v.node, args=v.message_args or ())

    def visit_if(self, node: astroid.nodes.If) -> None:
        for v in self._factory_rule.check(node):
            self.add_message(v.code, node=v.node, args=v.message_args or ())
        for v in self._strategy_rule.check(node):
            self.add_message(v.code, node=v.node, args=v.message_args or ())

    def visit_classdef(self, node: astroid.nodes.ClassDef) -> None:
        for v in self._state_rule.check(node):
            self.add_message(v.code, node=v.node, args=v.message_args or ())
