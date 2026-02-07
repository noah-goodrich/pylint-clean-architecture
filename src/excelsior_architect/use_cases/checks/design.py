"""Design checks (W9007, W9009, W9012, W9013, W9015, W9016)."""

from collections.abc import Mapping
from typing import TYPE_CHECKING

import astroid
from pylint.checkers import BaseChecker

if TYPE_CHECKING:
    from pylint.lint import PyLinter

from excelsior_architect.domain.config import ConfigurationLoader
from excelsior_architect.domain.protocols import AstroidProtocol
from excelsior_architect.domain.registry_types import RuleRegistryEntry
from excelsior_architect.domain.rule_msgs import RuleMsgBuilder
from excelsior_architect.domain.rules.design_rules import DesignRule


class DesignChecker(BaseChecker):
    """Design pattern enforcement. Thin: delegates to DesignRule."""

    name: str = "clean-arch-design"
    CODES = ["W9012", "W9007", "W9009", "W9013", "W9015", "W9016"]

    def __init__(
        self,
        linter: "PyLinter",
        ast_gateway: AstroidProtocol,
        config_loader: ConfigurationLoader,
        registry: Mapping[str, RuleRegistryEntry],
    ) -> None:
        self.msgs = RuleMsgBuilder.build_msgs_for_codes(
            registry, self.CODES)  # type: ignore[assignment]
        super().__init__(linter)
        self.config_loader = config_loader
        self._design_rule = DesignRule(
            config_loader=self.config_loader,
            ast_gateway=ast_gateway,
        )

    @property
    def raw_types(self) -> set[str]:
        """Shim for tests. Delegates to rule."""
        return self._design_rule.raw_types

    @property
    def infrastructure_modules(self) -> set[str]:
        """Shim for tests. Delegates to rule."""
        return self._design_rule.infrastructure_modules

    def visit_return(self, node: astroid.nodes.Return) -> None:
        for v in self._design_rule.check_return(node):
            self.add_message(
                v.code,
                node=v.node,
                args=v.message_args or (),
            )

    def visit_assign(self, node: astroid.nodes.Assign) -> None:
        for v in self._design_rule.check_assign(node):
            self.add_message(
                v.code,
                node=v.node,
                args=v.message_args or (),
            )

    def visit_functiondef(self, node: astroid.nodes.FunctionDef) -> None:
        for v in self._design_rule.check_functiondef(node):
            self.add_message(
                v.code,
                node=v.node,
                args=v.message_args or (),
            )

    def visit_if(self, node: astroid.nodes.If) -> None:
        for v in self._design_rule.check_if(node):
            self.add_message(
                v.code,
                node=v.node,
                args=v.message_args or (),
            )
