"""Design checks (W9007, W9009)."""

# AST checks often violate Demeter by design
import astroid  # type: ignore[import-untyped]
from pylint.checkers import BaseChecker
from clean_architecture_linter.config import ConfigurationLoader
from clean_architecture_linter.helpers import get_call_name
from clean_architecture_linter.layer_registry import LayerRegistry


class DesignChecker(BaseChecker):
    """W9007, W9009: Design pattern enforcement."""

    name = "clean-arch-design"
    msgs = {
        "W9007": (
            "Naked Return: %s returned from Repository. Return Entity instead.",
            "naked-return-violation",
            "Repository methods must return Domain Entities, not raw I/O objects.",
        ),
        "W9009": (
            "Missing Abstraction: %s holds reference to %s. Use Domain Entity.",
            "missing-abstraction-violation",
            "Use Cases cannot hold references to infrastructure objects (*Client).",
        ),
    }

    RAW_TYPES = {"Cursor", "Session", "Response", "Engine", "Connection", "Result"}

    def __init__(self, linter=None):
        super().__init__(linter)
        self.config_loader = ConfigurationLoader()

    def visit_return(self, node):
        """W9007: Flag raw I/O object returns."""
        if not node.value:
            return

        type_name = self._get_type_name(node.value)
        if type_name in self.RAW_TYPES:
            self.add_message("naked-return-violation", node=node, args=(type_name,))

    def visit_assign(self, node):
        """W9009: Flag Client references in UseCase layer."""
        root = node.root()
        file_path = getattr(root, "file", "")
        current_module = self.linter.current_name
        layer = self.config_loader.get_layer_for_module(current_module, file_path)

        if layer not in (LayerRegistry.LAYER_USE_CASE,):
            return

        if not isinstance(node.value, astroid.nodes.Call):
            return

        for target in node.targets:
            if hasattr(target, "name") and "client" in target.name.lower():
                func_name = get_call_name(node.value)
                self.add_message(
                    "missing-abstraction-violation",
                    node=node,
                    args=(target.name, func_name or "unknown"),
                )

    def _get_type_name(self, node):
        if isinstance(node, astroid.nodes.Call):
            if hasattr(node.func, "name"):
                return node.func.name
            if hasattr(node.func, "attrname"):
                return node.func.attrname
        return getattr(node, "name", None)
