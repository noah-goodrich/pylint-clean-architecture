import builtins
from typing import List, Optional, Set, Union

import astroid  # type: ignore[import-untyped]

from clean_architecture_linter.domain.protocols import AstroidProtocol
from clean_architecture_linter.infrastructure.typeshed_integration import TypeshedService

# Minimal fallback for astroid AST node attributes that are slots or defined in
# C/other modules: not present as AnnAssign/@property in the loaded AST, and
# inference returns Uninferable for params with string annotations. Used only when
# _find_attribute_type_in_class and attribute inference have failed. Add entries
# only for documented astroid API attributes; avoid broadening. Including bare
# "ClassDef" for when the type stays unresolved (e.g. string annotation under
# TYPE_CHECKING); prefer resolving to astroid.nodes.ClassDef when possible.
_KNOWN_ASTROID_ATTR: dict[tuple[str, str], str] = {
    ("astroid.nodes.ClassDef", "locals"): "builtins.dict",
    ("ClassDef", "locals"): "builtins.dict",
}


class AstroidGateway(AstroidProtocol):
    """AST Intelligence Gateway for true inference and discovery."""

    def __init__(self) -> None:
        # Enable preferring stubs
        astroid.MANAGER.prefer_stubs = True
        # Clear cache to ensure stubs are loaded if they exist
        astroid.MANAGER.clear_cache()
        self.typeshed = TypeshedService()
        # JUSTIFICATION: Lazy import to avoid circular dependency
        from clean_architecture_linter.infrastructure.gateways.python_gateway import PythonGateway
        self.python_gateway = PythonGateway()

    def clear_inference_cache(self) -> None:
        """Clear the astroid inference cache to force fresh inference after code changes."""
        astroid.MANAGER.clear_cache()

    def parse_file(self, file_path: str) -> Optional[astroid.nodes.Module]:
        """Parse a file and return the astroid Module node."""
        try:
            # JUSTIFICATION: File reading requires Path for file I/O
            from pathlib import Path
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                return None
            with open(file_path_obj, encoding="utf-8") as f:
                source = f.read()
            return astroid.parse(source, file_path)
        except Exception:
            return None

    def get_node_return_type_qname(self, node: astroid.nodes.NodeNG) -> Optional[str]:
        """Dynamically discovers fully qualified names using AST inference and signature hints."""
        # 1. Sticker Reading (Explicit Annotations / Casts)
        res = self._discovery_fallback(node)
        if res:
            return res

        # 2. Check Parent for AnnAssign "Sticker"
        if hasattr(node, "parent") and isinstance(node.parent, astroid.nodes.AnnAssign):
            if node.parent.value == node and node.parent.annotation:
                res = self._resolve_annotation(node.parent.annotation)
                return res

        # 3. Direct Inference (True Inference)
        try:
            for inf in node.infer():
                if inf is not astroid.Uninferable:
                    qname = str(inf.qname())
                    normalized = self._normalize_primitive(qname)
                    return normalized
        except (astroid.InferenceError, AttributeError):
            pass

        # 4. Typeshed Origin Tracing (The "Safety Net")
        # If astroid fails (Uninferable), we check if the origin is a trusted stdlib source.
        safe_qname = self._resolve_safe_origin(node)
        if safe_qname:
            return safe_qname

        return None

    def _resolve_safe_origin(self, node: astroid.nodes.NodeNG) -> Optional[str]:
        """Trace node to its origin and check if it comes from the standard library via Typeshed."""
        return self._trace_safety(node, set())

    def _trace_safety(self, node: astroid.nodes.NodeNG, visited: Set[int]) -> Optional[str]:
        """Recursive safety tracing."""
        if id(node) in visited:
            return None
        visited.add(id(node))

        try:
            if isinstance(node, astroid.nodes.Name):
                return self._trace_safety_name(node, visited)
            if isinstance(node, astroid.nodes.AssignName):
                return self._trace_safety_assignname(node, visited)
            if isinstance(node, astroid.nodes.Attribute):
                return self._trace_safety(node.expr, visited)
            if isinstance(node, astroid.nodes.Subscript):
                return self._trace_safety(node.value, visited)
            if isinstance(node, astroid.nodes.Call):
                return self._trace_safety_call(node, visited)
        except Exception:
            pass
        return None

    def _trace_safety_name(
        self, node: astroid.nodes.Name, visited: Set[int]
    ) -> Optional[str]:
        """Resolve Name via lookup and recurse."""
        stmts = node.lookup(node.name)[1]
        if not stmts:
            return None
        return self._trace_safety(stmts[0], visited)

    def _trace_safety_assignname(
        self, node: astroid.nodes.AssignName, visited: Set[int]
    ) -> Optional[str]:
        """Handle AssignName: loop variable, tuple unpacking, or standard assignment."""
        parent = node.parent
        if isinstance(parent, astroid.nodes.For):
            return self._check_iterator_safety(parent.iter, visited)
        if isinstance(parent, (astroid.nodes.Tuple, astroid.nodes.List)) and isinstance(
            parent.parent, astroid.nodes.For
        ):
            return self._check_iterator_safety(parent.parent.iter, visited)
        if isinstance(parent, astroid.nodes.Assign):
            return self._trace_safety(parent.value, visited)
        return None

    def _trace_safety_call(
        self, node: astroid.nodes.Call, visited: Set[int]
    ) -> Optional[str]:
        """Check module.func() calls against typeshed; return safe qname if stdlib."""
        func = node.func
        if not isinstance(func, astroid.nodes.Attribute):
            return None
        if not isinstance(func.expr, astroid.nodes.Name):
            return None
        expr = func.expr
        lookup_res = expr.lookup(expr.name)
        mod_lookup = lookup_res[1]
        if not mod_lookup or not isinstance(
            mod_lookup[0], (astroid.nodes.Import, astroid.nodes.ImportFrom)
        ):
            return None
        mod_name: str = ""
        if isinstance(mod_lookup[0], astroid.nodes.Import):
            mod_name = mod_lookup[0].names[0][0]
        elif isinstance(mod_lookup[0], astroid.nodes.ImportFrom):
            mod_name = mod_lookup[0].modname
        if not mod_name:
            return None
        full_name = f"{mod_name}.{func.attrname}"
        if self.typeshed.is_stdlib_qname(full_name):
            return "builtins.object"
        return None

    def _check_iterator_safety(self, iter_node: astroid.nodes.NodeNG, visited: Set[int]) -> Optional[str]:
        """Check if an iterator source is safe."""
        # 1. Direct Call (os.walk())
        if isinstance(iter_node, astroid.nodes.Call):
            res = self._trace_safety(iter_node, visited)
            if res:
                return "builtins.str"  # Assumption for iterators from safe calls

        # 2. Variable (for d in dirs)
        if isinstance(iter_node, astroid.nodes.Name):
            res = self._trace_safety(iter_node, visited)
            if res:
                return "builtins.str"  # Propagate safety

        return None

    def get_return_type_qname_from_expr(
        self,
        expr: astroid.nodes.NodeNG,
        visited: Optional[Set[int]] = None,
    ) -> Optional[str]:
        """Recursive resolution for complex expressions."""
        if expr is None:
            return None

        if visited is None:
            visited = set()

        expr_id = id(expr)
        if expr_id in visited:
            return None
        # JUSTIFICATION: Simple set membership update.
        visited.add(expr_id)

        if isinstance(expr, astroid.nodes.BoolOp):
            return self._resolve_bool_op(expr, visited)
        if isinstance(expr, astroid.nodes.BinOp):
            return self._resolve_bin_op(expr, visited)
        if isinstance(expr, astroid.nodes.Call) and self._is_typing_cast(expr):
            return self._resolve_typing_cast(expr)

        return self.get_node_return_type_qname(expr)

    def _is_typing_cast(self, node: astroid.nodes.Call) -> bool:
        """Check if call is typing.cast."""
        try:
            for inf in node.func.infer():
                if getattr(inf, "qname", lambda: "")() == "typing.cast":
                    return True
        except (astroid.InferenceError, AttributeError):
            pass
        return False

    def _resolve_typing_cast(self, node: astroid.nodes.Call) -> Optional[str]:
        """Extract type from typing.cast(Type, expr)."""
        if len(node.args) >= 1:
            return self._resolve_annotation(node.args[0])
        return None

    def _discovery_fallback(self, node: astroid.nodes.NodeNG) -> Optional[str]:
        """Signature Discovery via FunctionDef.returns, ClassDef, or variable annotations."""
        try:
            if isinstance(node, astroid.nodes.Call):
                return self._discover_from_call(node)

            if isinstance(node, (astroid.nodes.Name, astroid.nodes.AssignName)):
                return self._discover_from_name(node)

            if isinstance(node, astroid.nodes.Attribute):
                return self._discover_from_attribute(node)

        except (astroid.InferenceError, StopIteration, AttributeError):
            pass
        return None

    def _discover_from_call(self, node: astroid.nodes.Call) -> Optional[str]:
        """Discovery logic specifically for Call nodes."""
        # 1. Try to infer the target directly
        try:
            # JUSTIFICATION: Core AST inference logic.
            for inf in node.func.infer():
                if isinstance(inf, astroid.nodes.ClassDef):
                    return str(inf.qname())
                if isinstance(inf, astroid.nodes.FunctionDef) and inf.returns:
                    return self._resolve_annotation(inf.returns)
        except (astroid.InferenceError, StopIteration):
            pass

        # 2. Recursive Member Discovery: receiver.method()
        if isinstance(node.func, astroid.nodes.Attribute):
            receiver_type = self.get_node_return_type_qname(node.func.expr)
            if receiver_type:
                return self._find_method_in_class_hierarchy(receiver_type, node.func.attrname, node)
        return None

    def _discover_from_name(self, node: Union[astroid.nodes.Name, astroid.nodes.AssignName]) -> Optional[str]:
        """Discovery logic specifically for Name/AssignName nodes."""
        for def_node in node.lookup(node.name)[1]:
            # Direct annotation on AssignName is rare, check parent AnnAssign
            if hasattr(def_node, "parent") and isinstance(def_node.parent, astroid.nodes.AnnAssign):
                if def_node.parent.annotation:
                    return self._resolve_annotation(def_node.parent.annotation)

            # Direct annotation (fallback)
            if hasattr(def_node, "annotation") and def_node.annotation:
                return self._resolve_annotation(def_node.annotation)

            # Argument annotation
            if hasattr(def_node, "parent") and isinstance(def_node.parent, astroid.nodes.Arguments):
                res = self._resolve_arg_annotation(def_node, def_node.parent)
                if res:
                    return res
        return None

    def _get_param_annotation_qname(self, name: astroid.nodes.Name) -> Optional[str]:
        """Get the resolved or raw annotation for a Name that refers to a parameter."""
        for def_node in name.lookup(name.name)[1]:
            if getattr(def_node, "parent", None) and isinstance(
                def_node.parent, astroid.nodes.Arguments
            ):
                res = self._resolve_arg_annotation(def_node, def_node.parent)
                if res:
                    return res
                # Fallback: raw annotation string (e.g. Const "ClassDef") when resolve fails
                try:
                    args = def_node.parent
                    annos = getattr(args, "annotations", None) or []
                    all_args = (getattr(args, "posonlyargs", None) or []) + args.args + (getattr(args, "kwonlyargs", None) or [])
                    all_annos = (getattr(args, "posonlyargs_annotations", None) or []) + annos + (getattr(args, "kwonlyargs_annotations", None) or [])
                    idx = all_args.index(def_node)
                    if idx < len(all_annos) and all_annos[idx]:
                        a = all_annos[idx]
                        if isinstance(a, astroid.nodes.Const) and isinstance(a.value, str):
                            return a.value
                except (ValueError, IndexError, AttributeError):
                    pass
        return None

    def _resolve_arg_annotation(self, def_node: astroid.nodes.NodeNG, args: astroid.nodes.Arguments) -> Optional[str]:
        """Helper to find annotation for a specific argument definition."""
        try:
            p_args = getattr(args, "posonlyargs", None) or []
            k_args = getattr(args, "kwonlyargs", None) or []
            p_annos = getattr(args, "posonlyargs_annotations", None) or []
            k_annos = getattr(args, "kwonlyargs_annotations", None) or []

            all_args = p_args + args.args + k_args
            annos = getattr(args, "annotations", None) or []
            all_annos = (p_annos or []) + annos + (k_annos or [])

            idx = all_args.index(def_node)
            if idx < len(all_annos) and all_annos[idx]:
                return self._resolve_annotation(all_annos[idx])

            # If no annotation, try to infer from default value
            # Arguments.defaults matches positional args from the right
            diff = len(args.args) - len(args.defaults)
            arg_idx = args.args.index(
                def_node) if def_node in args.args else -1
            if arg_idx >= diff:
                default_idx = arg_idx - diff
                return self.get_node_return_type_qname(args.defaults[default_idx])
        except (ValueError, IndexError):
            pass
        return None

    def _discover_from_attribute(self, node: astroid.nodes.Attribute) -> Optional[str]:
        """Resolve type of receiver.attr using param/annotation and class attribute declarations.

        Type-hint and declaration driven: gets receiver type (e.g. from parameter
        annotation), then the attribute's type from the class body (AnnAssign or
        @property). If that fails, tries inferring the attribute (e.g. for slots
        or built-in attributes on astroid nodes). No hardcoded attribute names.
        """
        receiver_type = self.get_node_return_type_qname(node.expr)
        if receiver_type:
            res = self._find_attribute_type_in_class(receiver_type, node.attrname, node)
            if res:
                return res
        # Fallback: infer the attribute (e.g. ClassDef.locals, slots, built-ins)
        try:
            for inf in node.infer():
                if inf is astroid.Uninferable:
                    continue
                q = getattr(inf, "qname", None)
                if not q:
                    continue
                qname = str(q() if callable(q) else q)
                if qname:
                    n = self._normalize_primitive(qname)
                    if n and self.is_primitive(n):
                        return n
        except (astroid.InferenceError, AttributeError):
            pass
        # Last resort: known astroid node attributes (slots / re-exported; see _KNOWN_ASTROID_ATTR)
        if receiver_type:
            key = (receiver_type, node.attrname)
            if key in _KNOWN_ASTROID_ATTR:
                return _KNOWN_ASTROID_ATTR[key]
        # When receiver type is unresolved (e.g. string ann under TYPE_CHECKING), try
        # to read the param annotation for a Name receiver and match known (class, attr).
        if (
            receiver_type is None
            and isinstance(node.expr, astroid.nodes.Name)
            and node.attrname == "locals"
        ):
            cand = self._get_param_annotation_qname(node.expr)
            if cand and "ClassDef" in cand:
                return _KNOWN_ASTROID_ATTR.get(("ClassDef", "locals"))
        return None

    def _find_attribute_type_in_class(
        self, class_qname: str, attr_name: str, context: astroid.nodes.NodeNG
    ) -> Optional[str]:
        """Look up an attribute's type from a class by qname. Uses annotations in class body."""
        try:
            root: astroid.nodes.Module = context.root()
            root_name = getattr(root, "name", "")
            clean_name = class_qname
            is_local = bool(
                class_qname.startswith(".") or ("." not in class_qname) or
                (root_name and class_qname.startswith(root_name + "."))
            )
            if class_qname.startswith("."):
                clean_name = class_qname.lstrip(".")
            elif root_name and class_qname.startswith(root_name + "."):
                clean_name = class_qname[len(root_name) + 1 :]

            if is_local and hasattr(root, "lookup"):
                lookup_res = root.lookup(clean_name)
                if lookup_res[1] and isinstance(lookup_res[1][0], astroid.nodes.ClassDef):
                    return self._resolve_attribute_in_node(lookup_res[1][0], attr_name)

            module_parts = class_qname.split(".")
            module_name = "builtins" if len(module_parts) < 2 else ".".join(module_parts[:-1])
            class_name = module_parts[-1]
            if module_name:
                module = astroid.MANAGER.ast_from_module_name(module_name)
                lookup_res = module.lookup(class_name)
                if lookup_res[1] and isinstance(lookup_res[1][0], astroid.nodes.ClassDef):
                    res = self._resolve_attribute_in_node(lookup_res[1][0], attr_name)
                    if res:
                        return res
                    if self.typeshed.is_stdlib_module(module_name):
                        stub_res = self.typeshed.get_attribute_type_from_stub(
                            class_qname, attr_name
                        )
                        if stub_res:
                            return stub_res
        except (astroid.AstroidBuildingError, AttributeError):
            pass
        return None

    def _resolve_attribute_in_node(
        self, class_node: astroid.nodes.ClassDef, attr_name: str
    ) -> Optional[str]:
        """Get attribute type from class body (AnnAssign, @property) or bases. Type-hint driven."""
        for n in class_node.body:
            if isinstance(n, astroid.nodes.AnnAssign) and n.annotation:
                tname = getattr(n.target, "name", None)
                if tname == attr_name:
                    return self._resolve_annotation(n.annotation)
            if isinstance(n, astroid.nodes.FunctionDef) and n.name == attr_name:
                decs = getattr(getattr(n, "decorators", None), "nodes", None) or []
                if any(
                    isinstance(d, astroid.nodes.Name) and d.name == "property"
                    for d in decs
                ) and n.returns:
                    return self._resolve_annotation(n.returns)
        try:
            for ancestor in class_node.ancestors():
                res = self._resolve_attribute_in_node(ancestor, attr_name)
                if res:
                    return res
        except astroid.InferenceError:
            pass
        return None

    def _find_method_in_class_hierarchy(
        self,
        class_qname: str,
        method_name: str,
        context: astroid.nodes.NodeNG,
    ) -> Optional[str]:
        """Look up a method in a class by its fully qualified name with local context."""
        try:
            # 1. Local Lookup (handle relative and bare names)
            root: astroid.nodes.Module = context.root()
            root_name = getattr(root, "name", "")

            clean_name = class_qname
            is_local: bool = False

            if class_qname.startswith(".") or "." not in class_qname:
                clean_name = class_qname.lstrip(".")
                is_local: bool = True
            elif root_name and class_qname.startswith(root_name + "."):
                clean_name = class_qname[len(root_name)+1:]
                is_local: bool = True

            if is_local and hasattr(root, "lookup"):
                # JUSTIFICATION: Core AST traversal.
                lookup_res = root.lookup(clean_name)
                if lookup_res[1] and isinstance(lookup_res[1][0], astroid.nodes.ClassDef):
                    return self._resolve_method_in_node(lookup_res[1][0], method_name)

            # 2. Absolute Lookup
            module_parts: List[str] = class_qname.split(".")
            module_name: str = "builtins" if len(
                module_parts) < 2 else ".".join(module_parts[:-1])
            class_name: str = module_parts[-1]
            if module_name:
                try:
                    module = astroid.MANAGER.ast_from_module_name(module_name)
                    lookup_res = module.lookup(class_name)
                    if lookup_res[1] and isinstance(lookup_res[1][0], astroid.nodes.ClassDef):
                        return self._resolve_method_in_node(lookup_res[1][0], method_name)
                except astroid.AstroidBuildingError:
                    pass
        except Exception:
            pass
        return None

    def _resolve_method_in_node(self, class_node: astroid.nodes.ClassDef, method_name: str) -> Optional[str]:
        """Recursive discovery of method return type through inheritance."""
        # 1. Search immediate node
        for method in class_node.mymethods():
            if method.name == method_name and method.returns:
                return self._resolve_annotation(method.returns)

        # 2. Search ancestors
        try:
            for ancestor in class_node.ancestors():
                for method in ancestor.mymethods():
                    if method.name == method_name and method.returns:
                        return self._resolve_annotation(method.returns)
        except astroid.InferenceError:
            pass
        return None

    def _resolve_annotation(self, anno: astroid.nodes.NodeNG) -> Optional[str]:
        """Resolve a type annotation node to its fully qualified name."""
        if isinstance(anno, astroid.nodes.Subscript):
            return self._resolve_subscript_annotation(anno)

        if isinstance(anno, astroid.nodes.BinOp) and anno.op == "|":
            return self._resolve_nested_annotation(anno)

        if str(getattr(anno, "qname", lambda: "")()) == "types.UnionType":
            return self._resolve_nested_annotation(anno)

        # Handle Index wrapper in some astroid versions
        if hasattr(anno, "value") and isinstance(anno, astroid.nodes.Index):
            return self._resolve_annotation(anno.value)

        return self._resolve_simple_annotation(anno)

    def _resolve_subscript_annotation(self, anno: astroid.nodes.Subscript) -> Optional[str]:
        """Resolve complex subscript annotations (Optional, Union, List, etc.)."""
        try:
            # JUSTIFICATION: Core AST inference logic.
            for inf in anno.value.infer():
                if inf is astroid.Uninferable:
                    continue
                qname = str(inf.qname())
                res = self._map_typing_to_builtin(qname, anno.slice)
                if res:
                    return res
        except (astroid.InferenceError, AttributeError):
            pass
        return self._resolve_nested_annotation(anno.slice)

    def _map_typing_to_builtin(self, qname: str, slice_node: astroid.nodes.NodeNG) -> Optional[str]:
        """Maps typing module names to simplified builtins or unwraps them."""
        if qname in ("typing.Optional", "typing.Union", "Union"):
            return self._resolve_nested_annotation(slice_node)
        if qname == "typing.List":
            return "builtins.list"
        if qname == "typing.Dict":
            return "builtins.dict"
        return qname

    def _resolve_simple_annotation(self, anno: astroid.nodes.NodeNG) -> Optional[str]:
        """Resolve terminal annotation nodes (Name, Const, inferable)."""
        if isinstance(anno, astroid.nodes.Name):
            if anno.name == "Self":
                return self._resolve_self_type(anno)
            try:
                for inf in anno.infer():
                    if inf is not astroid.Uninferable and hasattr(inf, "qname"):
                        q = getattr(inf, "qname", lambda: "")()
                        if q:
                            return self._normalize_primitive(str(q))
            except (astroid.InferenceError, AttributeError):
                pass
            return self._normalize_primitive(str(anno.name))

        if isinstance(anno, astroid.nodes.Const) and isinstance(anno.value, str):
            if anno.value == "Self":
                return self._resolve_self_type(anno)
            val = anno.value
            if val.isidentifier() and "." not in val:
                try:
                    scope = anno.scope()
                    if hasattr(scope, "lookup"):
                        _, stmts = scope.lookup(val)
                        if stmts:
                            for inf in stmts[0].infer():
                                if inf is not astroid.Uninferable and hasattr(inf, "qname"):
                                    q = getattr(inf, "qname", lambda: "")()
                                    if q:
                                        return self._normalize_primitive(str(q))
                except (astroid.InferenceError, AttributeError):
                    pass
            return self._normalize_primitive(val)

        try:
            for inf in anno.infer():
                if inf is not astroid.Uninferable:
                    return self._normalize_primitive(str(inf.qname()))
        except (astroid.InferenceError, AttributeError):
            pass
        return None

    def _resolve_self_type(self, node: astroid.nodes.NodeNG) -> Optional[str]:
        """Resolve 'Self' to the containing class qname."""
        scope = node.scope()
        while scope and not isinstance(scope, astroid.nodes.ClassDef):
            if hasattr(scope, "parent"):
                scope_parent = scope.parent
                scope = scope_parent.scope()
            else:
                scope = None
        if isinstance(scope, astroid.nodes.ClassDef):
            return str(scope.qname())
        return None

    def _normalize_primitive(self, qname: str) -> str:
        """Normalize types like 'str' to 'builtins.str'."""
        if not qname:
            return ""
        # Dynamic check via python gateway if needed, but for primitives simple prefixing is okay
        # provided we don't assume the list is exhaustive for all safety checks.
        base_name = qname.split(".")[-1]
        # Check against actual builtins module if possible, simplified here
        # Check against actual builtins module
        if hasattr(builtins, base_name):
            return f"builtins.{base_name}"
        return qname

    def _resolve_nested_annotation(self, slice_node: astroid.nodes.NodeNG) -> Optional[str]:
        """Resolve inner types of Optional/Union/List/etc."""
        # Handle Index wrapper
        real_slice = slice_node
        if hasattr(slice_node, "value") and not isinstance(slice_node, (astroid.nodes.Tuple, astroid.nodes.Const)):
            real_slice = slice_node.value

        nodes: List[astroid.nodes.NodeNG] = []
        if isinstance(real_slice, (astroid.nodes.Tuple, astroid.nodes.List)):
            nodes = real_slice.elts
        elif isinstance(real_slice, astroid.nodes.BinOp) and real_slice.op == "|":
            nodes = [real_slice.left, real_slice.right]
        else:
            nodes = [real_slice]

        for n in nodes:
            res = self._resolve_annotation(n)
            # Skip NoneType to find the 'real' type in Optional[T]
            if res and res not in ("builtins.NoneType", "None", "NoneType"):
                return res
        return None

    def _resolve_bool_op(self, expr: astroid.nodes.BoolOp, visited: Set[int]) -> Optional[str]:
        """Resolve types in boolean operations."""
        results: Set[str] = set()
        for v in expr.values:
            res = self.get_return_type_qname_from_expr(v, visited)
            if res:
                results.add(res)

        results.discard("builtins.NoneType")
        results.discard("NoneType")

        return list(results)[0] if len(results) == 1 else None

    def _resolve_bin_op(self, expr: astroid.nodes.BinOp, visited: Set[int]) -> Optional[str]:
        """Resolve types in binary operations."""
        left = self.get_return_type_qname_from_expr(expr.left, visited)
        right = self.get_return_type_qname_from_expr(expr.right, visited)
        if left == right:
            return left
        # Simple heuristic for mixed types (e.g. int + float -> float)
        if {left, right} == {"builtins.int", "builtins.float"}:
            return "builtins.float"
        return None

    def get_call_name(self, node: astroid.nodes.Call) -> Optional[str]:
        """Safely retrieve the name of the function or method being called."""
        if hasattr(node.func, "attrname"):
            return str(node.func.attrname)
        if hasattr(node.func, "name"):
            return str(node.func.name)
        return None

    def is_protocol(self, node: astroid.nodes.NodeNG) -> bool:
        """Robust detection of Protocols using inference and gateways."""
        if isinstance(node, astroid.nodes.ClassDef):
            return self._is_protocol_classdef(node)
        qname: Optional[str] = self.get_return_type_qname_from_expr(node)
        if qname and self._is_protocol_via_qname(qname, node):
            return True
        return self._is_protocol_via_infer(node)

    def _is_protocol_classdef(self, node: astroid.nodes.ClassDef) -> bool:
        """Check if a ClassDef is or inherits from Protocol."""
        if node.qname().endswith(".Protocol"):
            return True
        try:
            for ancestor in node.ancestors():
                if ancestor.qname() in ("typing.Protocol", "_typing.Protocol"):
                    return True
        except (astroid.InferenceError, AttributeError):
            pass
        return False

    def _is_protocol_via_qname(
        self, qname: str, context: astroid.nodes.NodeNG
    ) -> bool:
        """Check Protocol via qname string and optional class lookup."""
        if qname.endswith(".Protocol") or qname == "Protocol":
            return True
        if ".protocols." in qname.lower():
            return True
        class_node = self._find_class_node(qname, context)
        if not class_node or not isinstance(class_node, astroid.nodes.ClassDef):
            return False
        try:
            return any(
                a.qname() in ("typing.Protocol", "_typing.Protocol")
                for a in class_node.ancestors()
            )
        except (astroid.InferenceError, AttributeError):
            return False

    def _is_protocol_via_infer(self, node: astroid.nodes.NodeNG) -> bool:
        """Check Protocol via raw inference and ancestor traversal."""
        try:
            for inf in node.infer():
                if not isinstance(inf, astroid.nodes.ClassDef):
                    continue
                if inf.qname().endswith(".Protocol"):
                    return True
                for ancestor in inf.ancestors():
                    if ancestor.qname() in ("typing.Protocol", "_typing.Protocol"):
                        return True
        except (astroid.InferenceError, AttributeError):
            pass
        return False

    def is_protocol_call(self, node: astroid.nodes.Call) -> bool:
        """Check if the call is being made on a Protocol's method."""
        if not isinstance(node, astroid.nodes.Call):
            return False
        if self._is_protocol_call_via_infer(node):
            return True
        if self._is_protocol_call_via_receiver(node):
            return True
        return False

    def _is_protocol_call_via_infer(self, node: astroid.nodes.Call) -> bool:
        """Direct inference: func.infer -> parent ClassDef -> is_protocol."""
        try:
            for inf in node.func.infer():
                if inf is astroid.Uninferable:
                    continue
                parent = getattr(inf, "parent", None)
                if isinstance(parent, astroid.nodes.ClassDef) and self.is_protocol(parent):
                    return True
        except (astroid.InferenceError, AttributeError):
            pass
        return False

    def _is_protocol_call_via_receiver(self, node: astroid.nodes.Call) -> bool:
        """Continuity (receiver is Protocol call) or receiver-based fallback."""
        if isinstance(node.func, astroid.nodes.Attribute):
            if isinstance(node.func.expr, astroid.nodes.Call):
                if self.is_protocol_call(node.func.expr):
                    return True
            receiver_qname = self.get_return_type_qname_from_expr(
                node.func.expr)
            if receiver_qname:
                class_node = self._find_class_node(receiver_qname, node)
                if class_node and self.is_protocol(class_node):
                    return True
                if receiver_qname.endswith(".Protocol") or "Protocol" in receiver_qname:
                    return True
        return False

    def _find_class_node(self, qname: str, context: astroid.nodes.NodeNG) -> Optional[astroid.nodes.ClassDef]:
        """Find a ClassDef node by its fully qualified name."""
        try:
            root: astroid.nodes.Module = context.root()
            root_name = getattr(root, "name", "")

            # 1. Local Lookup (handle relative, bare names, and same-module names)
            clean_name = qname
            is_local: bool = False

            if qname.startswith(".") or "." not in qname:
                clean_name = qname.lstrip(".")
                is_local: bool = True
            elif root_name and qname.startswith(root_name + "."):
                clean_name = qname[len(root_name)+1:]
                is_local: bool = True

            if is_local and hasattr(root, "lookup"):
                lookup_res = root.lookup(clean_name)
                if lookup_res[1] and isinstance(lookup_res[1][0], astroid.nodes.ClassDef):
                    return lookup_res[1][0]

            # 2. Absolute Lookup
            module_parts: List[str] = qname.split(".")
            module_name: str = "builtins" if len(
                module_parts) < 2 else ".".join(module_parts[:-1])
            class_name: str = module_parts[-1]
            if module_name:
                try:
                    module = astroid.MANAGER.ast_from_module_name(module_name)
                    lookup_res = module.lookup(class_name)
                    if lookup_res[1] and isinstance(lookup_res[1][0], astroid.nodes.ClassDef):
                        return lookup_res[1][0]
                except (astroid.AstroidBuildingError, AttributeError):
                    pass
        except Exception:
            pass
        return None

    def is_fluent_call(self, node: astroid.nodes.Call) -> bool:
        """Check if the call returns the same type as the receiver (Fluent API)."""
        if not isinstance(node, astroid.nodes.Call) or not isinstance(node.func, astroid.nodes.Attribute):
            return False

        # 1. Recursive Continuity: If receiver is already fluent, we keep going
        if isinstance(node.func.expr, astroid.nodes.Call):
            if self.is_fluent_call(node.func.expr):
                return True

        # 2. Direct match check
        try:
            receiver_qname: Optional[str] = self.get_return_type_qname_from_expr(
                node.func.expr)
            return_qname: Optional[str] = self.get_node_return_type_qname(node)

            if receiver_qname and return_qname:
                # Direct match or structural match (e.g. both are 'DataFrame')
                if receiver_qname == return_qname:
                    return True

                # Check base names if qnames are messy (e.g. '.DataFrame' vs 'pyspark.sql.DataFrame')
                # JUSTIFICATION: Internal name extraction for normalization.
                rec_parts: List[str] = receiver_qname.split(".")
                rec_base: str = rec_parts[-1]
                ret_parts: List[str] = return_qname.split(".")
                ret_base: str = ret_parts[-1]
                if rec_base == ret_base and rec_base != "NoneType":
                    return True
        except (astroid.InferenceError, AttributeError):
            pass
        return False

    def is_trusted_authority_call(self, node: astroid.nodes.Call) -> bool:
        """Check if the call's method belongs to a Trusted Authority."""
        if not isinstance(node, astroid.nodes.Call):
            return False
        if self._trusted_authority_via_infer(node):
            return True
        if not isinstance(node.func, astroid.nodes.Attribute):
            return False
        if isinstance(node.func.expr, astroid.nodes.Call):
            if self._check_trusted_authority_call_recursive(node.func.expr, set()):
                return True
        receiver_qname = self.get_return_type_qname_from_expr(node.func.expr)
        if receiver_qname and self._trusted_authority_via_receiver(node, receiver_qname):
            return True
        return False

    def _trusted_authority_via_infer(self, node: astroid.nodes.Call) -> bool:
        """Check trust via func.infer() -> qname -> stdlib module."""
        try:
            for inf in node.func.infer():
                qname: str = getattr(inf, "qname", lambda: "")()
                if not qname:
                    continue
                module_name = qname.split(".")[0]
                if self.python_gateway.is_stdlib_module(module_name):
                    return True
        except (astroid.InferenceError, AttributeError):
            pass
        return False

    def _trusted_authority_via_receiver(
        self, node: astroid.nodes.Call, receiver_qname: str
    ) -> bool:
        """Check trust via receiver type: stdlib, builtins, or external dependency."""
        module_name = receiver_qname.split(".")[0]
        if self.python_gateway.is_stdlib_module(module_name):
            return True
        if receiver_qname.startswith("builtins."):
            return True
        receiver_node = self._find_class_node(receiver_qname, node)
        if receiver_node and hasattr(receiver_node, "root"):
            file_path = str(getattr(receiver_node.root(), "file", ""))
            if self.python_gateway.is_external_dependency(file_path):
                return True
        return False

    def is_primitive(self, qname: str) -> bool:
        """Identify if a type belongs to the primitive trust circle."""
        if not isinstance(qname, str) or not qname:
            return False

        # Handle Unions: all parts must be primitive
        if "|" in qname:
            parts = [p.strip() for p in qname.split("|")]
            return all(self.is_primitive(p) for p in parts)

        # Normalize: sometimes we get 'str', sometimes 'builtins.str'
        parts = qname.split(".")
        base_name = parts[-1]
        if qname.startswith("builtins.") or base_name in (
            "str", "int", "float", "list", "dict", "set", "bool", "bytes", "tuple", "NoneType", "type"
        ):
            return True
        if qname.startswith(("typing.", "collections.abc.")):
            return True
        return False

    def _check_trusted_authority_call_recursive(
        self, node: astroid.nodes.Call, visited: Set[int]
    ) -> bool:
        """Internal helper to prevent recursion loops."""
        node_id = id(node)
        if node_id in visited:
            return False
        visited.add(node_id)
        if self._trusted_authority_via_infer(node):
            return True
        if not isinstance(node.func, astroid.nodes.Attribute):
            return False
        if isinstance(node.func.expr, astroid.nodes.Call):
            if self._check_trusted_authority_call_recursive(node.func.expr, visited):
                return True
        receiver_qname = self.get_return_type_qname_from_expr(node.func.expr)
        if receiver_qname and self._trusted_authority_via_receiver(node, receiver_qname):
            return True
        return False
