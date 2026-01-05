"""Layer boundary checks (W9003-W9009)."""

# AST checks often violate Demeter by design
# pylint: disable=law-of-demeter-violation
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

    # Hardcoded forbidden patterns for strict layers
    # Default forbidden patterns
    DEFAULT_FORBIDDEN_PREFIXES = [
        "os.",
        "open",
        "builtins.open",
        "requests.",
        "urllib.",
        "httpx.",
        "sqlalchemy.",
        "sqlite3.",
        "psycopg2.",
        "snowflake.connector",
        "snowflake.snowpark",
        "snowflake.core",
    ]

    def __init__(self, linter=None):
        super().__init__(linter)
        self.config_loader = ConfigurationLoader()

    @property
    def forbidden_prefixes(self):
        """Combine defaults with configured prefixes."""
        # This assumes ConfigurationLoader has a way to get this list
        # If not, we might need to add it to config.py as well
        # For now, we'll try to get it from a potential config attribute
        configured = getattr(self.config_loader, "forbidden_prefixes", [])
        return self.DEFAULT_FORBIDDEN_PREFIXES + configured

    def visit_import(self, node):
        self._check_import(node, [name for name, _ in node.names])

    def visit_importfrom(self, node):
        # Construct full module path: 'from foo.bar import baz' -> 'foo.bar.baz' ? No, better to check 'foo.bar'
        # Actually if we forbid 'snowflake.connector', then 'from snowflake.connector import connect' should be caught on 'snowflake.connector'
        if node.modname:
             self._check_import(node, [node.modname])

    def _check_import(self, node, names):
        root = node.root()
        file_path = getattr(root, "file", "")
        current_module = self.linter.current_name

        layer = self.config_loader.get_layer_for_module(current_module, file_path)
        print(f"DEBUG: checking import {names} in {current_module} ({layer})")

        # Only check UseCase and Domain
        if layer not in (LayerRegistry.LAYER_USE_CASE, LayerRegistry.LAYER_DOMAIN):
            print(f"DEBUG: skipping layer {layer}")
            return

        for name in names:
            for prefix in self.forbidden_prefixes:
                # remove trailing dot for module matching if present
                clean_prefix = prefix.rstrip(".")
                if name == clean_prefix or name.startswith(clean_prefix + "."):
                    print(f"DEBUG: MATCH {name} with {clean_prefix}")
                    self.add_message("clean-arch-resources", node=node, args=(f"import {name}", layer))
                    return

    def visit_call(self, node):
        root = node.root()
        file_path = getattr(root, "file", "")
        current_module = self.linter.current_name

        layer = self.config_loader.get_layer_for_module(current_module, file_path)

        if layer not in (LayerRegistry.LAYER_USE_CASE, LayerRegistry.LAYER_DOMAIN) and layer is not None:
            return

        # If layer is None (Unclassified), we treat it restrictively (Fail Closed)
        # to force architectural classification.

        call_name = self._get_call_name(node)
        if not call_name:
            return

        # 1. Check forbidden prefixes (Global)
        for prefix in self.forbidden_prefixes:
            if call_name.startswith(prefix) or call_name == prefix.rstrip("."):
                self.add_message("clean-arch-resources", node=node, args=(call_name, layer))
                return

        # 2. Check configured resource access methods
        resource_methods = self.config_loader.get_resource_access_methods()
        found_resource_type = None
        for r_type, methods in resource_methods.items():
            if call_name in methods:
                found_resource_type = r_type
                break

        if found_resource_type:
            # Check if allowed in this layer
            allowed = []
            if "layers" in self.config_loader.config:
                # Find the config for the current layer
                for l in self.config_loader.config["layers"]:
                    if l.get("name") == layer:
                        allowed = l.get("allowed_resources", [])
                        break

            if found_resource_type not in allowed:
                self.add_message("clean-arch-resources", node=node, args=(call_name, layer))

    def _get_call_name(self, node):
        """Reconstruct call name from AST."""
        if hasattr(node.func, "attrname"):
            return self._stringify_node(node.func)
        if hasattr(node.func, "name"):
            return node.func.name
        return None

    def _stringify_node(self, node):
        if hasattr(node, "name"):
            return node.name
        if hasattr(node, "attrname"):
            base = self._stringify_node(node.expr)
            return f"{base}.{node.attrname}" if base else node.attrname
        return None
