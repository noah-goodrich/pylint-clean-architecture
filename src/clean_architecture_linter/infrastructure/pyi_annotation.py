"""
Shared .pyi / stub annotation parsing: primitives, subscripts, and attribute lookup.

Used by StubAuthority (stubs/core, project stubs) and TypeshedService (typeshed).
"""

import ast
from typing import Optional

PRIMITIVE_IDS = frozenset[str](
    {"str", "int", "float", "bool", "list", "dict", "set", "bytes", "tuple", "type"}
)


def primitive_or_name(n: str) -> str:
    """Return builtins.n if n is a primitive, else n."""
    return f"builtins.{n}" if n in PRIMITIVE_IDS else n


def subscript_to_qname(anno: ast.Subscript) -> Optional[str]:
    """Map a Subscript annotation (Optional, Union, Dict, List, typing.Dict) to qname."""
    val = anno.value
    if isinstance(val, ast.Name):
        if val.id in ("Optional", "Union"):
            s = anno.slice
            elts = s.elts if isinstance(s, ast.Tuple) else [s]
            for e in elts:
                r = annotation_to_qname(e)
                if r and "None" not in (r or ""):
                    return r
        if val.id in ("Dict", "dict"):
            return "builtins.dict"
        if val.id in ("List", "list"):
            return "builtins.list"
    if isinstance(val, ast.Attribute) and isinstance(val.value, ast.Name):
        if val.value.id == "typing" and val.attr == "Dict":
            return "builtins.dict"
    return None


def annotation_to_qname(anno: ast.expr) -> Optional[str]:
    """Map a .pyi annotation to a qname (e.g. builtins.str, builtins.dict)."""
    if isinstance(anno, ast.Name):
        return primitive_or_name(anno.id)
    if isinstance(anno, ast.Constant) and isinstance(anno.value, str):
        return primitive_or_name(anno.value)
    if isinstance(anno, ast.Subscript):
        return subscript_to_qname(anno)
    if isinstance(anno, ast.Attribute) and isinstance(anno.value, ast.Name):
        return f"{anno.value.id}.{anno.attr}"
    return None


def attr_from_stmt(stmt: ast.stmt, attr_name: str) -> Optional[str]:
    """Get attribute type from AnnAssign or @property FunctionDef, or None."""
    if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
        if stmt.target.id == attr_name and stmt.annotation:
            return annotation_to_qname(stmt.annotation)
    if isinstance(stmt, ast.FunctionDef) and stmt.name == attr_name:
        is_prop = any(
            isinstance(d, ast.Name) and d.id == "property"
            for d in stmt.decorator_list
        )
        if is_prop and stmt.returns:
            return annotation_to_qname(stmt.returns)
    return None


def find_attr_in_ast(
    tree: ast.Module, class_name: str, attr_name: str
) -> Optional[str]:
    """Find attribute type in a parsed .pyi: AnnAssign or @property in class/bases."""
    classes = {n.name: n for n in tree.body if isinstance(n, ast.ClassDef)}

    def find_in_class(node: ast.ClassDef) -> Optional[str]:
        for stmt in node.body:
            r = attr_from_stmt(stmt, attr_name)
            if r:
                return r
        for base in node.bases:
            base_name: Optional[str] = None
            if isinstance(base, ast.Name):
                base_name = base.id
            elif isinstance(base, ast.Attribute):
                base_name = base.attr
            if base_name and base_name in classes:
                res = find_in_class(classes[base_name])
                if res:
                    return res
        return None

    if class_name not in classes:
        return None
    return find_in_class(classes[class_name])
