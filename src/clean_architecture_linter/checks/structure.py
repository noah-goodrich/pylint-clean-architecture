"""Module structure checks (W9010, W9011)."""

from pathlib import Path

# AST checks often violate Demeter by design
from pylint.checkers import BaseChecker

from clean_architecture_linter.config import ConfigurationLoader
from clean_architecture_linter.layer_registry import LayerRegistry


class ModuleStructureChecker(BaseChecker):
    """
    Governance Engine Rules:
    W9010: God File Violation (Mixed Layers or Multiple Heavy Components)
    W9011: Deep Structure Violation (Root Logic)
    """

    name = "clean-arch-structure"

    def __init__(self, linter=None):
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
        }
        super().__init__(linter)
        self.config_loader = ConfigurationLoader()
        self.current_classes = []
        self.current_layer_types = set()
        self.heavy_component_count = 0

    def open(self):
        """Called when starting to process a file."""
        self.config_loader.load_config()

    def visit_module(self, node):
        """Process module level checks."""
        self.current_classes = []
        self.current_layer_types = set()
        self.heavy_component_count = 0

        # W9011: Root Check
        if self._is_root_logic(node):
            self.add_message("clean-arch-folder-structure", node=node, args=(node.name,))

    def leave_module(self, node):
        """Check accumulated stats for God File (W9020)."""
        # If we have mixed layers
        if len(self.current_layer_types) > 1:
            layers_str = ", ".join(sorted(self.current_layer_types))
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

    def visit_classdef(self, node):
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

    def _is_root_logic(self, node):
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

    def _is_heavy_component(self, layer, node):
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
