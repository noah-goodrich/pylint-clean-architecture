"""Dependency Injection rule (W9301)."""

from typing import TYPE_CHECKING, ClassVar

import astroid  # type: ignore[import-untyped]

from clean_architecture_linter.domain.rules import Checkable, Violation

if TYPE_CHECKING:
    from clean_architecture_linter.domain.config import ConfigurationLoader
    from clean_architecture_linter.domain.protocols import AstroidProtocol, PythonProtocol


class DIRule(Checkable):
    """Rule for W9301: Direct instantiation of infrastructure in UseCase layer."""

    code: str = "W9301"
    description: str = "Dependency Injection: do not instantiate infrastructure in UseCase."
    fix_type: str = "code"
    INFRA_SUFFIXES: ClassVar[tuple[str, ...]] = (
        "Gateway", "Repository", "Client")

    def __init__(
        self,
        python_gateway: "PythonProtocol",
        ast_gateway: "AstroidProtocol",
        config_loader: "ConfigurationLoader",
    ) -> None:
        self._python_gateway = python_gateway
        self._ast_gateway = ast_gateway
        self._config_loader = config_loader

    def check(self, node: astroid.nodes.NodeNG) -> list[Violation]:
        """Check a Call node for W9301. Returns at most one violation."""
        from clean_architecture_linter.domain.layer_registry import LayerRegistry

        if not hasattr(node, "func"):
            return []
        layer = self._python_gateway.get_node_layer(node, self._config_loader)
        if layer != LayerRegistry.LAYER_USE_CASE:
            return []
        call_name = self._ast_gateway.get_call_name(node)
        if not call_name:
            return []
        if not any(call_name.endswith(s) for s in self.INFRA_SUFFIXES):
            return []
        return [
            Violation.from_node(
                code=self.code,
                message=f"Direct instantiation of infrastructure: {call_name}.",
                node=node,
                message_args=(call_name,),
            )
        ]
