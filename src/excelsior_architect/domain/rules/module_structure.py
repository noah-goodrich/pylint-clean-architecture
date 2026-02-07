"""Module structure rules (W9010, W9011, W9017, W9018, W9020)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import astroid

from excelsior_architect.domain.layer_registry import LayerRegistry
from excelsior_architect.domain.rules import Violation

if TYPE_CHECKING:
    from excelsior_architect.domain.config import ConfigurationLoader

TOP_LEVEL_FUNCTION_ALLOWLIST: frozenset[str] = frozenset(
    {"__main__.py", "checker.py"}
)


class ModuleStructureRule:
    """Rule for W9010, W9011, W9017, W9018, W9020. Stateless; checker holds module state."""

    code_god_file: str = "W9010"
    code_deep_structure: str = "W9011"
    code_layer_integrity: str = "W9017"
    code_top_level_functions: str = "W9018"
    code_global_state: str = "W9020"
    description: str = "Module structure: god file, deep structure, layer integrity, top-level functions, global state."
    fix_type: str = "code"

    def __init__(self, config_loader: ConfigurationLoader) -> None:
        self._config_loader = config_loader

    def check_visit_module(self, node: astroid.nodes.Module) -> list[Violation]:
        """Check W9011, W9017 on module entry. Caller resets state before calling."""
        violations: list[Violation] = []
        if self._is_root_logic(node):
            violations.append(
                Violation.from_node(
                    code=self.code_deep_structure,
                    message=f"Deep structure: root logic in {node.name}",
                    node=node,
                    message_args=(node.name,),
                )
            )
        file_path = getattr(node, "file", "")
        if file_path and self._is_unmapped_file(file_path):
            violations.append(
                Violation.from_node(
                    code=self.code_layer_integrity,
                    message=f"Layer integrity: unmapped file in src/ {file_path}",
                    node=node,
                    message_args=(file_path,),
                )
            )
        return violations

    def record_classdef(
        self, node: astroid.nodes.ClassDef
    ) -> tuple[str | None, bool, str]:
        """Return (layer, is_heavy, class_name) for caller to update state."""
        layer = self._config_loader.get_layer_for_class_node(node)
        if not layer:
            file_path = getattr(node.root(), "file", "")
            layer = self._config_loader.resolve_layer(
                node.name, file_path, node=node
            )
        is_heavy = bool(
            layer and self._is_heavy_component(layer, node)
        )
        return (layer, is_heavy, node.name)

    def record_functiondef(self, node: astroid.nodes.FunctionDef) -> bool:
        """Return True if top-level function (parent is Module). Caller increments count."""
        return isinstance(
            getattr(node, "parent", None), astroid.nodes.Module
        )

    def check_leave_module(
        self,
        node: astroid.nodes.Module,
        current_classes: list[str],
        current_layer_types: set[str],
        heavy_component_count: int,
        top_level_function_count: int,
    ) -> list[Violation]:
        """Check W9010, W9018. Call when leaving a module; caller passes state."""
        violations: list[Violation] = []
        if len(current_layer_types) > 1:
            layers_str = ", ".join(sorted(current_layer_types))
            violations.append(
                Violation.from_node(
                    code=self.code_god_file,
                    message=f"God file: Mixed layers: {layers_str}",
                    node=node,
                    message_args=(f"Mixed layers: {layers_str}",),
                )
            )
        elif heavy_component_count > 1:
            violations.append(
                Violation.from_node(
                    code=self.code_god_file,
                    message=f"God file: {heavy_component_count} Heavy components found",
                    node=node,
                    message_args=(
                        f"{heavy_component_count} Heavy components found",),
                )
            )
        file_path = getattr(node, "file", "")
        if file_path and self._has_disallowed_top_level_functions(
            node, file_path, top_level_function_count
        ):
            violations.append(
                Violation.from_node(
                    code=self.code_top_level_functions,
                    message=f"No top-level functions: {file_path}",
                    node=node,
                    message_args=(file_path,),
                )
            )
        return violations

    def check_global(self, node: astroid.nodes.Global) -> list[Violation]:
        """Check W9020 for each name in global statement."""
        violations: list[Violation] = []
        for name in getattr(node, "names", []):
            violations.append(
                Violation.from_node(
                    code=self.code_global_state,
                    message=f"Global state: use of 'global {name}' not allowed",
                    node=node,
                    message_args=(name,),
                )
            )
        return violations

    def _is_root_logic(self, node: astroid.nodes.Module) -> bool:
        file_path = getattr(node, "file", "")
        if not file_path:
            return False
        path_obj = Path(str(file_path))
        try:
            cwd = Path.cwd()
            rel_path = path_obj.relative_to(
                cwd) if path_obj.is_absolute() else path_obj
        except (ValueError, TypeError):
            return False
        if len(rel_path.parts) > 1:
            return False
        allowed = {"setup.py", "conftest.py",
                   "manage.py", "wsgi.py", "asgi.py"}
        if rel_path.name in allowed:
            return False
        return not rel_path.name.startswith("test_")

    def _is_heavy_component(self, layer: str, node: astroid.nodes.ClassDef) -> bool:
        if "Protocol" in node.name or "DTO" in node.name:
            return False
        try:
            if any(getattr(a, "name", None) == "Protocol" for a in node.ancestors()):
                return False
        except Exception:
            pass
        return layer in (
            LayerRegistry.LAYER_USE_CASE,
            LayerRegistry.LAYER_INFRASTRUCTURE,
        )

    def _is_unmapped_file(self, file_path: str) -> bool:
        path_obj = Path(str(file_path))
        try:
            parts = path_obj.parts
            if "src" not in parts:
                return False
            src_index = parts.index("src")
            rel_from_src = Path(*parts[src_index + 1:])
            if rel_from_src.name == "__init__.py":
                return False
            module_parts = []
            for part in parts[src_index + 1:]:
                if part.endswith(".py"):
                    module_parts.append(part[:-3])
                else:
                    module_parts.append(part)
            module_name = ".".join(module_parts)
            layer = self._config_loader.get_layer_for_module(
                module_name, file_path
            )
            if layer:
                return False
            layer = self._config_loader.registry.resolve_layer("", file_path)
            return layer is None
        except (ValueError, IndexError, TypeError):
            return False

    def _is_allowlisted_for_top_level_functions(self, file_path: str) -> bool:
        return Path(str(file_path)).name in TOP_LEVEL_FUNCTION_ALLOWLIST

    def _is_mapped_src_file(self, file_path: str) -> bool:
        return bool(self._config_loader.registry.resolve_layer("", file_path))

    def _has_disallowed_top_level_functions(
        self,
        node: astroid.nodes.Module,
        file_path: str,
        top_level_function_count: int,
    ) -> bool:
        if top_level_function_count == 0:
            return False
        if not self._is_mapped_src_file(file_path):
            return False
        return not self._is_allowlisted_for_top_level_functions(file_path)
