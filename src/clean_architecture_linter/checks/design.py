"""Design checks (W9007, W9009)."""

# AST checks often violate Demeter by design
import astroid  # type: ignore[import-untyped]
from pylint.checkers import BaseChecker

from clean_architecture_linter.config import ConfigurationLoader
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
        """W9009: Flag references to raw infrastructure types in UseCase layer."""
        root = node.root()
        file_path = getattr(root, "file", "")
        current_module = root.name
        layer = self.config_loader.get_layer_for_module(current_module, file_path)

        if layer not in (LayerRegistry.LAYER_USE_CASE,):
            return

        # Check assignment value type
        try:
            for inferred in node.value.infer():
                if inferred is astroid.Uninferable:
                    continue

                type_name = getattr(inferred, "name", "")
                # Check for raw types
                # Also flag any type ending in 'Client' (heuristic)
                if type_name in self.RAW_TYPES or (
                    type_name and type_name.endswith("Client")
                ):
                    self.add_message(
                        "missing-abstraction-violation",
                        node=node,
                        args=(node.targets[0].as_string(), type_name),
                    )
                    return

                # Also check ancestor classes (e.g. if it inherits from SnowflakeConnection)
                # This is more expensive but safer.
                if hasattr(inferred, "ancestors"):
                    for ancestor in inferred.ancestors():
                        if ancestor.name in self.RAW_TYPES:
                            self.add_message(
                                "missing-abstraction-violation",
                                node=node,
                                args=(node.targets[0].as_string(), ancestor.name),
                            )
                            return

        except astroid.InferenceError:
            pass

    def _get_type_name(self, node):
        if isinstance(node, astroid.nodes.Call):
            if hasattr(node.func, "name"):
                return node.func.name
            if hasattr(node.func, "attrname"):
                return node.func.attrname
        return getattr(node, "name", None)
