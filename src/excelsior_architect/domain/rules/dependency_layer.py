"""Layer Dependency Rule (W9001) - Strict layer dependency enforcement."""

from typing import TYPE_CHECKING, ClassVar

import astroid

from excelsior_architect.domain.layer_registry import LayerRegistry
from excelsior_architect.domain.rules import Checkable, Violation

if TYPE_CHECKING:
    from excelsior_architect.domain.config import ConfigurationLoader
    from excelsior_architect.domain.protocols import PythonProtocol


_DEFAULT_RULES: dict[str, set[str]] = {
    LayerRegistry.LAYER_DOMAIN: set(),
    LayerRegistry.LAYER_USE_CASE: {LayerRegistry.LAYER_DOMAIN},
    LayerRegistry.LAYER_INTERFACE: {
        LayerRegistry.LAYER_USE_CASE,
        LayerRegistry.LAYER_DOMAIN,
    },
    LayerRegistry.LAYER_INFRASTRUCTURE: {
        LayerRegistry.LAYER_USE_CASE,
        LayerRegistry.LAYER_DOMAIN,
        LayerRegistry.LAYER_INTERFACE,
    },
}


class LayerDependencyRule(Checkable):
    """Rule for W9001: Strict Layer Dependency enforcement."""

    code: str = "W9001"
    description: str = "Layer dependency: imports must respect layer matrix."
    fix_type: str = "code"
    DEFAULT_RULES: ClassVar[dict[str, set[str]]] = _DEFAULT_RULES

    def __init__(
        self,
        python_gateway: "PythonProtocol",
        config_loader: "ConfigurationLoader",
    ) -> None:
        self._python_gateway = python_gateway
        self._config_loader = config_loader

    def check(self, node: astroid.nodes.NodeNG) -> list[Violation]:
        """Check an import node for W9001 violations. Returns one violation per disallowed import."""
        violations: list[Violation] = []
        names_attr = getattr(node, "names", None)
        if names_attr is not None and not getattr(node, "modname", None):
            for item in names_attr:
                name = item[0] if isinstance(item, (list, tuple)) else item
                if isinstance(name, tuple):
                    name = name[0]
                v = self._check_import(node, str(name))
                if v:
                    violations.append(v)
            return violations
        modname = getattr(node, "modname", None)
        if modname:
            v = self._check_import(node, modname)
            if v:
                violations.append(v)
        return violations

    def _check_import(self, node: astroid.nodes.NodeNG, import_name: str) -> Violation | None:
        current_layer = self._python_gateway.get_node_layer(
            node, self._config_loader)
        root = node.root()
        current_file: str = getattr(root, "file", "") or ""
        if not isinstance(current_file, str):
            current_file = ""
        parts = current_file.split("/") if current_file else []
        if "tests" in parts or (parts[-1].startswith("test_") if len(parts) > 0 else False):
            return None
        if not current_layer:
            return None
        simulated_path = "/" + import_name.replace(".", "/")
        imported_layer = self._config_loader.resolve_layer(
            import_name, simulated_path)
        if not imported_layer:
            imported_layer = self._config_loader.get_layer_for_module(
                import_name)
        if not imported_layer:
            return None
        if current_layer == imported_layer:
            return None
        for kernel_mod in self._config_loader.shared_kernel_modules:
            if import_name == kernel_mod or import_name.startswith(kernel_mod + "."):
                return None
        allowed_layers = self.DEFAULT_RULES.get(current_layer, set())
        if imported_layer in allowed_layers:
            return None
        return Violation.from_node(
            code=self.code,
            message=f"Layer dependency: {imported_layer} not allowed in {current_layer}.",
            node=node,
            message_args=(imported_layer, current_layer),
        )
