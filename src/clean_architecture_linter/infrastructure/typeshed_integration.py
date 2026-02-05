import ast
import logging
from typing import Optional

from typeshed_client import finder

from clean_architecture_linter.domain.protocols import TypeshedProtocol
from clean_architecture_linter.infrastructure.pyi_annotation import PyiAnnotationHelper


class TypeshedService(TypeshedProtocol):
    """Service to interact with typeshed stubs via typeshed-client."""

    _instance: Optional["TypeshedService"] = None
    _stdlib_modules: set[str] = set()

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
        return PyiAnnotationHelper.find_attr_in_ast(tree, class_name, attr_name)
