"""Boundary rules: Visibility (W9003), Resource (W9004)."""

from typing import TYPE_CHECKING

import astroid  # type: ignore[import-untyped]

from clean_architecture_linter.domain.rules import Checkable, Violation

if TYPE_CHECKING:
    from clean_architecture_linter.domain.config import ConfigurationLoader
    from clean_architecture_linter.domain.protocols import PythonProtocol


class VisibilityRule(Checkable):
    """Rule for W9003: Protected member access across layers."""

    code: str = "W9003"
    description: str = "Visibility: protected member access across layers."
    fix_type: str = "code"

    def __init__(self, config_loader: "ConfigurationLoader") -> None:
        self._config_loader = config_loader

    def check(self, node: astroid.nodes.NodeNG) -> list[Violation]:
        """Check an attribute node for W9003. Returns at most one violation."""
        attrname = getattr(node, "attrname", None)
        if attrname is None or not isinstance(attrname, str):
            return []
        if not getattr(self._config_loader, "visibility_enforcement", True):
            return []
        if not attrname.startswith("_") or attrname.startswith("__"):
            return []
        if self._receiver_is_self_or_cls(node):
            return []
        return [
            Violation.from_node(
                code=self.code,
                message=f"Protected member access: {attrname}.",
                node=node,
                message_args=(attrname,),
            )
        ]

    def _receiver_is_self_or_cls(self, node: astroid.nodes.Attribute) -> bool:
        expr = node.expr
        while isinstance(expr, astroid.nodes.Attribute):
            expr = getattr(expr, "expr", expr)
        if isinstance(expr, astroid.nodes.Name):
            return getattr(expr, "name", "") in ("self", "cls")
        return False


class ResourceRule(Checkable):
    """Rule for W9004: Forbidden I/O access in UseCase/Domain layers."""

    code: str = "W9004"
    description: str = "Resource: forbidden I/O imports in UseCase/Domain."
    fix_type: str = "code"

    def __init__(
        self,
        python_gateway: "PythonProtocol",
        config_loader: "ConfigurationLoader",
    ) -> None:
        self._python_gateway = python_gateway
        self._config_loader = config_loader

    @property
    def allowed_prefixes(self) -> set[str]:
        defaults: set[str] = {
            "__future__", "typing", "dataclasses", "abc", "enum", "pathlib", "logging",
            "datetime", "uuid", "re", "math", "random", "decimal",
            "functools", "itertools", "collections", "contextlib", "json",
        }
        raw = self._config_loader.config.get("allowed_prefixes", [])
        if isinstance(raw, list):
            return defaults.union(set(str(p) for p in raw))
        return defaults

    def check(self, node: astroid.nodes.NodeNG) -> list[Violation]:
        """Check an import node for W9004. Returns at most one violation (first forbidden name)."""
        from clean_architecture_linter.domain.layer_registry import LayerRegistry

        names_attr = getattr(node, "names", None)
        modname = getattr(node, "modname", None)
        if isinstance(modname, str) and modname:
            names = [modname]
        elif names_attr is not None:
            names = [n[0] if isinstance(
                n, (list, tuple)) else n for n in names_attr]
            names = [str(n) for n in names]
        else:
            return []

        if self._is_test_file(node):
            return []
        if self._is_inside_type_checking(node):
            return []
        layer = self._python_gateway.get_node_layer(node, self._config_loader)
        if layer not in (LayerRegistry.LAYER_USE_CASE, LayerRegistry.LAYER_DOMAIN):
            return []
        for name in names:
            if self._is_forbidden(name):
                return [
                    Violation.from_node(
                        code=self.code,
                        message=f"Forbidden I/O import: {name}.",
                        node=node,
                        message_args=(f"import {name}", layer),
                    )
                ]
        return []

    def _is_test_file(self, node: astroid.nodes.NodeNG) -> bool:
        root = node.root()
        file_path: str = getattr(root, "file", "") or ""
        if not isinstance(file_path, str):
            file_path = ""
        module_name: str = getattr(root, "name", "") or ""
        if not isinstance(module_name, str):
            module_name = ""
        normalized_path = file_path.replace("\\", "/")
        parts = normalized_path.split("/")
        return (
            "tests" in parts or "test" in parts or
            (module_name.startswith("test_")
             if module_name else False) or ".tests." in module_name
        )

    def _is_inside_type_checking(self, node: astroid.nodes.NodeNG) -> bool:
        parent = getattr(node, "parent", None)
        depth = 0
        while parent is not None and depth < 1000:
            if isinstance(parent, astroid.nodes.If):
                test = getattr(parent, "test", None)
                if isinstance(test, astroid.nodes.Name) and getattr(test, "name", None) == "TYPE_CHECKING":
                    return True
            parent = getattr(parent, "parent", None)
            depth += 1
        return False

    def _is_forbidden(self, name: str) -> bool:
        parts = name.split(".")
        if any(p in parts for p in self._config_loader.internal_modules):
            return False
        for allowed in self.allowed_prefixes:
            if name == allowed or name.startswith(allowed + "."):
                return False
        return True
