"""Module structure checks (W9010, W9011, W9017, W9018, W9020)."""

from collections.abc import Mapping
from typing import TYPE_CHECKING

import astroid  # type: ignore[import-untyped]

if TYPE_CHECKING:
    from pylint.lint import PyLinter
from pylint.checkers import BaseChecker

from clean_architecture_linter.domain.config import ConfigurationLoader
from clean_architecture_linter.domain.registry_types import RuleRegistryEntry
from clean_architecture_linter.domain.rule_msgs import RuleMsgBuilder
from clean_architecture_linter.domain.rules.module_structure import ModuleStructureRule


class ModuleStructureChecker(BaseChecker):
    """
    W9010: God File. W9011: Deep Structure. W9017: Layer Integrity.
    W9018: No top-level functions. W9020: Global state.
    Thin: delegates to ModuleStructureRule.
    """

    name: str = "clean-arch-structure"
    CODES = ["W9010", "W9011", "W9017", "W9018", "W9020"]

    def __init__(
        self,
        linter: "PyLinter",
        config_loader: ConfigurationLoader,
        registry: Mapping[str, RuleRegistryEntry],
    ) -> None:
        self.msgs = RuleMsgBuilder.build_msgs_for_codes(
            registry, self.CODES)
        super().__init__(linter)
        self.config_loader = config_loader
        self._structure_rule = ModuleStructureRule(self.config_loader)
        self._current_classes: list[str] = []
        self._current_layer_types: set[str] = set()
        self._heavy_component_count: int = 0
        self._top_level_function_count: int = 0

    def visit_module(self, node: astroid.nodes.Module) -> None:
        self._current_classes = []
        self._current_layer_types = set()
        self._heavy_component_count = 0
        self._top_level_function_count = 0
        for v in self._structure_rule.check_visit_module(node):
            self.add_message(
                v.code,
                node=v.node,
                args=v.message_args or (),
            )

    def leave_module(self, node: astroid.nodes.Module) -> None:
        for v in self._structure_rule.check_leave_module(
            node,
            self._current_classes,
            self._current_layer_types,
            self._heavy_component_count,
            self._top_level_function_count,
        ):
            self.add_message(
                v.code,
                node=v.node,
                args=v.message_args or (),
            )

    def visit_classdef(self, node: astroid.nodes.ClassDef) -> None:
        layer, is_heavy, class_name = self._structure_rule.record_classdef(node)
        if layer:
            self._current_layer_types.add(layer)
        if is_heavy:
            self._heavy_component_count += 1
        self._current_classes.append(class_name)

    def visit_functiondef(self, node: astroid.nodes.FunctionDef) -> None:
        if self._structure_rule.record_functiondef(node):
            self._top_level_function_count += 1

    def visit_global(self, node: astroid.nodes.Global) -> None:
        for v in self._structure_rule.check_global(node):
            self.add_message(
                v.code,
                node=v.node,
                args=v.message_args or (),
            )
