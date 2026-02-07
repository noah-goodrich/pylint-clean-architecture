"""Design quality checks (W9032, W9033, W9034, W9035)."""

from collections.abc import Mapping
from typing import TYPE_CHECKING

import astroid
from pylint.checkers import BaseChecker

if TYPE_CHECKING:
    from pylint.lint import PyLinter

from excelsior_architect.domain.config import ConfigurationLoader
from excelsior_architect.domain.registry_types import RuleRegistryEntry
from excelsior_architect.domain.rule_msgs import RuleMsgBuilder
from excelsior_architect.domain.rules.complexity_rule import MethodComplexityRule
from excelsior_architect.domain.rules.constructor_injection import ConstructorInjectionRule
from excelsior_architect.domain.rules.exception_hygiene import ExceptionHygieneRule
from excelsior_architect.domain.rules.interface_segregation import InterfaceSegregationRule


class DesignQualityChecker(BaseChecker):
    """W9032 (Method Complexity), W9033 (Interface Segregation), W9034 (Constructor Injection), W9035 (Exception Hygiene)."""

    name: str = "clean-arch-design-quality"
    CODES = ["W9032", "W9033", "W9034", "W9035"]

    def __init__(
        self,
        linter: "PyLinter",
        config_loader: ConfigurationLoader,
        registry: Mapping[str, RuleRegistryEntry],
    ) -> None:
        self.msgs = RuleMsgBuilder.build_msgs_for_codes(
            registry, self.CODES)  # type: ignore[assignment]
        super().__init__(linter)
        self.config_loader = config_loader
        self._complexity_rule = MethodComplexityRule()
        self._interface_rule = InterfaceSegregationRule()
        self._constructor_rule = ConstructorInjectionRule(
            config_loader=config_loader)
        self._exception_rule = ExceptionHygieneRule()

    def visit_functiondef(self, node: astroid.nodes.FunctionDef) -> None:
        for v in self._complexity_rule.check(node):
            self.add_message(v.code, node=v.node, args=v.message_args or ())
        for v in self._constructor_rule.check(node):
            self.add_message(v.code, node=v.node, args=v.message_args or ())

    def visit_classdef(self, node: astroid.nodes.ClassDef) -> None:
        for v in self._interface_rule.check(node):
            self.add_message(v.code, node=v.node, args=v.message_args or ())

    def visit_try(self, node: astroid.nodes.NodeNG) -> None:
        handlers = getattr(node, "handlers", []) or []
        for handler in handlers:
            for v in self._exception_rule.check(handler):
                self.add_message(v.code, node=v.node,
                                 args=v.message_args or ())
