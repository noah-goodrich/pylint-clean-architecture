"""Dependency checks (W9010)."""

from pylint.checkers import BaseChecker

from clean_architecture_linter.config import ConfigurationLoader
from clean_architecture_linter.layer_registry import LayerRegistry


class DependencyChecker(BaseChecker):
    """W9010: Strict Layer Dependency enforcement."""

    name = "clean-arch-dependency"
    msgs = {
        "W9001": (
            "Illegal Dependency: %s layer cannot import from %s layer. Clean Fix: Invert dependency using an "
            "Interface/Protocol in the Domain layer.",
            "clean-arch-dependency",
            "Inner layers (Domain, UseCase) strictly cannot import from Outer layers.",
        ),
    }

    # Default Dependency Matrix (Allowed Imports)
    # Key: Layer doing the import
    # Value: Set of allowed layers to import from
    # Logic: Inner layers are restrictive.
    DEFAULT_RULES = {
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

    def __init__(self, linter=None):
        super().__init__(linter)
        self.config_loader = ConfigurationLoader()

    def visit_import(self, node):
        """Check direct imports: import x.y"""
        for name, _ in node.names:
            self._check_import(node, name)

    def visit_importfrom(self, node):
        """Check from imports: from x import y"""
        self._check_import(node, node.modname)

    def _check_import(self, node, import_name):
        # 1. Determine Current Layer
        root = node.root()
        current_file = getattr(root, "file", "")
        # Fallback to module name if file not available (e.g. in tests)
        current_module = root.name

        current_layer = self.config_loader.get_layer_for_module(current_module, current_file)

        # Skip checks for test files
        if "tests" in current_file.split("/") or "test_" in current_file.split("/")[-1]:
            return

        if not current_layer:
            return  # Unclassified file, allow for now (OR we could fail strict)

        # 2. Determine Imported Layer
        # We need to resolve the imported module's layer.
        # This is tricky because we might not have the file path for the imported module easily
        # without full AST analysis or sys.modules.

        # Simple heuristic: Check against LayerRegistry rules based on module name
        # We simulate a "file path" from the module name to trigger directory matching in registry
        simulated_path = "/" + import_name.replace(".", "/")
        imported_layer = self.config_loader.resolve_layer(import_name, simulated_path)

        # If heuristics fail, user might need to define explicit layer map in config
        if not imported_layer:
            # Try matching package prefixes if available in config
            imported_layer = self.config_loader.get_layer_for_module(import_name)

        if not imported_layer:
            return  # Library or unknown module

        if current_layer == imported_layer:
            return  # Intra-layer imports are OK

        # 3. Check Matrix
        allowed_layers = self.DEFAULT_RULES.get(current_layer, set())

        # Merge with user config overrides if any (TODO)

        if imported_layer not in allowed_layers:
            self.add_message(
                "clean-arch-dependency",
                node=node,
                args=(imported_layer, current_layer),
            )
