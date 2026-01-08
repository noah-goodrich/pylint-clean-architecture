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
    def allowed_prefixes(self):
        """Get configured allowed prefixes."""
        # Default safe list
        defaults = {
            "typing",
            "dataclasses",
            "abc",
            "enum",
            "pathlib",
            "logging",
            "datetime",
            "uuid",
            "re",
            "math",
            "random",
            "decimal",
            "functools",
            "itertools",
            "collections",
            "contextlib",
            "json",
        }

        # Add configured allow-list
        configured = set(self.config_loader.config.get("allowed_prefixes", []))
        return defaults.union(configured)

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

        # EXEMPTION: Tests are allowed to import anything
        # Check for /tests/ or /test/ in path (robust to OS separators), or module name
        normalized_path = file_path.replace("\\", "/")
        module_name = root.name

        is_test_path = (
            "/tests/" in normalized_path
            or normalized_path.startswith("tests/")
            or "/test/" in normalized_path
            or "tests" in normalized_path.split("/")
        )

        is_test_module = (
            ".tests." in module_name
            or module_name.startswith("tests.")
            or module_name.startswith("test_")
        )

        if is_test_path or is_test_module:
            return

        current_module = root.name

        layer = self.config_loader.get_layer_for_module(current_module, file_path)

        # Only check UseCase and Domain
        if layer not in (LayerRegistry.LAYER_USE_CASE, LayerRegistry.LAYER_DOMAIN):
            return

        for name in names:
            # Check 1: Is it an internal module? (domain, dto, use_cases)
            # We assume internal modules match our layer naming conventions
            parts = name.split(".")
            if any(
                p in parts
                for p in ("domain", "dto", "use_cases", "protocols", "models")
            ):
                continue

            # Check 2: Is it in the allowed prefixes list?
            # Check pure match or sub-module match (e.g. 'datetime' or 'datetime.datetime')
            is_allowed = False
            for allowed in self.allowed_prefixes:
                if name == allowed or name.startswith(allowed + "."):
                    is_allowed = True
                    break

            if is_allowed:
                continue

            # If not internal and not allowed, it is forbidden.
            self.add_message(
                "clean-arch-resources",
                node=node,
                args=(f"import {name}", layer),
            )
            return
