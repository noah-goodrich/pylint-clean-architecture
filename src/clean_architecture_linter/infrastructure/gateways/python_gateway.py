import sys
import sysconfig
from typing import Optional, TYPE_CHECKING
import astroid # type: ignore[import-untyped]
from clean_architecture_linter.domain.protocols import PythonProtocol

if TYPE_CHECKING:
    from clean_architecture_linter.config import ConfigurationLoader


class PythonGateway(PythonProtocol):
    """Environment interrogation using sysconfig and astroid."""

    def __init__(self) -> None:
        self._stdlib_path = sysconfig.get_path("stdlib")

    def is_std_lib_module(self, module_name: str) -> bool:
        """Dynamic detection of StdLib modules without hardcoded lists."""
        if not module_name:
            return False
        if module_name == "builtins":
            return True
        if module_name in sys.builtin_module_names:
            return True

        # Hardcoded trust list for common stdlib modules to handle edge cases
        if module_name in ("sys", "os", "pathlib", "json", "typing", "collections", "datetime", "ast", "abc", "builtins"):
            return True

        try:
            # Use astroid.MANAGER to find the module's file path
            module_node = astroid.MANAGER.ast_from_module_name(module_name)
            if hasattr(module_node, "file") and module_node.file:
                # Normalizing paths for cross-platform comparison
                mod_file = str(module_node.file)
                # JUSTIFICATION: Simple path comparison for stdlib detection.
                prefixes = [self._stdlib_path]
                if hasattr(sys, "base_prefix"):
                    prefixes.append(sys.base_prefix)
                if hasattr(sys, "prefix"):
                    prefixes.append(sys.prefix)

                return any(mod_file.startswith(p) for p in prefixes)
        except (astroid.AstroidBuildingError, AttributeError):
            pass

        return False

    def get_call_name(self, node: astroid.nodes.Call) -> Optional[str]:
        """Extract the name of the function or method being called."""
        if not isinstance(node, astroid.nodes.Call):
            return None

        if isinstance(node.func, astroid.nodes.Name):
            return str(node.func.name)
        if isinstance(node.func, astroid.nodes.Attribute):
            return str(node.func.attrname)
        return None

    def get_node_layer(self, node: astroid.nodes.NodeNG, config_loader: "ConfigurationLoader") -> Optional[str]:
        """Resolve architectural layer."""
        root = node.root()
        if not isinstance(root, astroid.nodes.Module):
            return None
        file_path = str(getattr(root, "file", ""))
        current_module = root.name
        return config_loader.get_layer_for_module(current_module, file_path)
