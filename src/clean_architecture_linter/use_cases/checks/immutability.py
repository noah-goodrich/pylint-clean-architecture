"""Immutability checks (W9601)."""

from collections.abc import Mapping
from typing import TYPE_CHECKING

import astroid  # type: ignore[import-untyped]

if TYPE_CHECKING:
    from pylint.lint import PyLinter

from pylint.checkers import BaseChecker

from clean_architecture_linter.domain.config import ConfigurationLoader
from clean_architecture_linter.domain.protocols import PythonProtocol
from clean_architecture_linter.domain.registry_types import RuleRegistryEntry
from clean_architecture_linter.domain.rule_msgs import RuleMsgBuilder
from clean_architecture_linter.domain.rules.immutability import DomainImmutabilityRule


class ImmutabilityChecker(BaseChecker):
    """W9601: Domain Immutability enforcement. Thin: delegates to DomainImmutabilityRule."""

    name: str = "clean-arch-immutability"
    CODES = ["W9601"]

    def __init__(
        self,
        linter: "PyLinter",
        python_gateway: PythonProtocol,
        config_loader: ConfigurationLoader,
        registry: Mapping[str, RuleRegistryEntry],
    ) -> None:
        self.msgs = RuleMsgBuilder.build_msgs_for_codes(
            registry, self.CODES)
        super().__init__(linter)
        self.config_loader = config_loader
        self._python_gateway = python_gateway
        self._immutability_rule = DomainImmutabilityRule(
            python_gateway=self._python_gateway,
            config_loader=self.config_loader,
        )

    def visit_assignattr(self, node: astroid.nodes.AssignAttr) -> None:
        """Delegate W9601 to domain rule."""
        for v in self._immutability_rule.check_assignattr(node):
            self.add_message(
                v.code,
                node=v.node,
                args=v.message_args or (),
            )

    def visit_classdef(self, node: astroid.nodes.ClassDef) -> None:
        """Delegate W9601 to domain rule."""
        for v in self._immutability_rule.check_classdef(node):
            self.add_message(
                v.code,
                node=v.node,
                args=v.message_args or (),
            )

    # Test compatibility: tests assert on these; they delegate to the rule.
    def _is_dataclass_name(self, n: astroid.nodes.NodeNG) -> bool:
        return self._immutability_rule._is_dataclass_name(n)

    def _dataclass_frozen_from_decorators(
        self, decorators: list[astroid.nodes.NodeNG]
    ) -> tuple[bool, bool]:
        return self._immutability_rule._dataclass_frozen_from_decorators(decorators)
