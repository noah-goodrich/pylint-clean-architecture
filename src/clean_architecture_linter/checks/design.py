"""Design checks (W9007, W9009, W9012, W9013, W9015, W9016)."""

from typing import TYPE_CHECKING, Optional, List, Set, Any, IO

import astroid  # type: ignore[import-untyped]
from pylint.checkers import BaseChecker

if TYPE_CHECKING:
    from pylint.lint import PyLinter

from clean_architecture_linter.config import ConfigurationLoader
from clean_architecture_linter.layer_registry import LayerRegistry
from clean_architecture_linter.di.container import ExcelsiorContainer
from clean_architecture_linter.domain.protocols import AstroidProtocol


class DesignChecker(BaseChecker):
    """Design pattern enforcement."""

    name = "clean-arch-design"

    def __init__(self, linter: "PyLinter") -> None:
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
                "Domain and UseCase layers must remain silent.",
            ),
            "W9015": (
                "Missing Type Hint: %s in %s signature. "
                "Clean Fix: Add explicit type hints to all parameters and the return value.",
                "missing-type-hint",
                "All function and method signatures must be fully type-hinted.",
            ),
            "W9016": (
                "Banned Any: Explicit use of 'Any' detected in %s. "
                "Clean Fix: Use specific astroid.nodes types or Domain Entities.",
                "banned-any-usage",
                "Engineering Excellence standards reject 'Any'.",
            ),
        }
        super().__init__(linter)
        self.config_loader = ConfigurationLoader()
        container = ExcelsiorContainer.get_instance()
        self._ast_gateway: AstroidProtocol = container.get("AstroidGateway")

    @property
    def raw_types(self) -> Set[str]:
        """Get combined set of default and configured raw types."""
        defaults: Set[str] = {"Cursor", "Session", "Response", "Engine", "Connection", "Result"}
        return defaults.union(self.config_loader.raw_types)

    @property
    def infrastructure_modules(self) -> Set[str]:
        """Get combined set of default and configured infrastructure modules."""
        defaults: Set[str] = {
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

    def visit_return(self, node: astroid.nodes.Return) -> None:
        """W9007: Flag raw I/O object returns."""
        if not node.value:
            return

        type_name = self._get_inferred_type_name(node.value)
        if type_name in self.raw_types:
            self.add_message("naked-return-violation", node=node, args=(type_name,))
            return

        if self._is_infrastructure_type(node.value) and type_name:
            self.add_message("naked-return-violation", node=node, args=(type_name,))

    def visit_assign(self, node: astroid.nodes.Assign) -> None:
        """W9009: Flag references to raw infrastructure types in UseCase layer."""
        root = node.root()
        file_path: str = getattr(root, "file", "")
        current_module = root.name
        layer = self.config_loader.get_layer_for_module(current_module, file_path)

        if layer != LayerRegistry.LAYER_USE_CASE:
            return

        self._check_assignment_value(node)

    def _check_assignment_value(self, node: astroid.nodes.Assign) -> None:
        """Helper to inspect assignment values."""
        try:
            for inferred in node.value.infer():
                if inferred is astroid.Uninferable:
                    continue

                type_name: str = getattr(inferred, "name", "")
                if type_name in self.raw_types or type_name.endswith("Client"):
                    self.add_message(
                        "missing-abstraction-violation",
                        node=node,
                        args=(node.targets[0].as_string(), type_name),
                    )
                    return

                if self._is_infrastructure_inferred(inferred):
                    self.add_message(
                        "missing-abstraction-violation",
                        node=node,
                        args=(node.targets[0].as_string(), type_name or "InfrastructureObject"),
                    )
                    return
        except astroid.InferenceError:
            pass

    def visit_functiondef(self, node: astroid.nodes.FunctionDef) -> None:
        """W9015 & W9016 check."""
        if not node.returns:
            self.add_message("missing-type-hint", node=node, args=("return type", node.name))

        self._check_parameters(node)
        self._check_for_any_in_signature(node)

    def _check_parameters(self, node: astroid.nodes.FunctionDef) -> None:
        """Verify each parameter has a hint."""
        args = node.args
        for i, arg in enumerate(args.args):
            if i == 0 and node.is_method() and arg.name in ("self", "cls"):
                continue

            has_hint = False
            if i < len(args.annotations) and args.annotations[i]:
                has_hint = True
            elif hasattr(arg, "annotation") and arg.annotation:
                has_hint = True

            if not has_hint:
                self.add_message("missing-type-hint", node=node, args=(f"parameter '{arg.name}'", node.name))

        # W9015: Check varargs
        if args.vararg and not args.varargannotation:
            self.add_message("missing-type-hint", node=node, args=(f"parameter '*{args.vararg}'", node.name))

        # W9015: Check kwargs
        if args.kwarg and not args.kwargannotation:
            self.add_message("missing-type-hint", node=node, args=(f"parameter '**{args.kwarg}'", node.name))

    def _check_for_any_in_signature(self, node: astroid.nodes.FunctionDef) -> None:
        """Recursively check for 'Any' in signature."""
        if node.returns:
            self._recursive_check_any(node.returns, f"return type of '{node.name}'")

        args = node.args
        for i, anno in enumerate(args.annotations):
            if anno:
                arg_name = args.args[i].name
                self._recursive_check_any(anno, f"parameter '{arg_name}'")

    def _recursive_check_any(self, node: astroid.nodes.NodeNG, context: str) -> None:
        """Logic for detecting 'Any' usage."""
        found_any = False
        if isinstance(node, astroid.nodes.Name) and node.name == "Any":
            found_any = True
        elif isinstance(node, astroid.nodes.Attribute) and node.attrname == "Any":
            found_any = True
        elif isinstance(node, astroid.nodes.Subscript):
            self._recursive_check_any(node.value, context)
            self._recursive_check_any(node.slice, context)
        elif isinstance(node, astroid.nodes.Tuple):
            for elt in node.elts:
                self._recursive_check_any(elt, context)

        if found_any and not self._is_exempted(node):
            self.add_message("banned-any-usage", node=node, args=(context,))

    def _is_exempted(self, node: astroid.nodes.NodeNG) -> bool:
        """Check for noqa and justification."""
        try:
            root: astroid.nodes.Module = node.root()
            if hasattr(root, "stream"):
                stream: IO[bytes] = root.stream()
                if stream:
                    lines: List[bytes] = stream.readlines()
                    line_bytes: bytes = lines[node.lineno - 1]
                    line_str: str = line_bytes.decode("utf-8")
                    return "noqa: W9016" in line_str and "JUSTIFICATION:" in line_str.upper()
        except (AttributeError, IndexError, IOError):
            pass
        return False

    def visit_if(self, node: astroid.nodes.If) -> None:
        """W9012: Defensive None check detection."""
        root = node.root()
        file_path: str = getattr(root, "file", "")
        layer = self.config_loader.get_layer_for_module(root.name, file_path)

        if layer not in (LayerRegistry.LAYER_USE_CASE, LayerRegistry.LAYER_DOMAIN):
            return

        var_name = self._match_none_check(node.test)
        if var_name and any(isinstance(stmt, astroid.nodes.Raise) for stmt in node.body):
            self.add_message("defensive-none-check", node=node, args=(var_name, layer))

    def _match_none_check(self, test: astroid.nodes.NodeNG) -> Optional[str]:
        """Match 'x is None' or 'not x' patterns."""
        if isinstance(test, astroid.nodes.Compare) and len(test.ops) == 1:
            op, comparator = test.ops[0]
            if op in ("is", "is not") and isinstance(comparator, astroid.nodes.Const) and comparator.value is None:
                if isinstance(test.left, astroid.nodes.Name):
                    return str(test.left.name)

        if isinstance(test, astroid.nodes.UnaryOp) and test.op == "not":
            if isinstance(test.operand, astroid.nodes.Name):
                return str(test.operand.name)
        return None

    def _get_inferred_type_name(self, node: astroid.nodes.NodeNG) -> Optional[str]:
        """Heuristic type name discovery."""
        qname: Optional[str] = self._ast_gateway.get_node_return_type_qname(node)
        if not qname:
            # Fallback for uninferable calls in tests/simple code
            if isinstance(node, astroid.nodes.Call):
                if isinstance(node.func, astroid.nodes.Name):
                    return node.func.name
                if isinstance(node.func, astroid.nodes.Attribute):
                    return node.func.attrname
            return None
        parts = qname.split(".")
        return parts[-1]

    def _is_infrastructure_type(self, node: astroid.nodes.NodeNG) -> bool:
        """Check if node belongs to infrastructure."""
        try:
            for inferred in node.infer():
                if self._is_infrastructure_inferred(inferred):
                    return True
        except astroid.InferenceError:
            pass
        return False

    def _is_infrastructure_inferred(self, inferred: object) -> bool:
        """Deeper inference check for infrastructure origin."""
        if inferred is astroid.Uninferable:
            return False

        if not hasattr(inferred, "root"):
            return False

        root = inferred.root()
        if not hasattr(root, "name"):
            return False

        root_name: str = root.name
        for infra_mod in self.infrastructure_modules:
            if root_name == infra_mod or root_name.startswith(infra_mod + "."):
                return True
        return False
