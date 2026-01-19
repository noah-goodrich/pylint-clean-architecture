import sys
from typing import TYPE_CHECKING, Optional, Set, Union

import astroid  # type: ignore[import-untyped]

if TYPE_CHECKING:
    from clean_architecture_linter.config import ConfigurationLoader

from clean_architecture_linter.constants import BUILTIN_TYPE_MAP


def get_call_name(node: astroid.nodes.Call) -> Optional[str]:
    """Extract the name of the function or method being called from a Call node."""
    if not isinstance(node, astroid.nodes.Call):
        return None

    if isinstance(node.func, astroid.nodes.Name):
        return node.func.name
    if isinstance(node.func, astroid.nodes.Attribute):
        return node.func.attrname
    return None


def get_node_layer(node: astroid.nodes.NodeNG, config_loader: "ConfigurationLoader") -> Optional[str]:
    """Resolve the architectural layer for a given AST node."""
    root = node.root()
    file_path = getattr(root, "file", "")
    current_module = root.name
    return config_loader.get_layer_for_module(current_module, file_path)


def _normalize_qname(qname: Optional[str]) -> Optional[str]:
    """Normalize qnames (e.g. typing.List -> builtins.list)."""
    if not qname:
        return None

    # Structural/Generic normalization only.
    # Primitives must be resolved via inference to builtins.<type>.
    mapping = {
        "typing.List": "builtins.list",
        "typing.Dict": "builtins.dict",
        "typing.Set": "builtins.set",
        "typing.Tuple": "builtins.tuple",
        "typing.Optional": "builtins.Optional",
        "typing.Union": "builtins.Union",
        "builtins.NoneType": "builtins.NoneType",
    }
    mapping.update(BUILTIN_TYPE_MAP)

    if qname in mapping:
        return mapping[qname]

    if qname.startswith("typing."):
        base = qname.split("[")[0].split(".")[-1]
        typing_map = {
            "List": "builtins.list",
            "Dict": "builtins.dict",
            "Set": "builtins.set",
            "Tuple": "builtins.tuple",
        }
        if base in typing_map:
            return typing_map[base]
        if base in ("Optional", "Union"):
            return f"builtins.{base}"

    return mapping.get(qname, qname)


def _get_return_type_from_method(
    method: Union[astroid.nodes.FunctionDef, astroid.bases.BoundMethod, astroid.bases.UnboundMethod, astroid.bases.Instance]
) -> Optional[str]:
    """Helper to extract return type qname from a function/method node."""
    # Unwrap BoundMethod/UnboundMethod
    if hasattr(method, "_proxied"):
         proxied = method._proxied
         if proxied and proxied != method:
             return _get_return_type_from_method(proxied)

    if not hasattr(method, "returns"):
        return None

    anno = method.returns
    if not anno:
        return None

    return _get_return_type_from_annotation(anno)


def _get_return_type_from_annotation(anno: astroid.nodes.NodeNG) -> Optional[str]:
    """Helper to resolve a type annotation node (Name, Attribute, Subscript) to a qname."""
    if anno is None:
        return None

    # Handle Subscripts (Optional[T], list[T], etc.)
    if isinstance(anno, astroid.nodes.Subscript):
        res = _resolve_subscript_annotation(anno)
        if res:
            return res

    # Standard inference
    try:
        for hint_inferred in anno.infer():
            if hint_inferred is not astroid.Uninferable:
                return _normalize_qname(hint_inferred.qname())

        # FINAL FALLBACK
        if isinstance(anno, astroid.nodes.Name):
            return _normalize_qname(anno.name)
        if isinstance(anno, astroid.nodes.Attribute):
            return _normalize_qname(anno.as_string())
    except (astroid.InferenceError, AttributeError):
        pass
    return None


def _resolve_subscript_annotation(anno: astroid.nodes.Subscript) -> Optional[str]:
    """Internal helper for subscript annotation resolution."""
    try:
        inferred_values = list(anno.value.infer())
        for val_inf in inferred_values:
            if val_inf is astroid.Uninferable:
                continue
            qname = _normalize_qname(val_inf.qname())
            if qname in ("builtins.Optional", "builtins.Union"):
                return _resolve_nested_annotation(anno.slice)

        # Fallback for when inference fails (common in small snippets or partially resolved code)
        if isinstance(anno.value, astroid.nodes.Name):
            name = anno.value.name
            if name in ("Optional", "Union"):
                 return _resolve_nested_annotation(anno.slice)

        # Handle list[T], dict[K, V] generic types
        for val_inf in inferred_values:
            if val_inf is not astroid.Uninferable:
                return _normalize_qname(val_inf.qname())

        if isinstance(anno.value, astroid.nodes.Name):
            return _normalize_qname(anno.value.name)

    except (astroid.InferenceError, AttributeError):
        pass
    return None


