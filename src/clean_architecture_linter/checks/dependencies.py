"""Dependency checks (W9010)."""

from typing import TYPE_CHECKING, ClassVar, Optional

if TYPE_CHECKING:
    from pylint.lint import PyLinter

import astroid  # type: ignore[import-untyped]
from pylint.checkers import BaseChecker

from clean_architecture_linter.config import ConfigurationLoader
from clean_architecture_linter.layer_registry import LayerRegistry


class DependencyChecker(BaseChecker):
    """W9010: Strict Layer Dependency enforcement."""

    name = "clean-arch-dependency"

    def __init__(self, linter: "PyLinter") -> None:
        self.msgs = {
            "W9001": (
                "Illegal Dependency: %s layer is imported by %s layer. Clean Fix: Invert dependency using an "
                "Interface/Protocol in the Domain layer.",
                "clean-arch-dependency",
                "Inner layers (Domain, UseCase) strictly cannot import from Outer layers.",
            )
        }
        super().__init__(linter)
        self.config_loader = ConfigurationLoader()
        from clean_architecture_linter.di.container import ExcelsiorContainer
        self._python_gateway = ExcelsiorContainer.get_instance().get("PythonGateway")

    # Default Dependency Matrix (Allowed Imports)
    DEFAULT_RULES: ClassVar[dict[str, set[str]]] = {
        LayerRegistry.LAYER_DOMAIN: set(),  # Domain imports NOTHING (only stdlib)
        LayerRegistry.LAYER_USE_CASE: {LayerRegistry.LAYER_DOMAIN},
        LayerRegistry.LAYER_INTERFACE: {
            LayerRegistry.LAYER_USE_CASE,
            LayerRegistry.LAYER_DOMAIN,
        },
        LayerRegistry.LAYER_INFRASTRUCTURE: {
            LayerRegistry.LAYER_USE_CASE,
            LayerRegistry.LAYER_DOMAIN,
        },
    }

    def visit_import(self, node: astroid.nodes.Import) -> None:
        """Check direct imports: import x.y"""
        for name, _ in node.names:
            self._check_import(node, name)

    def visit_importfrom(self, node: astroid.nodes.ImportFrom) -> None:
        """Check from imports: from x import y"""
        if node.modname:
            self._check_import(node, node.modname)

    def _check_import(self, node: astroid.nodes.NodeNG, import_name: str) -> None:
        # 1. Determine Current Layer
        current_layer = self._python_gateway.get_node_layer(node, self.config_loader)

        # Skip checks for test files
        root = node.root()
        current_file: str = getattr(root, "file", "")
        if "tests" in current_file.split("/") or "test_" in current_file.split("/")[-1]:
            return

        if not current_layer:
            return

        # 2. Determine Imported Layer
        simulated_path = "/" + import_name.replace(".", "/")
        imported_layer = self.config_loader.resolve_layer(import_name, simulated_path)

        if not imported_layer:
            imported_layer = self.config_loader.get_layer_for_module(import_name)

        if not imported_layer:
            return  # Library or unknown module

        if current_layer == imported_layer:
            return  # Intra-layer imports are OK

        # 3. Check Shared Kernel
        for kernel_mod in self.config_loader.shared_kernel_modules:
            if import_name == kernel_mod or import_name.startswith(kernel_mod + "."):
                return

        # 4. Check Matrix
        allowed_layers = self.DEFAULT_RULES.get(current_layer, set())

        if imported_layer not in allowed_layers:
            self.add_message(
                "clean-arch-dependency",
                node=node,
                args=(imported_layer, current_layer),
            )
