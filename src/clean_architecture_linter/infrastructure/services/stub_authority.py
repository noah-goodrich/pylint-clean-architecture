"""
Stub Authority: Load and query .pyi files. Stub-First, no nominal maps.

Search order:
  1. src/clean_architecture_linter/stubs/core/ (built-in: astroid, linter internals)
  2. stubs/ at project root (project-local)
"""

import ast
from pathlib import Path
from typing import Optional

from clean_architecture_linter.infrastructure.pyi_annotation import find_attr_in_ast


def _core_stubs_dir() -> Path:
    """Path to stubs/core inside the clean_architecture_linter package."""
    # .../clean_architecture_linter/infrastructure/services/stub_authority.py
    # -> .../clean_architecture_linter
    pkg = Path(__file__).resolve().parent.parent.parent
    return pkg / "stubs" / "core"


class StubAuthority:
    """
    Load and query .pyi files. No nominal guessing.
    Search: 1) stubs/core (built-in), 2) project stubs/
    """

    def get_stub_path(
        self, module_name: str, project_root: Optional[str] = None
    ) -> Optional[str]:
        """
        Resolve a .pyi for a module. Returns path or None.
        - astroid / astroid.nodes -> stubs/core/astroid.pyi
        - Else: stubs/core/{a/b/c}.pyi then project stubs/{a/b/c}.pyi
        """
        core = _core_stubs_dir()
        # Core: astroid and astroid.nodes -> astroid.pyi
        if module_name in ("astroid", "astroid.nodes"):
            p = core / "astroid.pyi"
            return str(p) if p.exists() else None
        # Core: stubs/core/snowflake/connector.pyi for snowflake.connector
        rel = module_name.replace(".", "/") + ".pyi"
        p = core / rel
        if p.exists():
            return str(p)
        # Project: stubs/ at project root; e.g. stubs/snowflake/connector.pyi
        if project_root:
            cand = Path(project_root) / "stubs" / \
                (module_name.replace(".", "/") + ".pyi")
            if cand.exists():
                return str(cand)
        return None

    def get_attribute_type(
        self,
        module_name: str,
        class_name: str,
        attr_name: str,
        project_root: Optional[str] = None,
    ) -> Optional[str]:
        """
        Resolve an attribute's type from a .pyi. Returns qname (e.g. builtins.str)
        or None. Uses stubs/core for astroid/astroid.nodes and project stubs for
        other modules. When the requested module does not resolve, tries
        astroid.nodes once (handles mis-attributed builtins for node types).
        """
        result = self._get_attribute_type_impl(
            module_name, class_name, attr_name, project_root
        )
        if result is not None:
            return result
        # Single fallback: if the requested module did not resolve and we are not
        # already querying astroid.nodes, try the core astroid stub (e.g. for
        # ClassDef/FunctionDef/NodeNG when module was wrong or missing).
        if module_name not in ("astroid", "astroid.nodes"):
            return self._get_attribute_type_impl(
                "astroid.nodes", class_name, attr_name, project_root
            )
        return None

    def _get_attribute_type_impl(
        self,
        module_name: str,
        class_name: str,
        attr_name: str,
        project_root: Optional[str] = None,
    ) -> Optional[str]:
        """Internal: resolve from one module. No fallbacks."""
        stub_path: Optional[str] = None
        core = _core_stubs_dir()
        astroid_pyi = core / "astroid.pyi"
        if module_name in ("astroid", "astroid.nodes"):
            if astroid_pyi.exists():
                stub_path = str(astroid_pyi)
        if not stub_path:
            stub_path = self.get_stub_path(module_name, project_root)
        if not stub_path:
            return None
        try:
            with open(stub_path, encoding="utf-8") as f:
                tree = ast.parse(f.read())
        except (OSError, SyntaxError):
            return None
        return find_attr_in_ast(tree, class_name, attr_name)