def _resolve_nested_annotation(slice_node: astroid.nodes.NodeNG) -> Optional[str]:
    """Helper to resolve the inner type of Optional[T] or Union[T, None]."""
    # handle Tuple (Union[A, B]) or single node (Optional[A])
    nodes_to_check = []
    if isinstance(slice_node, astroid.nodes.Tuple):
        nodes_to_check = slice_node.elts
    else:
        nodes_to_check = [slice_node]

    for n in nodes_to_check:
        res = _get_return_type_from_annotation(n)
        if res and res != "builtins.NoneType":
            return res
    return None


def _get_annotation_node(target: astroid.nodes.NodeNG) -> Optional[astroid.nodes.NodeNG]:
    """Helper to find the type annotation node for an AssignName or Argument."""
    if hasattr(target, "annotation") and target.annotation:
        return target.annotation

    if hasattr(target, "parent") and isinstance(target.parent, astroid.nodes.AnnAssign):
        return target.parent.annotation

    if isinstance(target.parent, astroid.nodes.Arguments):
        args_node = target.parent
        try:
            if target in args_node.args:
                idx = args_node.args.index(target)
                if idx < len(args_node.annotations) and args_node.annotations[idx]:
                    return args_node.annotations[idx]
        except (ValueError, AttributeError):
            pass
    return None


def get_return_type_qname_from_expr(expr: astroid.nodes.NodeNG, visited: Optional[Set[int]] = None) -> Optional[str]:
    """
    Recursively attempt to find the return type qname from an expression.
    """
    if expr is None:
        return None

    if visited is None:
        visited = set()

    expr_id = id(expr)
    if expr_id in visited:
        return None
    visited.add(expr_id)

    if isinstance(expr, astroid.nodes.Call):
        return get_return_type_qname(expr)
    if isinstance(expr, astroid.nodes.BoolOp):
        return _resolve_bool_op_type(expr, visited)
    if isinstance(expr, astroid.nodes.BinOp):
        return _resolve_bin_op_type(expr, visited)
    if isinstance(expr, astroid.nodes.Attribute):
        return _resolve_attribute_type(expr, visited)
    if isinstance(expr, (astroid.nodes.Name, astroid.nodes.AssignName)):
        return _resolve_name_type(expr, visited)

    return None


def _resolve_bool_op_type(expr: astroid.nodes.BoolOp, visited: Set[int]) -> Optional[str]:
    """Resolve type for boolean operations."""
    types = {get_return_type_qname_from_expr(v, visited) for v in expr.values}
    types.discard(None)
    if "builtins.NoneType" in types:
        types.discard("builtins.NoneType")
    return list(types)[0] if len(types) == 1 else None


def _resolve_bin_op_type(expr: astroid.nodes.BinOp, visited: Set[int]) -> Optional[str]:
    """Resolve type for binary operations."""
    left = get_return_type_qname_from_expr(expr.left, visited)
    right = get_return_type_qname_from_expr(expr.right, visited)
    return left if left == right else None


def _resolve_attribute_type(expr: astroid.nodes.Attribute, visited: Set[int]) -> Optional[str]:
    """Resolve type for attribute access."""
    try:
        for inf in expr.infer():
            if inf is not astroid.Uninferable:
                return _normalize_qname(inf.qname())
    except (astroid.InferenceError, AttributeError):
        pass

    receiver_qname = get_return_type_qname_from_expr(expr.expr, visited)
    if not receiver_qname:
        return None

    try:
        module, class_name = _get_module_and_class_from_qname(receiver_qname, expr.root())
        if not module or not class_name:
            return None

        _, nodes = module.lookup(class_name)
        for res_inf in nodes:
            if isinstance(res_inf, astroid.nodes.ClassDef):
                for attr_node in res_inf.igetattr(expr.attrname):
                    if hasattr(attr_node, "returns") or hasattr(attr_node, "_proxied"):
                        return _get_return_type_from_method(attr_node)
                    anno = _get_annotation_node(attr_node)
                    if anno:
                        return _get_return_type_from_annotation(anno)
    except Exception:
        pass
    return None


