"""Contract Integrity checks (W9201, W9202)."""

from collections.abc import Mapping
from typing import TYPE_CHECKING

import astroid

if TYPE_CHECKING:
    from pylint.lint import PyLinter

from pylint.checkers import BaseChecker

from excelsior_architect.domain.config import ConfigurationLoader
from excelsior_architect.domain.protocols import PythonProtocol
from excelsior_architect.domain.registry_types import RuleRegistryEntry
from excelsior_architect.domain.rule_msgs import RuleMsgBuilder
from excelsior_architect.domain.rules.contract_integrity import (
    ConcreteMethodStubRule,
    ContractIntegrityRule,
)


class ContractChecker(BaseChecker):
    """W9201: Contract Integrity (Domain Interface) enforcement. Thin: delegates to ContractIntegrityRule."""

    name: str = "clean-arch-contracts"
    CODES = ["W9201", "W9202"]

    def __init__(
        self,
        linter: "PyLinter",
        python_gateway: PythonProtocol,
        config_loader: ConfigurationLoader,
        registry: Mapping[str, RuleRegistryEntry],
    ) -> None:
        self.msgs = RuleMsgBuilder.build_msgs_for_codes(
            registry, self.CODES)  # type: ignore[assignment]
        super().__init__(linter)
        self._config_loader = config_loader
        self.config_loader = config_loader
        self._python_gateway = python_gateway
        self._contract_rule = ContractIntegrityRule(
            python_gateway=self._python_gateway,
            config_loader=self._config_loader,
        )
        self._concrete_stub_rule = ConcreteMethodStubRule(
            python_gateway=self._python_gateway,
            config_loader=self._config_loader,
        )

    def visit_classdef(self, node: astroid.nodes.ClassDef) -> None:
        """Delegate W9201 to domain rule; report each violation via add_message."""
        for v in self._contract_rule.check(node):
            self.add_message(
                v.code,
                node=v.node,
                args=v.message_args or (),
            )

    def visit_functiondef(self, node: astroid.nodes.FunctionDef) -> None:
        """Delegate W9202 to domain rule; report each violation via add_message."""
        for v in self._concrete_stub_rule.check(node):
            self.add_message(
                v.code,
                node=v.node,
                args=v.message_args or (),
            )
