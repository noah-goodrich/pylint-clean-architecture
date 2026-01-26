import sys
import sysconfig
from typing import TYPE_CHECKING, Optional

import astroid  # type: ignore[import-untyped]

from clean_architecture_linter.domain.protocols import PythonProtocol

if TYPE_CHECKING:
    from clean_architecture_linter.domain.config import ConfigurationLoader


class PythonGateway(PythonProtocol):
    """Environment interrogation using sysconfig and astroid."""

    def __init__(self) -> None:
        self._stdlib_path = sysconfig.get_path("stdlib")

    def is_stdlib_module(self, module_name: str) -> bool:
        """Dynamic detection of StdLib modules using sys.stdlib_module_names and environment paths."""
        if not module_name:
            return False
        if module_name == "builtins":
            return True

        # 1. Check against the authoritative list (Python 3.10+)
        if hasattr(sys, "stdlib_module_names"):
            if module_name in sys.stdlib_module_names:
                return True
        # Fallback for older python, though Excelsior targets modern stacks
        elif module_name in sys.builtin_module_names:
            return True

        # 2. Check path location for bundled modules that might not be in the set
        try:
            module_node = astroid.MANAGER.ast_from_module_name(module_name)
            if hasattr(module_node, "file") and module_node.file:
                mod_file = str(module_node.file)
                # If it's in the stdlib directory and NOT in site-packages
                if mod_file.startswith(self._stdlib_path) and "site-packages" not in mod_file:
                    return True
        except (astroid.AstroidBuildingError, AttributeError):
            pass

        return False

    def is_external_dependency(self, file_path: Optional[str]) -> bool:
        """Check if a file resides in site-packages (Infrastructure)."""
        if not file_path:
            return False
        # Universal heuristics for installed packages
        return "site-packages" in file_path or "dist-packages" in file_path or ".venv" in file_path

    def is_exception_node(self, node: astroid.nodes.ClassDef) -> bool:
        """Check if class inherits from builtins.Exception."""
        try:
            for ancestor in node.ancestors():
                if ancestor.qname() == "builtins.Exception":
                    return True
        except (AttributeError, astroid.InferenceError):
            pass
        return False

    def is_protocol_node(self, node: astroid.nodes.ClassDef) -> bool:
        """Check if class inherits from typing.Protocol."""
        if not node.bases:
            return False
        try:
            # Quick check on bases first
            for base in node.bases:
                if hasattr(base, "name") and "Protocol" in base.name:
                    return True

            # Deep check
            for ancestor in node.ancestors():
                if ancestor.qname() in ("typing.Protocol", "typing_extensions.Protocol"):
                    return True
        except (AttributeError, astroid.InferenceError):
            pass
        return False



    def get_node_layer(self, node: astroid.nodes.NodeNG, config_loader: "ConfigurationLoader") -> Optional[str]:
        """Resolve architectural layer."""
        root = node.root()
        if not isinstance(root, astroid.nodes.Module):
            return None
        file_path = str(getattr(root, "file", ""))
        current_module = root.name
        return config_loader.get_layer_for_module(current_module, file_path)
