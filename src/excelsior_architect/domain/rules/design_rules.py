"""Design rules (W9007, W9009, W9012, W9015, W9016)."""

from typing import IO, TYPE_CHECKING

import astroid

from excelsior_architect.domain.layer_registry import LayerRegistry
from excelsior_architect.domain.rules import Violation

if TYPE_CHECKING:
    from excelsior_architect.domain.config import ConfigurationLoader
    from excelsior_architect.domain.protocols import AstroidProtocol


class DesignRule:
    """Rule for W9007 (raw I/O return), W9009 (raw infra in UseCase), W9012 (defensive None), W9015 (type hints), W9016 (Any)."""

    code_raw_return: str = "W9007"
    code_raw_assign: str = "W9009"
    code_defensive_none: str = "W9012"
    code_missing_hint: str = "W9015"
    code_any_hint: str = "W9016"
    description: str = "Design: raw I/O, infra in UseCase, defensive None, type hints, Any."
    fix_type: str = "code"

    def __init__(
        self,
        config_loader: "ConfigurationLoader",
        ast_gateway: "AstroidProtocol",
    ) -> None:
        self._config_loader = config_loader
        self._ast_gateway = ast_gateway

    @property
    def raw_types(self) -> set[str]:
        defaults: set[str] = {"Cursor", "Session",
                              "Response", "Engine", "Connection", "Result"}
        return defaults.union(self._config_loader.raw_types)

    @property
    def infrastructure_modules(self) -> set[str]:
        defaults: set[str] = {
            "sqlalchemy", "requests", "psycopg2", "boto3", "redis",
            "pymongo", "httpx", "aiohttp", "urllib3",
        }
        return defaults.union(self._config_loader.infrastructure_modules)

    def check_return(self, node: astroid.nodes.Return) -> list[Violation]:
        """W9007: Flag raw I/O object returns."""
        violations: list[Violation] = []
        value = getattr(node, "value", None)
        if not value:
            return violations
        type_name = self._get_inferred_type_name(value)
        if type_name in self.raw_types:
            violations.append(
                Violation.from_node(
                    code=self.code_raw_return,
                    message=f"Raw I/O return: {type_name}",
                    node=node,
                    message_args=(type_name,),
                )
            )
            return violations
        if value and self._is_infrastructure_type(value) and type_name:
            violations.append(
                Violation.from_node(
                    code=self.code_raw_return,
                    message=f"Raw I/O return: {type_name}",
                    node=node,
                    message_args=(type_name,),
                )
            )
        return violations

    def check_assign(self, node: astroid.nodes.Assign) -> list[Violation]:
        """W9009: Flag raw infrastructure types in UseCase layer."""
        violations: list[Violation] = []
        root = node.root()
        file_path: str = getattr(root, "file", "") or ""
        current_module = getattr(root, "name", "")
        layer = self._config_loader.get_layer_for_module(
            current_module, file_path)
        if layer != LayerRegistry.LAYER_USE_CASE:
            return violations
        for v in self._check_assignment_value(node):
            violations.append(v)
        return violations

    def _check_assignment_value(self, node: astroid.nodes.Assign) -> list[Violation]:
        violations: list[Violation] = []
        try:
            node_value = node.value
            for inferred in node_value.infer():
                if inferred is astroid.Uninferable:
                    continue
                type_name: str = getattr(inferred, "name", "") or ""
                if type_name in self.raw_types or type_name.endswith("Client"):
                    target_str = ""
                    if node.targets and hasattr(node.targets[0], "as_string"):
                        target_str = node.targets[0].as_string()
                    violations.append(
                        Violation.from_node(
                            code=self.code_raw_assign,
                            message=f"Raw infrastructure in UseCase: {target_str} -> {type_name}",
                            node=node,
                            message_args=(target_str, type_name),
                        )
                    )
                    return violations
                if self._is_infrastructure_inferred(inferred):
                    target_str = ""
                    if node.targets and hasattr(node.targets[0], "as_string"):
                        target_str = node.targets[0].as_string()
                    violations.append(
                        Violation.from_node(
                            code=self.code_raw_assign,
                            message=f"Raw infrastructure in UseCase: {target_str} -> {type_name or 'InfrastructureObject'}",
                            node=node,
                            message_args=(
                                target_str, type_name or "InfrastructureObject"),
                        )
                    )
                    return violations
        except astroid.InferenceError:
            pass
        return violations

    def check_functiondef(self, node: astroid.nodes.FunctionDef) -> list[Violation]:
        """W9015 (missing hints), W9016 (Any in signature)."""
        violations: list[Violation] = []
        # Type narrowing: node is already FunctionDef
        if not node.returns:
            violations.append(
                Violation.from_node(
                    code=self.code_missing_hint,
                    message=f"Missing return type for '{node.name}'",
                    node=node,
                    message_args=("return type", node.name),
                )
            )
        for v in self._check_parameters(node):
            violations.append(v)
        for v in self._check_for_any_in_signature(node):
            violations.append(v)
        return violations

    def _check_parameters(self, node: astroid.nodes.FunctionDef) -> list[Violation]:
        violations: list[Violation] = []
        args = getattr(node, "args", None)
        if not args:
            return violations
        for i, arg in enumerate(args.args):
            if i == 0 and getattr(node, "is_method", lambda: False)() and getattr(arg, "name", "") in ("self", "cls"):
                continue
            has_hint = False
            if (i < len(args.annotations) and args.annotations[i]) or (getattr(arg, "annotation", None)):
                has_hint = True
            if not has_hint:
                violations.append(
                    Violation.from_node(
                        code=self.code_missing_hint,
                        message=f"Missing type hint for parameter '{arg.name}'",
                        node=node,
                        message_args=(f"parameter '{arg.name}'", node.name),
                    )
                )
        if getattr(args, "vararg", None) and not getattr(args, "varargannotation", None):
            violations.append(
                Violation.from_node(
                    code=self.code_missing_hint,
                    message=f"Missing type hint for *{args.vararg}",
                    node=node,
                    message_args=(f"parameter '*{args.vararg}'", node.name),
                )
            )
        if getattr(args, "kwarg", None) and not getattr(args, "kwargannotation", None):
            violations.append(
                Violation.from_node(
                    code=self.code_missing_hint,
                    message=f"Missing type hint for **{args.kwarg}",
                    node=node,
                    message_args=(f"parameter '**{args.kwarg}'", node.name),
                )
            )
        return violations

    def _check_for_any_in_signature(self, node: astroid.nodes.FunctionDef) -> list[Violation]:
        violations: list[Violation] = []
        if node.returns:
            for v in self._recursive_check_any(node.returns, f"return type of '{node.name}'"):
                violations.append(v)
        args = getattr(node, "args", None)
        if args and getattr(args, "annotations", None):
            for i, anno in enumerate(args.annotations):
                if anno and i < len(args.args):
                    arg_name = args.args[i].name
                    for v in self._recursive_check_any(anno, f"parameter '{arg_name}'"):
                        violations.append(v)
        return violations

    def _recursive_check_any(self, node: astroid.nodes.NodeNG, context: str) -> list[Violation]:
        violations: list[Violation] = []
        found_any = False
        if (isinstance(node, astroid.nodes.Name) and getattr(node, "name", None) == "Any") or (isinstance(node, astroid.nodes.Attribute) and getattr(node, "attrname", None) == "Any"):
            found_any = True
        elif isinstance(node, astroid.nodes.Subscript):
            violations.extend(self._recursive_check_any(node.value, context))
            violations.extend(self._recursive_check_any(node.slice, context))
        elif isinstance(node, astroid.nodes.Tuple):
            for elt in getattr(node, "elts", []):
                violations.extend(self._recursive_check_any(elt, context))
        if found_any and not self._is_exempted(node):
            violations.append(
                Violation.from_node(
                    code=self.code_any_hint,
                    message=f"Banned Any type: {context}",
                    node=node,
                    message_args=(context,),
                )
            )
        return violations

    def _is_exempted(self, node: astroid.nodes.NodeNG) -> bool:
        try:
            root = node.root()
            if hasattr(root, "stream"):
                stream: IO[bytes] = root.stream()
                if stream:
                    lines = stream.readlines()
                    line_bytes = lines[getattr(node, "lineno", 1) - 1]
                    line_str = line_bytes.decode("utf-8")
                    return "noqa: W9016" in line_str and "JUSTIFICATION:" in line_str.upper()
        except (OSError, AttributeError, IndexError, TypeError):
            pass
        return False

    def check_if(self, node: astroid.nodes.If) -> list[Violation]:
        """W9012: Defensive None check in UseCase/Domain."""
        violations: list[Violation] = []
        root = node.root()
        file_path = getattr(root, "file", "") or ""
        layer = self._config_loader.get_layer_for_module(
            getattr(root, "name", ""), file_path)
        if layer not in (LayerRegistry.LAYER_USE_CASE, LayerRegistry.LAYER_DOMAIN):
            return violations
        var_name = self._match_none_check(getattr(node, "test", None))
        if var_name and any(isinstance(stmt, astroid.nodes.Raise) for stmt in getattr(node, "body", [])):
            violations.append(
                Violation.from_node(
                    code=self.code_defensive_none,
                    message=f"Defensive None check: {var_name} in {layer}",
                    node=node,
                    message_args=(var_name, layer),
                )
            )
        return violations

    def _match_none_check(self, test: astroid.nodes.NodeNG | None) -> str | None:
        if test is None:
            return None
        if isinstance(test, astroid.nodes.Compare):
            test_ops = test.ops
            if len(test_ops) == 1:
                op, comparator = test_ops[0]
                if op in ("is", "is not") and isinstance(comparator, astroid.nodes.Const) and comparator.value is None:
                    test_left = test.left
                    if isinstance(test_left, astroid.nodes.Name):
                        return str(test_left.name)
        if isinstance(test, astroid.nodes.UnaryOp) and test.op == "not":
            test_operand = test.operand
            if isinstance(test_operand, astroid.nodes.Name):
                return str(test_operand.name)
        return None

    def _get_inferred_type_name(self, node: astroid.nodes.NodeNG) -> str | None:
        qname = self._ast_gateway.get_node_return_type_qname(node)
        if not qname:
            if isinstance(node, astroid.nodes.Call):
                func = getattr(node, "func", None)
                if isinstance(func, astroid.nodes.Name):
                    return str(getattr(func, "name", ""))
                if isinstance(func, astroid.nodes.Attribute):
                    return str(getattr(func, "attrname", ""))
            return None
        parts = qname.split(".")
        return str(parts[-1]) if parts else None

    def _is_infrastructure_type(self, node: astroid.nodes.NodeNG) -> bool:
        try:
            for inferred in node.infer():
                if self._is_infrastructure_inferred(inferred):
                    return True
        except astroid.InferenceError:
            pass
        return False

    def _is_infrastructure_inferred(self, inferred: object) -> bool:
        if inferred is astroid.Uninferable:
            return False
        if not hasattr(inferred, "root"):
            return False
        root = inferred.root()
        if not hasattr(root, "name"):
            return False
        root_name = str(getattr(root, "name", ""))
        for infra_mod in self.infrastructure_modules:
            if root_name == infra_mod or root_name.startswith(infra_mod + "."):
                return True
        return False
