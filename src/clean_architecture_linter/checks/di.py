"""Dependency Injection checks (W9301)."""

from typing import TYPE_CHECKING, ClassVar, Optional

import astroid  # type: ignore[import-untyped]

if TYPE_CHECKING:
    from pylint.lint import PyLinter

from pylint.checkers import BaseChecker

from clean_architecture_linter.config import ConfigurationLoader
from clean_architecture_linter.di.container import ExcelsiorContainer
from clean_architecture_linter.domain.protocols import AstroidProtocol, PythonProtocol
from clean_architecture_linter.layer_registry import LayerRegistry


class DIChecker(BaseChecker):
    """W9301: Dependency Injection enforcement."""

    name = "clean-arch-di"

    def __init__(self, linter: "PyLinter") -> None:
        self.msgs = {
            "W9301": (
                "DI Violation: %s instantiated directly in UseCase. Use constructor injection. Clean Fix: Pass the "
                "dependency as an argument to __init__.",
                "di-enforcement-violation",
                "Infrastructure classes (Gateway, Repository, Client) must be injected into UseCases.",
            )
        }
        super().__init__(linter)
        self.config_loader = ConfigurationLoader()
        container = ExcelsiorContainer.get_instance()
        self._python_gateway: PythonProtocol = container.get("PythonGateway")
        self._ast_gateway: AstroidProtocol = container.get("AstroidGateway")

    INFRA_SUFFIXES: ClassVar[tuple[str, ...]] = ("Gateway", "Repository", "Client")

    def visit_call(self, node: astroid.nodes.Call) -> None:
        """
        Flag direct instantiation of infrastructure classes in UseCase layer.
        """
        layer = self._python_gateway.get_node_layer(node, self.config_loader)

        # Only enforce on UseCase layer
        if layer != LayerRegistry.LAYER_USE_CASE:
            return

        call_name: Optional[str] = self._ast_gateway.get_call_name(node)
        if not call_name:
            return

        if any(call_name.endswith(suffix) for suffix in self.INFRA_SUFFIXES):
            self.add_message("di-enforcement-violation", node=node, args=(call_name,))
