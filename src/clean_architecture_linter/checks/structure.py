"""Module structure checks (W9010, W9011)."""

from pathlib import Path
from typing import TYPE_CHECKING

# AST checks often violate Demeter by design
import astroid  # type: ignore[import-untyped]

if TYPE_CHECKING:
    from pylint.lint import PyLinter
from pylint.checkers import BaseChecker

from clean_architecture_linter.config import ConfigurationLoader
from clean_architecture_linter.layer_registry import LayerRegistry


class ModuleStructureChecker(BaseChecker):
    """
    Governance Engine Rules:
    W9010: God File Violation (Mixed Layers or Multiple Heavy Components)
    W9011: Deep Structure Violation (Root Logic)
    W9012: God Module (function-only file with too many top-level functions)
    W9017: Layer Integrity Gate - Unmapped file in src/
    W9018: Class-Only Mandate - Procedural file in UseCase/Infrastructure
    """

    name: str = "clean-arch-structure"
    GOD_MODULE_FUNCTION_THRESHOLD: int = 5

    def __init__(self, linter: "PyLinter") -> None:
        self.msgs = {
            "W9010": (
                "God File detected: %s. Clean Fix: Split into separate files.",
                "clean-arch-god-file",
                "A file should not contain multiple 'Heavy' components or mixed layers.",
            ),
            "W9011": (
                "Deep Structure violation: Module '%s' in project root. Clean Fix: Move to a sub-package.",
                "clean-arch-folder-structure",
                "Non-boilerplate logic must reside in sub-packages (e.g. core/, gateways/).",
            ),
            "W9017": (
                "Layer Integrity violation: File '%s' is unmapped. Clean Fix: Add to [tool.clean-arch.layer_map] in pyproject.toml.",
                "clean-arch-layer-integrity",
                "All files in src/ must be mapped to an architectural layer.",
            ),
            "W9018": (
                "Class-Only violation: Module '%s' contains top-level functions but no classes. Clean Fix: Migrate procedural logic into service objects.",
                "clean-arch-class-only",
                "UseCase and Infrastructure layers must use classes, not top-level functions.",
            ),
        }
        super().__init__(linter)
        self.config_loader = ConfigurationLoader()
        self.current_classes: list[str] = []
        self.current_layer_types: set[str] = set()
        self.heavy_component_count: int = 0
        self.top_level_function_count: int = 0

    def open(self) -> None:
        """Called when starting to process a file."""
        self.config_loader.load_config()

    def visit_module(self, node: astroid.nodes.Module) -> None:
        """Process module level checks."""
        self.current_classes = []
        self.current_layer_types = set()
        self.heavy_component_count = 0
        self.top_level_function_count = 0

        # W9011: Root Check
        if self._is_root_logic(node):
            self.add_message("clean-arch-folder-structure", node=node, args=(node.name,))

        # W9017: Layer Integrity Gate - Check for unmapped files in src/
        file_path = getattr(node, "file", "")
        if file_path:
            if self._is_unmapped_file(file_path):
                self.add_message("clean-arch-layer-integrity", node=node, args=(file_path,))

    def leave_module(self, node: astroid.nodes.Module) -> None:
        """Check accumulated stats for God File (W9020) and Class-Only (W9018)."""
        # If we have mixed layers
        if len(self.current_layer_types) > 1:
            layers_str: str = ", ".join(sorted(self.current_layer_types))
            self.add_message(
                "clean-arch-god-file",
                node=node,
                args=(f"Mixed layers: {layers_str}",),
            )

        # If we have multiple heavy components
        elif self.heavy_component_count > 1:
            self.add_message(
                "clean-arch-god-file",
                node=node,
                args=(f"{self.heavy_component_count} Heavy components found",),
            )

        # W9018: Class-Only Mandate - Check for procedural files in UseCase/Infrastructure
        file_path = getattr(node, "file", "")
        if file_path and self._is_procedural_in_restricted_layer(node, file_path):
            self.add_message("clean-arch-class-only", node=node, args=(file_path,))

    def visit_classdef(self, node: astroid.nodes.ClassDef) -> None:
        """Visit class definition to categorize."""
        # Resolve layer using the new inheritance-aware method
        layer = self.config_loader.get_layer_for_class_node(node)

        # Fallback to file path if class-specific resolution failed
        if not layer:
            file_path = getattr(node.root(), "file", "")
            layer = self.config_loader.resolve_layer(node.name, file_path, node=node)

        if layer:
            self.current_layer_types.add(layer)
            if self._is_heavy_component(layer, node):
                self.heavy_component_count += 1

        # Track classes for W9018 check
        self.current_classes.append(node.name)

    def visit_functiondef(self, node: astroid.nodes.FunctionDef) -> None:
        """Visit function definition to track top-level functions."""
        # Only count top-level functions (not methods)
        if isinstance(node.parent, astroid.nodes.Module):
            self.top_level_function_count += 1

    def _is_root_logic(self, node: astroid.nodes.Module) -> bool:
        """Check if file is in project root and not allowed boilerplate."""
        file_path = getattr(node, "file", "")
        if not file_path:
            return False

        path_obj = Path(file_path)
        # Assuming project root is where we run pylint from, or we try to detect it.
        # But node.file is absolute. We need relative path to execution root or pyproject.

        try:
            cwd = Path.cwd()
            rel_path = path_obj.relative_to(cwd) if path_obj.is_absolute() else path_obj
        except ValueError:
            return False

        # If it's in a subdirectory?
        if len(rel_path.parts) > 1:
            return False  # It's deeper than root

        # It is in root. Check allowed files.
        allowed = {"setup.py", "conftest.py", "manage.py", "wsgi.py", "asgi.py"}
        if rel_path.name in allowed:
            return False

        return not rel_path.name.startswith("test_")

    def _is_heavy_component(self, layer: str, node: astroid.nodes.ClassDef) -> bool:
        """Check if layer is considered 'Heavy'."""
        # W9020 Refinement:
        # Protocols (checking for Protocol in ancestors or name) are LIGHT.
        # DTOs (checking name) are LIGHT.
        if "Protocol" in node.name or "DTO" in node.name:
            return False

        # Check ancestors for Protocol
        try:
            if any(a.name == "Protocol" for a in node.ancestors()):
                return False
        except Exception:
            pass

        # Heavy Layers: UseCase and Infrastructure
        return layer in (
            LayerRegistry.LAYER_USE_CASE,
            LayerRegistry.LAYER_INFRASTRUCTURE,
        )

    def _is_unmapped_file(self, file_path: str) -> bool:
        """Check if file is in src/ and unmapped (W9017)."""
        path_obj = Path(file_path)

        # Check if file is in src/ directory
        try:
            # Check if path contains 'src' directory
            parts = path_obj.parts
            if 'src' not in parts:
                return False

            # Get relative path from src
            src_index = parts.index('src')
            rel_from_src = Path(*parts[src_index + 1:])

            # Exclude __init__.py files
            if rel_from_src.name == '__init__.py':
                return False

            # Convert file path to module name for layer_map checking
            # e.g., /path/to/src/clean_architecture_linter/domain/rules.py
            # -> clean_architecture_linter.domain.rules
            module_parts = []
            for part in parts[src_index + 1:]:
                if part.endswith('.py'):
                    module_parts.append(part[:-3])  # Remove .py extension
                else:
                    module_parts.append(part)

            module_name = '.'.join(module_parts)

            # Check layer_map first (explicit mappings)
            layer = self.config_loader.get_layer_for_module(module_name, file_path)
            if layer:
                return False

            # Fallback to registry resolution (convention-based)
            layer = self.config_loader.registry.resolve_layer("", file_path)
            return layer is None
        except (ValueError, IndexError):
            return False

    def _is_procedural_in_restricted_layer(self, node: astroid.nodes.Module, file_path: str) -> bool:
        """Check if module has top-level functions but no classes in UseCase/Infrastructure (W9018)."""
        # Must have top-level functions but no classes
        if self.top_level_function_count == 0 or len(self.current_classes) > 0:
            return False

        # Check if file is in UseCase or Infrastructure layer
        layer = self.config_loader.registry.resolve_layer("", file_path)
        if not layer:
            return False

        return layer in (
            LayerRegistry.LAYER_USE_CASE,
            LayerRegistry.LAYER_INFRASTRUCTURE,
        )
