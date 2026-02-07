"""Dependency Injection rule (W9301)."""

from typing import TYPE_CHECKING, ClassVar, cast

import astroid

from excelsior_architect.domain.rules import Checkable, Violation

if TYPE_CHECKING:
    from excelsior_architect.domain.config import ConfigurationLoader
    from excelsior_architect.domain.protocols import AstroidProtocol, PythonProtocol


class DIRule(Checkable):
    """Rule for W9301: Direct instantiation of infrastructure in Domain/UseCase layer."""

    code: str = "W9301"
    description: str = "Dependency Injection: do not instantiate infrastructure in Domain/UseCase."
    fix_type: str = "code"
    # Expanded: flag any direct instantiation of types that typically belong in infrastructure
    INFRA_SUFFIXES: ClassVar[tuple[str, ...]] = (
        "Gateway", "Repository", "Client", "Adapter", "Service",
        "Reporter", "Storage", "Checker", "Scaffolder",
    )

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
        """Check a Call node for W9301. Flag infrastructure instantiation in Domain/UseCase."""
        from excelsior_architect.domain.layer_registry import LayerRegistry

        if not hasattr(node, "func"):
            return []
        call_node = cast(astroid.nodes.Call, node)
        layer = self._python_gateway.get_node_layer(
            call_node, self._config_loader)
        # Check both Domain and UseCase layers (not only UseCase)
        if layer not in (LayerRegistry.LAYER_USE_CASE, LayerRegistry.LAYER_DOMAIN):
            return []
        call_name = self._ast_gateway.get_call_name(call_node)
        if not call_name:
            return []
        # Extract bare class name (last segment after dot) for suffix check
        bare_name = call_name.split(".")[-1] if "." in call_name else call_name
        if not any(bare_name.endswith(s) for s in self.INFRA_SUFFIXES):
            return []
        return [
            Violation.from_node(
                code=self.code,
                message=f"Direct instantiation of infrastructure: {call_name}. Inject via constructor.",
                node=node,
                message_args=(call_name,),
            )
        ]
