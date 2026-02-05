"""Layer boundary checks (W9003, W9004)."""

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
from clean_architecture_linter.domain.rules.boundary_rules import ResourceRule, VisibilityRule


class VisibilityChecker(BaseChecker):
    """W9003: Protected member access across layers. Thin: delegates to VisibilityRule."""

    name: str = "clean-arch-visibility"
    CODES = ["W9003"]

    def __init__(
        self,
        linter: "PyLinter",
        config_loader: ConfigurationLoader,
        registry: Mapping[str, RuleRegistryEntry],
    ) -> None:
        self.msgs = RuleMsgBuilder.build_msgs_for_codes(registry, self.CODES)
        super().__init__(linter)
        self.config_loader = config_loader
        self._visibility_rule = VisibilityRule(
            config_loader=self.config_loader)

    def visit_attribute(self, node: astroid.nodes.Attribute) -> None:
        """Delegate W9003 to domain rule; report each violation via add_message."""
        for v in self._visibility_rule.check(node):
            self.add_message(
                v.code,
                node=v.node,
                args=v.message_args or (),
            )


class ResourceChecker(BaseChecker):
    """W9004: Forbidden I/O access in UseCase/Domain layers. Thin: delegates to ResourceRule."""

    name: str = "clean-arch-resources"
    CODES = ["W9004"]

    def __init__(
        self,
        linter: "PyLinter",
        python_gateway: PythonProtocol,
        config_loader: ConfigurationLoader,
        registry: Mapping[str, RuleRegistryEntry],
    ) -> None:
        self.msgs = RuleMsgBuilder.build_msgs_for_codes(registry, self.CODES)
        super().__init__(linter)
        self.config_loader = config_loader
        self._python_gateway = python_gateway
        self._resource_rule = ResourceRule(
            python_gateway=self._python_gateway,
            config_loader=self.config_loader,
        )

    def visit_import(self, node: astroid.nodes.Import) -> None:
        """Delegate W9004 to domain rule."""
        for v in self._resource_rule.check(node):
            self.add_message(
                v.code,
                node=v.node,
                args=v.message_args or (),
            )

    def visit_importfrom(self, node: astroid.nodes.ImportFrom) -> None:
        """Delegate W9004 to domain rule."""
        for v in self._resource_rule.check(node):
            self.add_message(
                v.code,
                node=v.node,
                args=v.message_args or (),
            )
