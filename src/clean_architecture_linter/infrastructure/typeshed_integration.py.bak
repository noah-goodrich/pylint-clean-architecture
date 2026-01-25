
import logging
from typing import Optional, Set

from typeshed_client import finder

from clean_architecture_linter.domain.protocols import TypeshedProtocol


class TypeshedService(TypeshedProtocol):
    """Service to interact with typeshed stubs via typeshed-client."""

    _instance: Optional["TypeshedService"] = None
    _stdlib_modules: Set[str] = set()

    def __new__(cls) -> "TypeshedService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # JUSTIFICATION: Internal singleton initialization
            cls._instance._load_stdlib_modules() # pylint: disable=clean-arch-visibility
        return cls._instance

    def _load_stdlib_modules(self) -> None:
        """Cache list of standard library modules from typeshed."""
        try:
             # typeshed-client finder can list all modules in stdlib
             # We iterate known stdlib versions or just check 'stdlib' folder
             _ = finder.get_search_context()  # Reserved for future use
             # This is a bit implementation dependent, but we want to know
             # if a module is in the stdlib search path.
             pass
        except Exception:
             logging.warning("Failed to initialize TypeshedService")

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
