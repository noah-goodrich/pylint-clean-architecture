"""Architectural entropy check (W9030)."""

from collections.abc import Mapping
from typing import TYPE_CHECKING

import astroid  # type: ignore[import-untyped]

if TYPE_CHECKING:
    from pylint.lint import PyLinter

from pylint.checkers import BaseChecker

from clean_architecture_linter.domain.registry_types import RuleRegistryEntry
from clean_architecture_linter.domain.rule_msgs import RuleMsgBuilder
from clean_architecture_linter.domain.rules.entropy_rule import EntropyRule


class EntropyChecker(BaseChecker):
    """W9030: Architectural entropy. Thin: delegates to EntropyRule."""

    name: str = "clean-arch-entropy"
    CODES = ["W9030"]

    def __init__(
        self, linter: "PyLinter", registry: Mapping[str, RuleRegistryEntry]
    ) -> None:
        self.msgs = RuleMsgBuilder.build_msgs_for_codes(registry, self.CODES)
        super().__init__(linter)
        self._entropy_rule = EntropyRule()

    def visit_module(self, node: astroid.nodes.Module) -> None:
        """Delegate W9030 to domain rule; report each violation via add_message."""
        for v in self._entropy_rule.check(node):
            self.add_message(
                v.code,
                node=v.node,
                args=v.message_args or (),
            )

    def close(self) -> None:
        super().close()
