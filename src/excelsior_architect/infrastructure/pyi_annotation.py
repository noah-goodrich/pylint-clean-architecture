"""
Shared .pyi / stub annotation parsing: primitives, subscripts, and attribute lookup.

Used by StubAuthority (bundled stubs, project stubs) and TypeshedService (typeshed).
No top-level functions (W9018).
"""

import ast

PRIMITIVE_IDS = frozenset[str](
    {"str", "int", "float", "bool", "list", "dict", "set", "bytes", "tuple", "type"}
)


class PyiAnnotationHelper:
    """Static helpers for .pyi annotation parsing. No top-level functions (W9018)."""

    @staticmethod
    def primitive_or_name(n: str) -> str:
        """Return builtins.n if n is a primitive, else n."""
        return f"builtins.{n}" if n in PRIMITIVE_IDS else n

    @staticmethod
    def subscript_to_qname(anno: ast.Subscript) -> str | None:
        """Map a Subscript annotation (Optional, Union, Dict, List, typing.Dict) to qname."""
        val = anno.value
        if isinstance(val, ast.Name):
            if val.id in ("Optional", "Union"):
                s = anno.slice
                elts = s.elts if isinstance(s, ast.Tuple) else [s]
                for e in elts:
                    r = PyiAnnotationHelper.annotation_to_qname(e)
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

    @staticmethod
    def annotation_to_qname(anno: ast.expr) -> str | None:
        """Map a .pyi annotation to a qname (e.g. builtins.str, builtins.dict)."""
        if isinstance(anno, ast.Name):
            return PyiAnnotationHelper.primitive_or_name(anno.id)
        if isinstance(anno, ast.Constant) and isinstance(anno.value, str):
            return PyiAnnotationHelper.primitive_or_name(anno.value)
        if isinstance(anno, ast.Subscript):
            return PyiAnnotationHelper.subscript_to_qname(anno)
        if isinstance(anno, ast.Attribute) and isinstance(anno.value, ast.Name):
            return f"{anno.value.id}.{anno.attr}"
        return None

    @staticmethod
    def attr_from_stmt(stmt: ast.stmt, attr_name: str) -> str | None:
        """Get attribute type from AnnAssign or @property FunctionDef, or None."""
        if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
            if stmt.target.id == attr_name and stmt.annotation:
                return PyiAnnotationHelper.annotation_to_qname(stmt.annotation)
        if isinstance(stmt, ast.FunctionDef) and stmt.name == attr_name:
            is_prop = any(
                isinstance(d, ast.Name) and d.id == "property"
                for d in stmt.decorator_list
            )
            if is_prop and stmt.returns:
                return PyiAnnotationHelper.annotation_to_qname(stmt.returns)
        return None

    @staticmethod
    def find_attr_in_ast(
        tree: ast.Module, class_name: str, attr_name: str
    ) -> str | None:
        """Find attribute type in a parsed .pyi: AnnAssign or @property in class/bases."""
        classes = {n.name: n for n in tree.body if isinstance(n, ast.ClassDef)}

        def find_in_class(node: ast.ClassDef) -> str | None:
            for stmt in node.body:
                r = PyiAnnotationHelper.attr_from_stmt(stmt, attr_name)
                if r:
                    return r
            for base in node.bases:
                base_name: str | None = None
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
