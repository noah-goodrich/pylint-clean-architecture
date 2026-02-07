"""Layer boundary checks (W9003, W9004)."""

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
from excelsior_architect.domain.rules.boundary_rules import (
    IllegalIOCallRule,
    ResourceRule,
    UIConcernRule,
    VisibilityRule,
)


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
        self.msgs = RuleMsgBuilder.build_msgs_for_codes(
            registry, self.CODES)  # type: ignore[assignment]
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
        self.msgs = RuleMsgBuilder.build_msgs_for_codes(
            registry, self.CODES)  # type: ignore[assignment]
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


class IllegalIOCallChecker(BaseChecker):
    """W9013: Illegal I/O call (print, input, open, Path, etc.) in Domain/UseCase layers."""

    name: str = "clean-arch-illegal-io-call"
    CODES = ["W9013"]

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
        self.config_loader = config_loader
        self._illegal_io_rule = IllegalIOCallRule(
            python_gateway=python_gateway,
            config_loader=config_loader,
        )

    def visit_call(self, node: astroid.nodes.Call) -> None:
        """Delegate W9013 to domain rule."""
        for v in self._illegal_io_rule.check(node):
            self.add_message(
                v.code,
                node=v.node,
                args=v.message_args or (),
            )


class UIConcernChecker(BaseChecker):
    """W9014: UI concern (ANSI codes, emoji, isatty) in Domain layer."""

    name: str = "clean-arch-ui-concern"
    CODES = ["W9014"]

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
        self.config_loader = config_loader
        self._ui_concern_rule = UIConcernRule(
            python_gateway=python_gateway,
            config_loader=config_loader,
        )

    def visit_call(self, node: astroid.nodes.Call) -> None:
        """Delegate W9014 (isatty) to domain rule."""
        for v in self._ui_concern_rule.check_call(node):
            self.add_message(
                v.code,
                node=v.node,
                args=v.message_args or (),
            )

    def visit_const(self, node: astroid.nodes.Const) -> None:
        """Delegate W9014 (ANSI/emoji in strings) to domain rule."""
        for v in self._ui_concern_rule.check_const(node):
            self.add_message(
                v.code,
                node=v.node,
                args=v.message_args or (),
            )
