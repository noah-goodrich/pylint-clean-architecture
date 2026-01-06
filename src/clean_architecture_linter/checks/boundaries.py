"""Layer boundary checks (W9003-W9009)."""

# AST checks often violate Demeter by design
from pylint.checkers import BaseChecker
from clean_architecture_linter.config import ConfigurationLoader
from clean_architecture_linter.layer_registry import LayerRegistry


class VisibilityChecker(BaseChecker):
    """W9003: Protected member access across layers."""

    name = "clean-arch-visibility"
    msgs = {
        "W9003": (
            'Access to protected member "%s" from outer layer.',
            "clean-arch-visibility",
            "Protected members (_name) should not be accessed across layer boundaries.",
        ),
    }

    def __init__(self, linter=None):
        super().__init__(linter)
        self.config_loader = ConfigurationLoader()

    def visit_attribute(self, node):
        """Check for protected member access."""
        if not self.config_loader.visibility_enforcement:
            return

        if node.attrname.startswith("_") and not node.attrname.startswith("__"):
            # Skip self/cls access
            if hasattr(node.expr, "name") and node.expr.name in ("self", "cls"):
                return

            self.add_message("clean-arch-visibility", node=node, args=(node.attrname,))


class ResourceChecker(BaseChecker):
    """W9004: Forbidden I/O access in UseCase/Domain layers."""

    name = "clean-arch-resources"
    msgs = {
        "W9004": (
            "Forbidden I/O access (%s) in %s layer. Use Repository injection.",
            "clean-arch-resources",
            "Raw I/O operations are forbidden in UseCase and Domain layers.",
        ),
    }

    def __init__(self, linter=None):
        super().__init__(linter)
        self.config_loader = ConfigurationLoader()

    @property
    def forbidden_prefixes(self):
        """Get configured forbidden prefixes."""
        return self.config_loader.config.get("forbidden_prefixes", [])

    def visit_import(self, node):
        """Check for forbidden imports."""
        self._check_import(node, [name for name, _ in node.names])

    def visit_importfrom(self, node):
        """Handle from x import y."""
        if node.modname:
            self._check_import(node, [node.modname])



    def _check_import(self, node, names):
        root = node.root()
        file_path = getattr(root, "file", "")
        current_module = root.name

        layer = self.config_loader.get_layer_for_module(current_module, file_path)

        # Only check UseCase and Domain
        if layer not in (LayerRegistry.LAYER_USE_CASE, LayerRegistry.LAYER_DOMAIN):
            return

        for name in names:
            for prefix in self.forbidden_prefixes:
                clean_prefix = prefix.rstrip(".")
                if name == clean_prefix or name.startswith(clean_prefix + "."):
                    self.add_message(
                        "clean-arch-resources",
                        node=node,
                        args=(f"import {name}", layer)
                    )
                    return
