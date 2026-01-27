
import ast
import logging
from typing import Optional, Set

from typeshed_client import finder

from clean_architecture_linter.domain.protocols import TypeshedProtocol


def _annotation_to_qname(anno: ast.expr) -> Optional[str]:
    """Map a typeshed annotation node to a qname (e.g. builtins.str, builtins.dict)."""
    if isinstance(anno, ast.Name):
        n = anno.id
        if n in ("str", "int", "float", "bool", "list", "dict", "set", "bytes", "tuple", "type"):
            return f"builtins.{n}"
        return n
    if isinstance(anno, ast.Constant) and isinstance(anno.value, str):
        n = anno.value
        if n in ("str", "int", "float", "bool", "list", "dict", "set", "bytes", "tuple", "type"):
            return f"builtins.{n}"
        return n
    if isinstance(anno, ast.Subscript):
        val = anno.value
        if isinstance(val, ast.Name):
            if val.id in ("Optional", "Union"):
                s = anno.slice
                elts = s.elts if isinstance(s, ast.Tuple) else [s]
                for e in elts:
                    r = _annotation_to_qname(e)
                    if r and "None" not in r:
                        return r
            if val.id == "Dict":
                return "builtins.dict"
            if val.id == "List":
                return "builtins.list"
        if isinstance(val, ast.Attribute) and isinstance(val.value, ast.Name):
            if val.value.id == "typing" and val.attr == "Dict":
                return "builtins.dict"
    if isinstance(anno, ast.Attribute) and isinstance(anno.value, ast.Name):
        return f"{anno.value.id}.{anno.attr}"
    return None


class TypeshedService(TypeshedProtocol):
    """Service to interact with typeshed stubs via typeshed-client."""

    _instance: Optional["TypeshedService"] = None
    _stdlib_modules: Set[str] = set()

    def __new__(cls) -> "TypeshedService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # Inline stdlib init to avoid protected method call from __new__
            try:
                _ = finder.get_search_context()  # Reserved for future use
            except Exception:
                logging.warning("Failed to initialize TypeshedService")
        return cls._instance

    def is_stdlib_module(self, module_name: str) -> bool:
        """Check if a module is part of the standard library."""
        try:
            # We use finder to look up the stub.
            # If it's found in the stdlib portion of typeshed, it's stdlib.
            # typeshed-client 2.0+ uses get_stub_file
            stub = finder.get_stub_file(module_name)

            if not stub:
                return False

            stub_path = str(stub)
            # Rough heuristic: typeshed keeps stdlib stubs in a 'stdlib' folder
            # OR top-level in bundled typeshed (e.g. .../typeshed/os/...)
            # We trust everything in the bundled typeshed that isn't explicitly third-party stubs?
            # Actually, typeshed-client includes stdlib.

            if "stdlib" in stub_path:
                return True

            # If it's in the stubs folder of typeshed, it's third-party
            if "typeshed/stubs/" in stub_path or "typeshed_client/typeshed/stubs/" in stub_path:
                 return False

            # If path contains 'typeshed_client/typeshed/', it's likely stdlib info from the bundle
            if "typeshed_client/typeshed/" in stub_path:
                 return True

            return False

        except ImportError:
            # Fallback if typeshed_client not installed/working
            return False
        except Exception:
            return False

    def is_stdlib_qname(self, qname: str) -> bool:
        """Check if a fully qualified name originates from stdlib."""
        if not qname:
            return False
        module_part = qname.split(".")[0]
        return self.is_stdlib_module(module_part)

    def get_attribute_type_from_stub(
        self, class_qname: str, attr_name: str
    ) -> Optional[str]:
        """Resolve an attribute's type from typeshed stubs (stdlib only)."""
        parts = class_qname.split(".")
        if len(parts) < 2:
            return None
        module_name = ".".join(parts[:-1])
        class_name = parts[-1]
        if not self.is_stdlib_module(module_name):
            return None
        try:
            stub = finder.get_stub_file(module_name)
            if not stub:
                return None
            with open(str(stub), encoding="utf-8") as f:
                tree = ast.parse(f.read())
        except (OSError, SyntaxError, ImportError):
            return None
        return _find_attr_in_module_ast(tree, class_name, attr_name)


def _find_attr_in_module_ast(
    tree: ast.Module, class_name: str, attr_name: str
) -> Optional[str]:
    """Find attribute type in a parsed .pyi: AnnAssign or @property in class/bases."""
    classes = {n.name: n for n in tree.body if isinstance(n, ast.ClassDef)}

    def find_in_class(node: ast.ClassDef) -> Optional[str]:
        for stmt in node.body:
            if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                if stmt.target.id == attr_name and stmt.annotation:
                    return _annotation_to_qname(stmt.annotation)
            if isinstance(stmt, ast.FunctionDef) and stmt.name == attr_name:
                is_prop = any(
                    isinstance(d, ast.Name) and d.id == "property"
                    for d in stmt.decorator_list
                )
                if is_prop and stmt.returns:
                    return _annotation_to_qname(stmt.returns)
        for base in node.bases:
            base_name = None
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
