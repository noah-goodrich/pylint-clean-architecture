"""Boundary rules: Visibility (W9003), Resource (W9004)."""

from typing import TYPE_CHECKING, cast

import astroid

from excelsior_architect.domain.rules import Checkable, Violation

if TYPE_CHECKING:
    from excelsior_architect.domain.config import ConfigurationLoader
    from excelsior_architect.domain.protocols import PythonProtocol


class VisibilityRule(Checkable):
    """Rule for W9003: Protected member access across layers."""

    code: str = "W9003"
    description: str = "Visibility: protected member access across layers."
    fix_type: str = "code"

    def __init__(self, config_loader: "ConfigurationLoader") -> None:
        self._config_loader = config_loader

    def check(self, node: astroid.nodes.NodeNG) -> list[Violation]:
        """Check an attribute node for W9003. Returns at most one violation."""
        # Check for attribute-specific features instead of isinstance for mock compatibility
        attrname = getattr(node, "attrname", None)
        if attrname is None or not isinstance(attrname, str):
            return []
        # Only Attribute nodes have 'expr', so this ensures type safety
        if not hasattr(node, "expr"):
            return []
        # Cast for type checker after runtime check
        attr_node = cast(astroid.nodes.Attribute, node)
        if not getattr(self._config_loader, "visibility_enforcement", True):
            return []
        if not attrname.startswith("_") or attrname.startswith("__"):
            return []
        if self._receiver_is_self_or_cls(attr_node):
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
            return defaults.union({str(p) for p in raw})
        return defaults

    def check(self, node: astroid.nodes.NodeNG) -> list[Violation]:
        """Check an import node for W9004. Returns at most one violation (first forbidden name)."""
        from excelsior_architect.domain.layer_registry import LayerRegistry

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
        return all(not (name == allowed or name.startswith(allowed + ".")) for allowed in self.allowed_prefixes)


class IllegalIOCallRule(Checkable):
    """Rule for W9013: Illegal I/O call (print, input, open, Path, subprocess, etc.) in Domain/UseCase layers."""

    code: str = "W9013"
    description: str = "Illegal I/O call in Domain/UseCase layer."
    fix_type: str = "code"

    # Builtin or common I/O call names that are forbidden in domain/use_case
    FORBIDDEN_CALL_NAMES: set[str] = {
        "print", "input", "open",
    }
    # Qualified names (module.attr) that are forbidden
    FORBIDDEN_QUALIFIED: set[str] = {
        "pathlib.Path", "os.makedirs", "os.path.join", "subprocess.run",
        "subprocess.call", "subprocess.check_call", "subprocess.Popen",
    }

    def __init__(
        self,
        python_gateway: "PythonProtocol",
        config_loader: "ConfigurationLoader",
    ) -> None:
        self._python_gateway = python_gateway
        self._config_loader = config_loader

    def check(self, node: astroid.nodes.NodeNG) -> list[Violation]:
        """Check a Call node for W9013. Returns at most one violation."""
        from excelsior_architect.domain.layer_registry import LayerRegistry

        if not hasattr(node, "func"):
            return []
        call_node = cast(astroid.nodes.Call, node)
        if self._is_test_file(call_node):
            return []
        layer = self._python_gateway.get_node_layer(
            call_node, self._config_loader)
        if layer not in (LayerRegistry.LAYER_USE_CASE, LayerRegistry.LAYER_DOMAIN):
            return []
        called = self._called_name(call_node)
        if not called:
            return []
        hint = "UIOutputPort or FileSystemProtocol"
        if called in self.FORBIDDEN_CALL_NAMES:
            return [
                Violation.from_node(
                    code=self.code,
                    message=f"Illegal I/O call: {called}() in {layer} layer.",
                    node=call_node,
                    message_args=(called, layer, hint),
                )
            ]
        if called in self.FORBIDDEN_QUALIFIED:
            return [
                Violation.from_node(
                    code=self.code,
                    message=f"Illegal I/O call: {called}() in {layer} layer.",
                    node=call_node,
                    message_args=(called, layer, hint),
                )
            ]
        return []

    def _called_name(self, node: astroid.nodes.Call) -> str | None:
        """Return the called function name or qualified name (e.g. 'print', 'pathlib.Path')."""
        func = getattr(node, "func", None)
        if func is None:
            return None
        if isinstance(func, astroid.nodes.Name):
            return getattr(func, "name", None) or None
        if isinstance(func, astroid.nodes.Attribute):
            expr = getattr(func, "expr", None)
            attr = getattr(func, "attrname", None)
            if not attr:
                return None
            if isinstance(expr, astroid.nodes.Name):
                mod = getattr(expr, "name", None)
                return f"{mod}.{attr}" if mod else attr
            if isinstance(expr, astroid.nodes.Attribute):
                inner = self._attr_chain(expr)
                return f"{inner}.{attr}" if inner else attr
        return None

    def _attr_chain(self, node: astroid.nodes.Attribute) -> str:
        """Build qualified name from Attribute chain (e.g. pathlib.Path -> pathlib.Path)."""
        parts: list[str] = [getattr(node, "attrname", "") or ""]
        expr = getattr(node, "expr", None)
        while isinstance(expr, astroid.nodes.Attribute):
            parts.append(getattr(expr, "attrname", "") or "")
            expr = getattr(expr, "expr", None)
        if isinstance(expr, astroid.nodes.Name):
            parts.append(getattr(expr, "name", "") or "")
        parts.reverse()
        return ".".join(p for p in parts if p)

    def _is_test_file(self, node: astroid.nodes.NodeNG) -> bool:
        root = node.root()
        file_path: str = getattr(root, "file", "") or ""
        module_name: str = getattr(root, "name", "") or ""
        normalized_path = file_path.replace("\\", "/")
        parts = normalized_path.split("/")
        return (
            "tests" in parts or "test" in parts or
            (module_name.startswith("test_")
             if module_name else False) or ".tests." in module_name
        )