def _get_module_and_class_from_qname(
    qname: str, root_node: astroid.nodes.Module
) -> tuple[Optional[astroid.nodes.Module], Optional[str]]:
    """Helper to resolve module and class name from qname."""
    if qname.startswith("."):
        return root_node, qname[1:]
    if "." in qname:
        root_name, class_name = qname.rsplit(".", 1)
        try:
            return astroid.MANAGER.ast_from_module_name(root_name), class_name
        except Exception:
            return None, None
    return root_node, qname


def _resolve_name_type(
    expr: Union[astroid.nodes.Name, astroid.nodes.AssignName], visited: Set[int]
) -> Optional[str]:
    """Resolve type for Name or AssignName nodes."""
    try:
        for inf in expr.infer():
            if inf is not astroid.Uninferable:
                return _normalize_qname(inf.qname())
    except (astroid.InferenceError, AttributeError):
        pass

    name_to_lookup = getattr(expr, "name", None)
    if not name_to_lookup:
        return None

    frame = expr.scope()
    try:
        scope_nodes = frame.lookup(name_to_lookup)
        if not scope_nodes:
            return None

        # Try to find type from assignments or annotations in scope
        return _find_type_in_scope_nodes(scope_nodes[1], expr, visited)
    except Exception:
        pass
    return None


def _find_type_in_scope_nodes(
    nodes: list[astroid.nodes.NodeNG], expr: astroid.nodes.NodeNG, visited: Set[int]
) -> Optional[str]:
    """Helper to find type from assignments or annotations."""
    for target in nodes:
        # Handle Assignments
        if hasattr(target, "parent") and isinstance(target.parent, (astroid.nodes.Assign, astroid.nodes.AnnAssign)):
            rhs = getattr(target.parent, "value", None)
            if rhs and rhs != expr:
                res = get_return_type_qname_from_expr(rhs, visited)
                if res:
                    return res

        # Handle Annotations (Parameters, AnnAssign)
        anno = _get_annotation_node(target)
        if anno:
            res = _get_return_type_from_annotation(anno)
            if res:
                return res
    return None


def get_return_type_qname(node: astroid.nodes.Call) -> Optional[str]:
    """
    Get the return type of a Call node using programmatic resolution.
    Moving from 'Simulating the Interpreter' to 'Querying the Environment.'
    """
    # 1. Resolution via node.func.infer()
    try:
        inferred_targets = list(node.func.infer())
        for inferred in inferred_targets:
            if inferred is astroid.Uninferable:
                continue

            # Task 2: Harden getattr Heuristics
            # Special logic for getattr must only execute if it resolves to builtins.getattr
            if hasattr(inferred, "qname") and inferred.qname() == "builtins.getattr":
                if len(node.args) == 3:
                    return get_return_type_qname_from_expr(node.args[2])
                return None

            # Task 1: If the resolved object is a builtins class (the constructor), return its .qname().
            if isinstance(inferred, astroid.nodes.ClassDef):
                return _normalize_qname(inferred.qname())

            # Task 1: If the resolved object is a builtins function, return its .returns hint.
            res = _get_return_type_from_method(inferred)
            if res:
                return res
    except (astroid.InferenceError, AttributeError):
        pass

    # 2. Manual attribute resolution fallback (for un-inferred chains)
    if isinstance(node.func, astroid.nodes.Attribute):
        res = _resolve_attribute_type(node.func, set())
        if res:
            return res

    # 3. Final Fallback: Full ASTroid inference on the call node itself
    # Catches builtin returns like [].pop() -> T
    try:
        for inf in node.infer():
            if inf is not astroid.Uninferable:
                return _normalize_qname(inf.qname())
    except Exception:
        pass

    # Zero-Fallback Policy: Unresolved types return None.
    return None




def is_std_lib_module(module_name: str) -> bool:
    """Check if a module is part of the Python Standard Library."""
    if not module_name:
        return False
    if module_name == "builtins":
        return True
    if module_name in sys.builtin_module_names:
        return True

    try:
        module = __import__(module_name)
        if hasattr(module, "__file__") and module.__file__:
            return module.__file__.startswith(sys.base_prefix)
    except Exception:
        pass

    std_lib_names = {
        "pathlib",
        "datetime",
        "json",
        "os",
        "sys",
        "re",
        "typing",
        "logging",
        "argparse",
        "uuid",
        "enum",
        "math",
        "random",
        "io",
        "copy",
        "collections",
        "functools",
        "itertools",
        "hashlib",
        "base64",
    }
    return module_name in std_lib_names
