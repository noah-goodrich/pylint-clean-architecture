"""Law of Demeter rules (W9006, W9019)."""

from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, cast

import astroid

from excelsior_architect.domain.rules import Violation

if TYPE_CHECKING:
    from excelsior_architect.domain.config import ConfigurationLoader
    from excelsior_architect.domain.protocols import (
        AstroidProtocol,
        PythonProtocol,
        StubAuthorityProtocol,
    )

_MIN_CHAIN_LENGTH: int = 2
_MAX_SELF_CHAIN_LENGTH: int = 2


class LawOfDemeterRule:
    """Rule for W9006 (Law of Demeter), W9019 (unstable dependency). Stateful."""

    code_demeter: str = "W9006"
    code_unstable: str = "W9019"
    description: str = "Law of Demeter: avoid chained calls and stranger methods."
    fix_type: str = "comment"

    _NODE_MODULE_RESOLVERS: ClassVar[dict[type, str]] = {
        astroid.nodes.Call: "_module_from_call",
        astroid.nodes.Name: "_module_from_name",
    }

    def __init__(
        self,
        ast_gateway: "AstroidProtocol",
        python_gateway: "PythonProtocol",
        stub_resolver: "StubAuthorityProtocol",
        config_loader: "ConfigurationLoader",
    ) -> None:
        self._ast_gateway = ast_gateway
        self._python_gateway = python_gateway
        self._stub_resolver = stub_resolver
        self._config_loader = config_loader

    def record_assign(
        self, node: astroid.nodes.NodeNG, locals_map: dict[str, bool]
    ) -> None:
        """Track if a local variable is created from a method call (likely a stranger)."""
        if not hasattr(node, "value") or not isinstance(
            getattr(node, "value", None), astroid.nodes.Call
        ):
            return
        call_val = node.value
        if self._ast_gateway.is_trusted_authority_call(call_val):
            return
        return_qname = self._ast_gateway.get_return_type_qname_from_expr(
            call_val)
        if return_qname and self._ast_gateway.is_primitive(return_qname):
            return
        func = getattr(call_val, "func", None)
        if isinstance(func, astroid.nodes.Attribute):
            receiver_qname = self._ast_gateway.get_return_type_qname_from_expr(
                func.expr
            )
            if receiver_qname and self._ast_gateway.is_primitive(receiver_qname):
                return
        for target in getattr(node, "targets", []):
            if isinstance(target, astroid.nodes.AssignName):
                locals_map[target.name] = True

    def check_call(
        self, node: astroid.nodes.Call, locals_map: dict[str, bool]
    ) -> list[Violation]:
        """Check a Call for W9006/W9019. Returns list of violations (method chain or stranger)."""
        violations: list[Violation] = []
        if self._is_test_file(node):
            return violations
        chain_violations = self._check_method_chain(node)
        if chain_violations:
            return chain_violations
        stranger_violations = self._check_stranger_variable(node, locals_map)
        violations.extend(stranger_violations)
        return violations

    def _is_test_file(self, node: astroid.nodes.NodeNG) -> bool:
        root = node.root()
        file_path: str = getattr(root, "file", "") or ""
        if not file_path:
            return False
        if any(x in file_path.lower() for x in ("benchmark", "samples", "bait")):
            return False
        parts = file_path.split("/")
        filename = parts[-1] if parts else ""
        if "tests" in parts or filename.startswith("test_"):
            return not ("/tmp/" in file_path or "snowfort" in file_path)
        return False

    def _check_method_chain(self, node: astroid.nodes.Call) -> list[Violation]:
        if not isinstance(getattr(node, "func", None), astroid.nodes.Attribute):
            return []
        chain: list[str] = []
        curr: astroid.nodes.NodeNG = node.func
        while isinstance(curr, (astroid.nodes.Attribute, astroid.nodes.Call)):
            if isinstance(curr, astroid.nodes.Attribute):
                chain.append(curr.attrname)
                curr = curr.expr
            else:
                if curr != node:
                    chain.append("()")
                curr = curr.func
        if len(chain) < _MIN_CHAIN_LENGTH:
            return []
        receiver_qname = self._ast_gateway.get_return_type_qname_from_expr(
            curr)
        if receiver_qname is None:
            ext_mod = self._get_external_module_for_uninferable(curr)
            if ext_mod:
                project_root = self._get_project_root(node)
                if self._stub_resolver.get_stub_path(ext_mod, project_root) is None:
                    stub_path_arg = ext_mod.replace(".", "/")
                    return [
                        Violation.from_node(
                            code=self.code_unstable,
                            message=f"Uninferable dependency: create stubs/{stub_path_arg}.pyi",
                            node=node,
                            message_args=(ext_mod, stub_path_arg),
                        )
                    ]
        config_loader = self._config_loader
        if self._is_chain_excluded(node, chain, curr, config_loader):
            return []
        full_chain = ".".join(reversed(chain)).replace(".()", "()")
        return [
            Violation.from_node(
                code=self.code_demeter,
                message=f"Law of Demeter: {full_chain}",
                node=node,
                message_args=(full_chain,),
            )
        ]

    def _check_stranger_variable(
        self, node: astroid.nodes.Call, locals_map: dict[str, bool]
    ) -> list[Violation]:
        violations: list[Violation] = []
        func = getattr(node, "func", None)
        if not isinstance(func, astroid.nodes.Attribute):
            return violations
        expr = func.expr
        if not isinstance(expr, astroid.nodes.Name):
            return violations
        if not locals_map.get(expr.name, False):
            return violations
        var_qname = self._ast_gateway.get_return_type_qname_from_expr(expr)
        if var_qname and self._ast_gateway.is_primitive(var_qname):
            return violations
        if var_qname is None:
            ext_mod = self._get_external_module_for_uninferable(expr)
            if ext_mod:
                project_root = self._get_project_root(node)
                if self._stub_resolver.get_stub_path(ext_mod, project_root) is None:
                    stub_path_arg = ext_mod.replace(".", "/")
                    return [
                        Violation.from_node(
                            code=self.code_unstable,
                            message=f"Uninferable dependency: create stubs/{stub_path_arg}.pyi",
                            node=node,
                            message_args=(ext_mod, stub_path_arg),
                        )
                    ]
        if self._is_assigned_from_primitive_method(expr):
            return violations
        if self._is_assigned_from_container_get(expr):
            return violations
        if self._is_chain_excluded(node, [func.attrname], expr, self._config_loader):
            return violations
        msg_arg = f"{expr.name}.{func.attrname} (Stranger)"
        violations.append(
            Violation.from_node(
                code=self.code_demeter,
                message=f"Law of Demeter: {msg_arg}",
                node=node,
                message_args=(msg_arg,),
            )
        )
        return violations

    def _get_project_root(self, node: astroid.nodes.NodeNG) -> str | None:
        try:
            root = node.root()
            path = getattr(root, "file", None)
            if not path:
                return None
            current = Path(str(path)).resolve().parent
            while True:
                if (current / "pyproject.toml").exists():
                    return str(current)
                parent = current.parent
                if parent == current:
                    break
                current = parent
        except (AttributeError, OSError, TypeError):
            pass
        return None

    def _is_module_in_project(self, module_name: str) -> bool:
        config = self._config_loader
        layer_map = config.config.get("layer_map") or {}
        if not isinstance(layer_map, dict):
            return False
        tops = {k.split(".")[0] for k in layer_map if isinstance(k, str)}
        return any(
            module_name == t or module_name.startswith(t + ".")
            for t in tops
        )

    def _dotted_from_expr(self, expr: astroid.nodes.NodeNG) -> str | None:
        if isinstance(expr, astroid.nodes.Attribute):
            base = self._dotted_from_expr(expr.expr)
            return f"{base}.{expr.attrname}" if base else None
        if isinstance(expr, astroid.nodes.Name):
            try:
                stmts = expr.lookup(expr.name)[1]
            except (astroid.InferenceError, AttributeError):
                return None
            if not stmts:
                return None
            s = stmts[0]
            if isinstance(s, astroid.nodes.ImportFrom):
                return str(s.modname) if s.modname else None
            if isinstance(s, astroid.nodes.Import) and s.names:
                full, alias = s.names[0]
                return str(full) if alias else str(expr.name)
        return None

    def _module_from_call(self, call_node: astroid.nodes.Call) -> str | None:
        try:
            for inf in call_node.func.infer():
                if inf is astroid.Uninferable:
                    continue
                q = getattr(inf, "qname", None)
                if q is None:
                    continue
                qn = q() if callable(q) else q
                if isinstance(qn, str) and "." in qn:
                    return qn.rsplit(".", 1)[0]
        except (astroid.InferenceError, AttributeError):
            pass
        func = call_node.func
        if isinstance(func, astroid.nodes.Attribute):
            return self._dotted_from_expr(func.expr)
        if isinstance(func, astroid.nodes.Name):
            stmts: list[astroid.nodes.NodeNG] = getattr(
                func, "lookup", lambda _: ([], []))(func.name)[1]
            if stmts and isinstance(stmts[0], astroid.nodes.ImportFrom):
                return getattr(stmts[0], "modname", None) or None
        return None

    def _module_from_assign(
        self, parent: astroid.nodes.Assign, name: str
    ) -> str | None:
        for t in parent.targets:
            if isinstance(t, astroid.nodes.AssignName) and t.name == name:
                if isinstance(parent.value, astroid.nodes.Call):
                    return self._module_from_call(parent.value)
                if isinstance(
                    parent.value,
                    (astroid.nodes.Attribute, astroid.nodes.Name),
                ):
                    return self._dotted_from_expr(parent.value)
                break
        return None

    def _module_from_import(
        self, parent: astroid.nodes.Import, name: str
    ) -> str | None:
        for (full, alias) in parent.names:
            if (alias or (str(full).split(".")[0] if full else "")) == name:
                return str(full)
        if parent.names:
            full, alias = parent.names[0]
            return (
                str(full)
                if alias
                else (name if full and str(full).split(".")[0] == name else str(full))
            )
        return None

    def _module_from_name(self, name_node: astroid.nodes.Name) -> str | None:
        try:
            scope = name_node.scope()
        except (AttributeError, astroid.InferenceError):
            return None
        stmts: list[astroid.nodes.NodeNG] = name_node.lookup(name_node.name)[1]
        for def_node in stmts:
            try:
                if def_node.scope() != scope:
                    continue
            except (AttributeError, astroid.InferenceError):
                pass
            parent = getattr(def_node, "parent", None)
            if isinstance(parent, astroid.nodes.Assign) and parent.value:
                r = self._module_from_assign(parent, name_node.name)
                if r is not None:
                    return r
            elif isinstance(parent, astroid.nodes.ImportFrom):
                return getattr(parent, "modname", None) or None
            elif isinstance(parent, astroid.nodes.Import) and parent.names:
                return self._module_from_import(parent, name_node.name)
        return None

    def _get_external_module_for_uninferable(
        self, node: astroid.nodes.NodeNG
    ) -> str | None:
        mod: str | None = None
        for node_type, method_name in self._NODE_MODULE_RESOLVERS.items():
            if isinstance(node, node_type):
                mod = getattr(self, method_name)(node)
                break
        if not mod:
            return None
        top = mod.split(".")[0]
        if self._python_gateway.is_stdlib_module(top):
            return None
        if self._is_module_in_project(mod):
            return None
        return mod

    def _is_assigned_from_primitive_method(
        self, var_node: astroid.nodes.Name
    ) -> bool:
        func_node = var_node.frame()
        if not isinstance(func_node, astroid.nodes.FunctionDef):
            return False
        for assign_node in func_node.nodes_of_class(astroid.nodes.Assign):
            # Type narrowing: cast to help mypy understand the specific type
            assign = cast(astroid.nodes.Assign, assign_node)
            for target in assign.targets:
                if not (
                    isinstance(target, astroid.nodes.AssignName)
                    and target.name == var_node.name
                ):
                    continue
                assign_value = assign.value
                if not isinstance(assign_value, astroid.nodes.Call):
                    return False
                call_func = assign_value.func
                if isinstance(call_func, astroid.nodes.Attribute):
                    receiver_qname = self._ast_gateway.get_return_type_qname_from_expr(
                        call_func.expr
                    )
                    if receiver_qname and self._ast_gateway.is_primitive(
                        receiver_qname
                    ):
                        return True
                    func_expr = call_func.expr
                    if isinstance(
                        func_expr, astroid.nodes.Name
                    ) and self._has_isinstance_primitive_guard(
                        func_node,
                        func_expr.name,
                        assign.lineno,
                    ):
                        return True
        return False

    def _unwrap_not(self, test: astroid.nodes.NodeNG) -> astroid.nodes.NodeNG:
        if isinstance(test, astroid.nodes.UnaryOp) and test.op == "not":
            return test.operand
        return test

    def _isinstance_guard_var_primitive(
        self, test: astroid.nodes.Call, var_name: str
    ) -> bool:
        try:
            for inf in test.func.infer():
                if getattr(inf, "name", None) != "isinstance":
                    continue
                if len(test.args) < 2:
                    return False
                if not (
                    isinstance(test.args[0], astroid.nodes.Name)
                    and test.args[0].name == var_name
                ):
                    return False
                type_arg = test.args[1]
                for type_inf in type_arg.infer():
                    q = getattr(type_inf, "qname", None)
                    if q is None:
                        continue
                    type_qname = q() if callable(q) else q
                    if isinstance(
                        type_qname, str
                    ) and self._ast_gateway.is_primitive(type_qname):
                        return True
                return False
        except (astroid.InferenceError, AttributeError):
            pass
        return False

    def _has_isinstance_primitive_guard(
        self,
        func_node: astroid.nodes.FunctionDef,
        var_name: str,
        before_line: int,
    ) -> bool:
        for if_stmt in func_node.nodes_of_class(astroid.nodes.If):
            # Type narrowing: cast to help mypy understand the specific type
            if_node = cast(astroid.nodes.If, if_stmt)
            if if_node.lineno >= before_line:
                continue
            if_test = if_node.test
            test = self._unwrap_not(if_test)
            if isinstance(test, astroid.nodes.Call) and self._isinstance_guard_var_primitive(
                test, var_name
            ):
                return True
        return False

    def _is_assigned_from_container_get(
        self, var_node: astroid.nodes.Name
    ) -> bool:
        func_node = var_node.frame()
        if not isinstance(func_node, astroid.nodes.FunctionDef):
            return False
        for assign_node in func_node.nodes_of_class(astroid.nodes.Assign):
            # Type narrowing: cast to help mypy understand the specific type
            assign = cast(astroid.nodes.Assign, assign_node)
            for target in assign.targets:
                if not (
                    isinstance(target, astroid.nodes.AssignName)
                    and target.name == var_node.name
                ):
                    continue
                assign_value = assign.value
                if not isinstance(assign_value, astroid.nodes.Call):
                    return False
                call_func = assign_value.func
                if not isinstance(call_func, astroid.nodes.Attribute):
                    return False
                if call_func.attrname != "get":
                    return False
                container = call_func.expr
                if self._is_locally_instantiated(container):
                    return True
                return bool(isinstance(container, astroid.nodes.Name) and container.name == "self")
        return False

    def _is_chain_excluded(
        self,
        node: astroid.nodes.Call,
        chain: list[str],
        curr: astroid.nodes.NodeNG,
        config_loader: "ConfigurationLoader",
    ) -> bool:
        if self._excluded_by_environment_or_trust(node, curr, config_loader):
            return True
        if self._excluded_by_receiver_or_safe_source(
            node, curr, chain, config_loader
        ):
            return True
        return self._is_allowed_by_inference(curr, config_loader)

    def _excluded_by_environment_or_trust(
        self,
        node: astroid.nodes.Call,
        curr: astroid.nodes.NodeNG,
        config_loader: "ConfigurationLoader",
    ) -> bool:
        if self._is_test_file(node) or self._is_mock_involved(curr):
            return True
        if self._is_override_excluded(node, config_loader):
            return True
        if self._ast_gateway.is_trusted_authority_call(node):
            return True
        if isinstance(node.func, astroid.nodes.Attribute) and isinstance(
            node.func.expr, astroid.nodes.Call
        ) and self._ast_gateway.is_protocol_call(node.func.expr):
            return True
        return bool(self._ast_gateway.is_fluent_call(node))

    def _excluded_by_receiver_or_safe_source(
        self,
        node: astroid.nodes.Call,
        curr: astroid.nodes.NodeNG,
        chain: list[str],
        config_loader: "ConfigurationLoader",
    ) -> bool:
        if isinstance(node.func, astroid.nodes.Attribute) and self._is_primitive_receiver(node.func.expr):
            return True
        if self._is_safe_source(curr, config_loader):
            return True
        if self._is_self_or_cls(curr, chain):
            return True
        if self._is_locally_instantiated(curr):
            return True
        return bool(self._is_hinted_protocol(curr))

    def _is_primitive_receiver(self, receiver: astroid.nodes.NodeNG) -> bool:
        qname = self._ast_gateway.get_return_type_qname_from_expr(receiver)
        return bool(qname and self._ast_gateway.is_primitive(qname))

    def _is_self_or_cls(self, curr: astroid.nodes.NodeNG, chain: list[str]) -> bool:
        return (
            isinstance(curr, astroid.nodes.Name)
            and curr.name in ("self", "cls")
            and len(chain) <= _MAX_SELF_CHAIN_LENGTH
        )

    def _is_safe_source(
        self,
        receiver: astroid.nodes.NodeNG,
        config_loader: "ConfigurationLoader",
    ) -> bool:
        qname: str | None = self._ast_gateway.get_return_type_qname_from_expr(
            receiver
        )
        if qname:
            if self._ast_gateway.is_primitive(qname):
                return True
            if self._python_gateway.is_stdlib_module(qname.split(".")[0]):
                return True
        if isinstance(receiver, astroid.nodes.Name) and self._python_gateway.is_stdlib_module(receiver.name):
            return True
        return self._is_inferred_safe(receiver, config_loader)

    def _is_inferred_safe(
        self,
        receiver: astroid.nodes.NodeNG,
        config_loader: "ConfigurationLoader",
    ) -> bool:
        try:
            for inferred in receiver.infer():
                if inferred is astroid.Uninferable:
                    continue
                inf_qname: str = getattr(inferred, "qname", lambda: "")()
                if callable(inf_qname):
                    inf_qname = inf_qname()
                if self._check_mod_allowed(inf_qname, config_loader, ""):
                    return True
                root = getattr(inferred, "root", None)
                root_name: str = getattr(root(), "name", "") if root else ""
                if self._check_mod_allowed(root_name, config_loader, ""):
                    return True
        except (astroid.InferenceError, AttributeError, TypeError):
            pass
        return False

    def _check_mod_allowed(
        self,
        mod_name: str,
        config_loader: "ConfigurationLoader",
        file_path: str,
    ) -> bool:
        if not mod_name:
            return False
        if self._python_gateway.is_stdlib_module(mod_name.split(".")[0]):
            return True
        allowed = config_loader.allowed_lod_roots
        return any(mod_name == m or mod_name.startswith(m + ".") for m in allowed)

    def _is_override_excluded(
        self, node: astroid.nodes.Call, config_loader: "ConfigurationLoader"
    ) -> bool:
        try:
            if not isinstance(node.func, astroid.nodes.Attribute):
                return False
            for inferred in node.func.infer():
                if inferred is astroid.Uninferable:
                    continue
                qname = getattr(inferred, "qname", lambda: "")()
                if callable(qname):
                    qname = qname()
                if qname in config_loader.allowed_lod_methods:
                    return True
        except (astroid.InferenceError, AttributeError):
            pass
        return False

    def _is_allowed_by_inference(
        self,
        node: astroid.nodes.NodeNG,
        config_loader: "ConfigurationLoader",
    ) -> bool:
        qname: str | None = self._ast_gateway.get_return_type_qname_from_expr(
            node
        )
        if qname:
            if self._is_layer_allowed(qname, config_loader):
                return True
            if any(
                qname.startswith(root) for root in config_loader.allowed_lod_roots
            ):
                return True
        return False

    def _is_layer_allowed(
        self, module_name: str, config_loader: "ConfigurationLoader"
    ) -> bool:
        layer: str | None = config_loader.get_layer_for_module(module_name)
        return bool(layer and ("domain" in layer.lower() or "dto" in layer.lower()))

    def _is_locally_instantiated(self, node: astroid.nodes.NodeNG) -> bool:
        if not isinstance(node, astroid.nodes.Name):
            return False
        scope = node.scope()
        try:
            for def_node in node.lookup(node.name)[1]:
                if def_node.scope() != scope:
                    continue
                parent = def_node.parent
                if isinstance(parent, astroid.nodes.Assign) and isinstance(
                    parent.value, astroid.nodes.Call
                ):
                    call_node: astroid.nodes.Call = parent.value
                    for inf in call_node.func.infer():
                        if isinstance(inf, astroid.nodes.ClassDef):
                            return True
        except (astroid.InferenceError, AttributeError):
            pass
        return False

    def _is_hinted_protocol(self, node: astroid.nodes.NodeNG) -> bool:
        return self._ast_gateway.is_protocol(node)

    def _is_mock_involved(self, node: astroid.nodes.NodeNG) -> bool:
        qname = self._ast_gateway.get_return_type_qname_from_expr(node)
        return bool(qname and any(m in qname for m in ("unittest.mock", "pytest", "MagicMock")))