class UIConcernRule(Checkable):
    """Rule for W9014: UI concern (ANSI codes, emoji, isatty) in Domain layer."""

    code: str = "W9014"
    description: str = "UI concern in Domain layer."
    fix_type: str = "code"

    # ANSI escape patterns in string literals
    ANSI_PATTERNS: tuple[str, ...] = ("\\033[", "\\x1b[", "\033[", "\x1b[")

    def __init__(
        self,
        python_gateway: "PythonProtocol",
        config_loader: "ConfigurationLoader",
    ) -> None:
        self._python_gateway = python_gateway
        self._config_loader = config_loader

    def check_call(self, node: astroid.nodes.Call) -> list[Violation]:
        """Check Call for sys.stdin.isatty() etc. in Domain/UseCase."""
        from excelsior_architect.domain.layer_registry import LayerRegistry

        if self._is_test_file(node):
            return []
        layer = self._python_gateway.get_node_layer(node, self._config_loader)
        if layer not in (LayerRegistry.LAYER_USE_CASE, LayerRegistry.LAYER_DOMAIN):
            return []
        func = getattr(node, "func", None)
        if not isinstance(func, astroid.nodes.Attribute):
            return []
        attr = getattr(func, "attrname", None)
        if attr != "isatty":
            return []
        expr = getattr(func, "expr", None)
        if isinstance(expr, astroid.nodes.Attribute):
            if getattr(expr, "attrname", None) == "stdin":
                inner = getattr(expr, "expr", None)
                if isinstance(inner, astroid.nodes.Name) and getattr(inner, "name", None) == "sys":
                    return [
                        Violation.from_node(
                            code=self.code,
                            message="UI concern: sys.stdin.isatty() in silent layer.",
                            node=node,
                            message_args=("sys.stdin.isatty()",),
                        )
                    ]
        return []

    def check_const(self, node: astroid.nodes.NodeNG) -> list[Violation]:
        """Check Const (string) for ANSI codes or emoji in Domain layer."""
        from excelsior_architect.domain.layer_registry import LayerRegistry

        if not hasattr(node, "value") or not isinstance(getattr(node, "value"), str):
            return []
        if self._is_test_file(node):
            return []
        layer = self._python_gateway.get_node_layer(node, self._config_loader)
        if layer != LayerRegistry.LAYER_DOMAIN:
            return []
        value = getattr(node, "value", "")
        for pattern in self.ANSI_PATTERNS:
            if pattern in value:
                return [
                    Violation.from_node(
                        code=self.code,
                        message="UI concern: ANSI escape codes in Domain layer.",
                        node=node,
                        message_args=("ANSI escape codes in string",),
                    )
                ]
        # Simple emoji check: common Unicode emoji ranges (simplified)
        for ch in value:
            if ord(ch) >= 0x1F300 and ord(ch) <= 0x1F9FF:
                return [
                    Violation.from_node(
                        code=self.code,
                        message="UI concern: emoji in Domain layer.",
                        node=node,
                        message_args=("emoji in string",),
                    )
                ]
        return []
