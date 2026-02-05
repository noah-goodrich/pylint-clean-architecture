"""Pattern checks (W9005, W9006, W9019)."""

from collections.abc import Mapping
from typing import TYPE_CHECKING

import astroid  # type: ignore[import-untyped]
from pylint.checkers import BaseChecker

if TYPE_CHECKING:
    from pylint.lint import PyLinter

    from clean_architecture_linter.domain.config import ConfigurationLoader

from clean_architecture_linter.domain.protocols import (
    AstroidProtocol,
    PythonProtocol,
    StubAuthorityProtocol,
)
from clean_architecture_linter.domain.registry_types import RuleRegistryEntry
from clean_architecture_linter.domain.rule_msgs import RuleMsgBuilder
from clean_architecture_linter.domain.rules.delegation import DelegationRule
from clean_architecture_linter.domain.rules.demeter import LawOfDemeterRule


class PatternChecker(BaseChecker):
    """W9005: Delegation anti-pattern detection. Thin: delegates to DelegationRule."""

    name: str = "clean-arch-delegation"
    CODES = ["W9005"]

    def __init__(
        self, linter: "PyLinter", registry: Mapping[str, RuleRegistryEntry]
    ) -> None:
        self.msgs = RuleMsgBuilder.build_msgs_for_codes(registry, self.CODES)
        super().__init__(linter)
        self._delegation_rule = DelegationRule()

    def visit_if(self, node: astroid.nodes.If) -> None:
        """Delegate W9005 to domain rule; report each violation via add_message."""
        for v in self._delegation_rule.check(node):
            self.add_message(
                v.code,
                node=v.node,
                args=v.message_args or (),
            )


class CouplingChecker(BaseChecker):
    """W9006, W9019: Law of Demeter / unstable dependency. Thin: delegates to LawOfDemeterRule."""

    name: str = "clean-arch-demeter"
    CODES = ["W9006", "W9019"]

    def __init__(
        self,
        linter: "PyLinter",
        ast_gateway: AstroidProtocol,
        python_gateway: PythonProtocol,
        stub_resolver: StubAuthorityProtocol,
        config_loader: "ConfigurationLoader",
        registry: Mapping[str, RuleRegistryEntry],
    ) -> None:
        self.msgs = RuleMsgBuilder.build_msgs_for_codes(registry, self.CODES)
        super().__init__(linter)
        self._demeter_rule = LawOfDemeterRule(
            ast_gateway=ast_gateway,
            python_gateway=python_gateway,
            stub_resolver=stub_resolver,
            config_loader=config_loader,
        )
        self._locals_map: dict[str, bool] = {}

    def visit_functiondef(self, node: astroid.nodes.FunctionDef) -> None:
        self._locals_map = {}

    def visit_assign(self, node: astroid.nodes.Assign) -> None:
        self._demeter_rule.record_assign(node, self._locals_map)

    def visit_call(self, node: astroid.nodes.Call) -> None:
        for v in self._demeter_rule.check_call(node, self._locals_map):
            self.add_message(
                v.code,
                node=v.node,
                args=v.message_args or (),
            )

    def _is_chain_excluded(
        self,
        node: astroid.nodes.Call,
        chain: list[str],
        curr: astroid.nodes.NodeNG,
    ) -> bool:
        """Shim for tests that mock checker._is_chain_excluded. Delegates to rule."""
        return self._demeter_rule._is_chain_excluded(
            node, chain, curr, self._demeter_rule._config_loader
        )

    def _is_test_file(self, node: astroid.nodes.NodeNG) -> bool:
        """Shim for tests that mock checker._is_test_file. Delegates to rule."""
        return self._demeter_rule._is_test_file(node)
