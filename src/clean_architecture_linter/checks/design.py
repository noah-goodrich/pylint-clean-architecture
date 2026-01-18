"""Design checks (W9007, W9009, W9012)."""

# AST checks often violate Demeter by design

import astroid  # type: ignore[import-untyped]
from pylint.checkers import BaseChecker

from clean_architecture_linter.config import ConfigurationLoader
from clean_architecture_linter.layer_registry import LayerRegistry


class DesignChecker(BaseChecker):
    """W9007, W9009, W9012: Design pattern enforcement."""

    name = "clean-arch-design"

    def __init__(self, linter=None):
        self.msgs = {
            "W9012": (
                "Defensive None Check: '%s' checked for None in %s layer. Validation belongs in Interface layer. "
                "Clean Fix: Ensure the value is validated before entering core logic.",
                "defensive-none-check",
                "Defensive 'if var is None' checks bloat logic and bypass boundary logic separation.",
            ),
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
            "W9013": (
                "Illegal I/O Operation: '%s' called in silent layer '%s'. "
                "Clean Fix: Delegate I/O to an Interface/Port (e.g., %s).",
                "illegal-io-operation",
                "Domain and UseCase layers must remain silent (no print, logging, or direct console I/O).",
            ),
            "W9014": (
                "Telemetry Template Drift: %s is missing or has incorrect __stellar_version__. Expected '1.1.1'. "
                "Clean Fix: Update telemetry.py to match the unified Fleet stabilizer template.",
                "template-drift-check",
                "Ensures all telemetry adapters follow the standardized version for Fleet stabilization.",
            ),
        }
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
        if self._is_infrastructure_type(node.value) and type_name:
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

    def visit_if(self, node: astroid.nodes.If) -> None:
        """W9012: Visit if statement to find defensive None checks."""
        root = node.root()
        file_path = getattr(root, "file", "")
        current_module = root.name
        layer = self.config_loader.get_layer_for_module(current_module, file_path)

        # Only check UseCase and Domain
        if layer not in (LayerRegistry.LAYER_USE_CASE, LayerRegistry.LAYER_DOMAIN):
            return

        var_name = self._match_none_check(node.test)
        if not var_name:
            return

        # Check if the body contains a raise statement (heuristic for "defensive")
        has_raise = any(isinstance(stmt, astroid.nodes.Raise) for stmt in node.body)

        if has_raise:
            self.add_message("defensive-none-check", node=node, args=(var_name, layer))

    def visit_module(self, node: astroid.nodes.Module) -> None:
        """W9014: Check for template drift in telemetry.py."""
        if not node.file or not node.file.endswith("telemetry.py"):
            return

        expected_version = "1.1.1"
        found_version = None

        # Look for __stellar_version__ = "1.0.0"
        for child in node.body:
            if (
                isinstance(child, astroid.nodes.Assign)
                and any(getattr(target, "name", "") == "__stellar_version__" for target in child.targets)
                and isinstance(child.value, astroid.nodes.Const)
            ):
                found_version = child.value.value
                break

        if found_version != expected_version:
            self.add_message("template-drift-check", node=node, args=(node.name,))

    def visit_call(self, node: astroid.nodes.Call) -> None:
        """W9013: Flag illegal I/O operations in silent layers."""
        root = node.root()
        file_path = getattr(root, "file", "")
        current_module = root.name
        layer = self.config_loader.get_layer_for_module(current_module, file_path)

        if layer not in self.config_loader.silent_layers:
            return

        func_name = ""
        is_method_call = False
        caller_name = ""

        if isinstance(node.func, astroid.nodes.Name):
            func_name = node.func.name
        elif isinstance(node.func, astroid.nodes.Attribute):
            func_name = node.func.attrname
            is_method_call = True
            if isinstance(node.func.expr, astroid.nodes.Name):
                caller_name = node.func.expr.name

        # 1. Check for print()
        if func_name == "print" and not is_method_call:
            self._add_io_violation(node, "print()", layer)
            return

        # 2. Check for logging functions
        logging_funcs = {
            "info",
            "error",
            "debug",
            "warning",
            "critical",
            "log",
            "exception",
        }
        if func_name in logging_funcs and caller_name in ("logging", "logger", "log") and not self._is_exempt_io(node):
            self._add_io_violation(node, f"{caller_name}.{func_name}()", layer)
            return

        # 3. Check for rich
        if (
            caller_name == "rich" or (isinstance(node.func, astroid.nodes.Attribute) and "rich" in str(node.func.expr))
        ) and func_name in ("print", "inspect", "Console"):
            self._add_io_violation(node, f"rich.{func_name}", layer)
            return

    def _is_exempt_io(self, node: astroid.nodes.Call) -> bool:
        """Check if the I/O call is made on an allowed interface."""
        if not isinstance(node.func, astroid.nodes.Attribute):
            return False

        allowed = self.config_loader.allowed_io_interfaces

        # Check by variable name (heuristic)
        if isinstance(node.func.expr, astroid.nodes.Name) and node.func.expr.name in allowed:
            return True

        # Check by inferred type (precise)
        try:
            for inferred in node.func.expr.infer():
                if inferred is astroid.Uninferable:
                    continue
                if getattr(inferred, "name", "") in allowed:
                    return True
                # Check ancestors
                if hasattr(inferred, "ancestors"):
                    for ancestor in inferred.ancestors():
                        if ancestor.name in allowed:
                            return True
        except astroid.InferenceError:
            pass

        return False

    def _add_io_violation(self, node, operation, layer):
        """Add W9013 message."""
        allowed_hint = ", ".join(list(self.config_loader.allowed_io_interfaces)[:2])
        self.add_message("illegal-io-operation", node=node, args=(operation, layer, allowed_hint))

    def _match_none_check(self, test: astroid.nodes.NodeNG) -> str | None:
        """Match 'var is None', 'var is not None', or 'not var'."""
        # Pattern 1: if var is None (astroid.Compare)
        if isinstance(test, astroid.nodes.Compare) and len(test.ops) == 1 and test.ops[0][0] in ("is", "is not"):
            _op, comparator = test.ops[0]
            if (
                isinstance(comparator, astroid.nodes.Const)
                and comparator.value is None
                and isinstance(test.left, astroid.nodes.Name)
            ):
                return test.left.name

        if (
            isinstance(test, astroid.nodes.UnaryOp)
            and test.op == "not"
            and isinstance(test.operand, astroid.nodes.Name)
        ):
            return test.operand.name

        return None

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

    def _is_infrastructure_inferred(self, inferred) -> bool:
        """Check if an inferred node defines comes from infrastructure module."""
        if inferred is astroid.Uninferable:
            return False

        # 1. Check root module
        if self._is_infra_root(inferred.root()):
            return True

        # 2. Check ancestors
        return self._has_infra_ancestor(inferred)

    def _is_infra_root(self, root) -> bool:
        """Check if root module is in infrastructure list."""
        if not hasattr(root, "name"):
            return False
        root_name = root.name
        for infra_mod in self.infrastructure_modules:
            if root_name == infra_mod or root_name.startswith(infra_mod + "."):
                return True
        return False

    def _has_infra_ancestor(self, inferred) -> bool:
        """Check if any ancestor comes from infrastructure."""
        if not hasattr(inferred, "ancestors"):
            return False
        for ancestor in inferred.ancestors():
            # Checking ancestor names (heuristic)
            if ancestor.name in self.raw_types:
                return True

            # Checking ancestor module definitions (precise)
            if self._is_infra_root(ancestor.root()):
                return True
        return False
