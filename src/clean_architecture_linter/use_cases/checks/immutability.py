"""Immutability checks (W9601)."""

from typing import TYPE_CHECKING, Optional

import astroid  # type: ignore[import-untyped]

if TYPE_CHECKING:
    from pylint.lint import PyLinter

from pylint.checkers import BaseChecker

from clean_architecture_linter.domain.config import ConfigurationLoader
from clean_architecture_linter.domain.layer_registry import LayerRegistry
from clean_architecture_linter.domain.protocols import PythonProtocol


class ImmutabilityChecker(BaseChecker):
    """W9601: Domain Immutability enforcement."""

    name: str = "clean-arch-immutability"

    def __init__(self, linter: "PyLinter", python_gateway: Optional[PythonProtocol] = None) -> None:
        self.msgs = {
            "W9601": (
                "Domain Immutability Violation: Attribute assignment in %s layer. "
                "Clean Fix: Use dataclasses with frozen=True or namedtuples.",
                "domain-immutability-violation",
                "Domain Entities should be immutable to prevent side-effect bugs.",
            )
        }
        super().__init__(linter)
        self.config_loader = ConfigurationLoader()
        self._python_gateway = python_gateway

    def visit_assignattr(self, node: astroid.nodes.AssignAttr) -> None:
        """Flag attribute assignments in the Domain layer."""
        layer = self._python_gateway.get_node_layer(node, self.config_loader)

        if layer != LayerRegistry.LAYER_DOMAIN:
            return

        # Skip __init__ assignments
        frame = node.frame()
        if isinstance(frame, astroid.nodes.FunctionDef) and frame.name == "__init__":
            return

        self.add_message("domain-immutability-violation", node=node, args=(layer,))

    def _is_dataclass_name(self, n: astroid.nodes.NodeNG) -> bool:
        """Return True if node is 'dataclass' (Name or Attribute)."""
        if isinstance(n, astroid.nodes.Name):
            return n.name == "dataclass"
        if isinstance(n, astroid.nodes.Attribute):
            return n.attrname == "dataclass"
        return False

    def _dataclass_frozen_from_decorators(
        self, decorators: list
    ) -> tuple[bool, bool]:
        """Scan decorator list for @dataclass and frozen=True. Returns (is_dataclass, is_frozen)."""
        is_dataclass: bool = False
        is_frozen: bool = False
        for decorator in decorators:
            if self._is_dataclass_name(decorator):
                is_dataclass: bool = True
            elif isinstance(decorator, astroid.nodes.Call):
                if self._is_dataclass_name(decorator.func):
                    is_dataclass: bool = True
                    if decorator.keywords:
                        for kw in decorator.keywords:
                            if (
                                kw.arg == "frozen"
                                and isinstance(kw.value, astroid.nodes.Const)
                                and kw.value.value is True
                            ):
                                is_frozen: bool = True
                                break
        return (is_dataclass, is_frozen)

    def visit_classdef(self, node: astroid.nodes.ClassDef) -> None:
        """W9601: Enforce frozen dataclasses in Domain layer."""
        layer = self._python_gateway.get_node_layer(node, self.config_loader)
        if layer != LayerRegistry.LAYER_DOMAIN:
            return
        if not node.decorators:
            return
        is_dataclass, is_frozen = self._dataclass_frozen_from_decorators(
            node.decorators.nodes
        )
        if is_dataclass and not is_frozen:
            self.add_message("domain-immutability-violation", node=node, args=(layer,))
