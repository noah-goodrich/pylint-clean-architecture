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
            "Naked Return: %s returned from Repository. Return Entity instead. Clean Fix: Map the raw object to a "
            "Domain Entity before returning.",
            "naked-return-violation",
            "Repository methods must return Domain Entities, not raw I/O objects.",
        ),
        "W9009": (
            "Missing Abstraction: %s holds reference to %s. Use Domain Entity. Clean Fix: Replace the raw object "
            "with a Domain Entity or Value Object.",
            "missing-abstraction-violation",
            "Use Cases cannot hold references to infrastructure objects (*Client).",
        ),
    }

    def __init__(self, linter=None):
        super().__init__(linter)
        self.config_loader = ConfigurationLoader()

    @property
    def raw_types(self):
        """Get combined set of default and configured raw types."""
        defaults = {"Cursor", "Session", "Response", "Engine", "Connection", "Result"}
        return defaults.union(self.config_loader.raw_types)

    @property
    def infrastructure_modules(self):
        """Get combined set of default and configured infrastructure modules."""
        defaults = {
            "sqlalchemy",
            "requests",
            "psycopg2",
            "boto3",
            "redis",
            "pymongo",
            "httpx",
            "aiohttp",
            "urllib3",
        }
        return defaults.union(self.config_loader.infrastructure_modules)

    def visit_return(self, node):
        """W9007: Flag raw I/O object returns."""
        if not node.value:
            return

        type_name = self._get_inferred_type_name(node.value)
        if type_name in self.raw_types:
            self.add_message("naked-return-violation", node=node, args=(type_name,))
            return

        # Check infrastructure module origin
        if self._is_infrastructure_type(node.value):
            if type_name:
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

                # Check for raw types by name (heuristic)
                if type_name in self.raw_types or (type_name and type_name.endswith("Client")):
                    self.add_message(
                        "missing-abstraction-violation",
                        node=node,
                        args=(node.targets[0].as_string(), type_name),
                    )
                    return

                # Check for infrastructure module origin (precise)
                if self._is_infrastructure_inferred(inferred):
                    self.add_message(
                        "missing-abstraction-violation",
                        node=node,
                        args=(
                            node.targets[0].as_string(),
                            type_name or "InfrastructureObject",
                        ),
                    )
                    return

        except astroid.InferenceError:
            pass

    def _get_inferred_type_name(self, node):
        """Get type name via inference if possible, else fallback to name."""
        try:
            for inferred in node.infer():
                if inferred is not astroid.Uninferable:
                    return getattr(inferred, "name", None)
        except astroid.InferenceError:
            pass

        # Fallback to simple name analysis
        if isinstance(node, astroid.nodes.Call):
            if hasattr(node.func, "name"):
                return node.func.name
            if hasattr(node.func, "attrname"):
                return node.func.attrname
        return getattr(node, "name", None)

    def _is_infrastructure_type(self, node):
        """Check if node infers to a type defined in an infrastructure module."""
        try:
            for inferred in node.infer():
                if self._is_infrastructure_inferred(inferred):
                    return True
        except astroid.InferenceError:
            pass
        return False

    def _is_infrastructure_inferred(self, inferred):
        """Check if an inferred node defines comes from infrastructure module."""
        if inferred is astroid.Uninferable:
            return False

        # Check root module
        root = inferred.root()
        if hasattr(root, "name"):
            root_name = root.name
            for infra_mod in self.infrastructure_modules:
                if root_name == infra_mod or root_name.startswith(infra_mod + "."):
                    return True

        # Check ancestors
        if hasattr(inferred, "ancestors"):
            for ancestor in inferred.ancestors():
                # Checking ancestor names (heuristic)
                if ancestor.name in self.raw_types:
                    return True

                # Checking ancestor module definitions (precise)
                ancestor_root = ancestor.root()
                if hasattr(ancestor_root, "name"):
                    anc_root_name = ancestor_root.name
                    for infra_mod in self.infrastructure_modules:
                        if anc_root_name == infra_mod or anc_root_name.startswith(infra_mod + "."):
                            return True
        return False
