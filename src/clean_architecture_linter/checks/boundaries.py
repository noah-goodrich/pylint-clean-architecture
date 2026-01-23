"""Layer boundary checks (W9003-W9009)."""

from typing import TYPE_CHECKING, Optional, List, Set

import astroid  # type: ignore[import-untyped]

if TYPE_CHECKING:
    from pylint.lint import PyLinter

from pylint.checkers import BaseChecker

from clean_architecture_linter.config import ConfigurationLoader
from clean_architecture_linter.domain.protocols import PythonProtocol
from clean_architecture_linter.layer_registry import LayerRegistry


class VisibilityChecker(BaseChecker):
    """W9003: Protected member access across layers."""

    name: str = "clean-arch-visibility"

    def __init__(self, linter: "PyLinter") -> None:
        self.msgs = {
            "W9003": (
                'Access to protected member "%s" from outer layer. Clean Fix: Expose public Interface or Use Case.',
                "clean-arch-visibility",
                "Protected members (_name) should not be accessed across layer boundaries.",
            )
        }
        super().__init__(linter)
        self.config_loader = ConfigurationLoader()

    def visit_attribute(self, node: astroid.nodes.Attribute) -> None:
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

    name: str = "clean-arch-resources"

    def __init__(self, linter: "PyLinter", python_gateway: Optional[PythonProtocol] = None) -> None:
        self.msgs = {
            "W9004": (
                "Forbidden I/O access (%s) in %s layer. Clean Fix: Move logic to Infrastructure "
                "and inject via a Domain Protocol.",
                "clean-arch-resources",
                "Raw I/O operations are forbidden in UseCase and Domain layers.",
            )
        }
        super().__init__(linter)
        self.config_loader = ConfigurationLoader()
        self._python_gateway = python_gateway

    @property
    def allowed_prefixes(self) -> Set[str]:
        """Get configured allowed prefixes."""
        defaults: Set[str] = {
            "typing", "dataclasses", "abc", "enum", "pathlib", "logging",
            "datetime", "uuid", "re", "math", "random", "decimal",
            "functools", "itertools", "collections", "contextlib", "json",
        }
        raw_prefixes = self.config_loader.config.get("allowed_prefixes", [])
        if isinstance(raw_prefixes, list):
            return defaults.union(set(str(p) for p in raw_prefixes))
        return defaults

    def visit_import(self, node: astroid.nodes.Import) -> None:
        """Check for forbidden imports."""
        self._check_import(node, [name for name, _ in node.names])

    def visit_importfrom(self, node: astroid.nodes.ImportFrom) -> None:
        """Handle from x import y."""
        if node.modname:
            self._check_import(node, [node.modname])

    def _check_import(self, node: astroid.nodes.NodeNG, names: List[str]) -> None:
        """Core logic for resource access check."""
        if not self._python_gateway:
            return

        if self._is_test_file(node):
            return

        layer = self._python_gateway.get_node_layer(node, self.config_loader)
        if layer not in (LayerRegistry.LAYER_USE_CASE, LayerRegistry.LAYER_DOMAIN):
            return

        for name in names:
            if self._is_forbidden(name):
                self.add_message("clean-arch-resources", node=node, args=(f"import {name}", layer))
                break

    def _is_test_file(self, node: astroid.nodes.NodeNG) -> bool:
        """Robust test file detection."""
        root = node.root()
        file_path: str = getattr(root, "file", "")
        module_name: str = root.name

        normalized_path = file_path.replace("\\", "/")
        parts: List[str] = normalized_path.split("/")

        return (
            "tests" in parts or
            "test" in parts or
            module_name.startswith("test_") or
            ".tests." in module_name
        )

    def _is_forbidden(self, name: str) -> bool:
        """Determine if a module import is forbidden."""
        parts = name.split(".")
        if any(p in parts for p in self.config_loader.internal_modules):
            return False

        for allowed in self.allowed_prefixes:
            if name == allowed or name.startswith(allowed + "."):
                return False
        return True
