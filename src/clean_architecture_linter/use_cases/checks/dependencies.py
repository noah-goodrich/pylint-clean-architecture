"""Dependency checks (W9001)."""

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
from clean_architecture_linter.domain.rules.dependency_layer import LayerDependencyRule


class DependencyChecker(BaseChecker):
    """W9001: Strict Layer Dependency enforcement. Thin: delegates to LayerDependencyRule."""

    name: str = "clean-arch-dependency"
    CODES = ["W9001"]

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
        self._dependency_rule = LayerDependencyRule(
            python_gateway=self._python_gateway,
            config_loader=self.config_loader,
        )

    def visit_import(self, node: astroid.nodes.Import) -> None:
        """Delegate W9001 to domain rule; report each violation via add_message."""
        for v in self._dependency_rule.check(node):
            self.add_message(
                v.code,
                node=v.node,
                args=v.message_args or (),
            )

    def visit_importfrom(self, node: astroid.nodes.ImportFrom) -> None:
        """Delegate W9001 to domain rule; report each violation via add_message."""
        for v in self._dependency_rule.check(node):
            self.add_message(
                v.code,
                node=v.node,
                args=v.message_args or (),
            )
