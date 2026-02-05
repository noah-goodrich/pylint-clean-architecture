"""Dependency Injection checks (W9301)."""

from collections.abc import Mapping
from typing import TYPE_CHECKING

import astroid  # type: ignore[import-untyped]

if TYPE_CHECKING:
    from pylint.lint import PyLinter

from pylint.checkers import BaseChecker

from clean_architecture_linter.domain.config import ConfigurationLoader
from clean_architecture_linter.domain.protocols import AstroidProtocol, PythonProtocol
from clean_architecture_linter.domain.registry_types import RuleRegistryEntry
from clean_architecture_linter.domain.rule_msgs import RuleMsgBuilder
from clean_architecture_linter.domain.rules.di import DIRule


class DIChecker(BaseChecker):
    """W9301: Dependency Injection enforcement. Thin: delegates to DIRule."""

    name: str = "clean-arch-di"
    CODES = ["W9301"]

    def __init__(
        self,
        linter: "PyLinter",
        ast_gateway: AstroidProtocol,
        python_gateway: PythonProtocol,
        config_loader: ConfigurationLoader,
        registry: Mapping[str, RuleRegistryEntry],
    ) -> None:
        self.msgs = RuleMsgBuilder.build_msgs_for_codes(
            registry, self.CODES)
        super().__init__(linter)
        self.config_loader = config_loader
        self._python_gateway = python_gateway
        self._ast_gateway = ast_gateway
        self._di_rule = DIRule(
            python_gateway=self._python_gateway,
            ast_gateway=self._ast_gateway,
            config_loader=self.config_loader,
        )

    def visit_call(self, node: astroid.nodes.Call) -> None:
        """Delegate W9301 to domain rule."""
        for v in self._di_rule.check(node):
            self.add_message(
                v.code,
                node=v.node,
                args=v.message_args or (),
            )
