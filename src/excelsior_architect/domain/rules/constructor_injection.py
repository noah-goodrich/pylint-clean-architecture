"""Constructor Injection rule (W9034): dependencies via __init__, typed to protocols."""

from typing import TYPE_CHECKING, ClassVar

import astroid

from excelsior_architect.domain.rules import Checkable, Violation

if TYPE_CHECKING:
    from excelsior_architect.domain.config import ConfigurationLoader


class ConstructorInjectionRule(Checkable):
    """Rule for W9034: Dependencies must be received via __init__ and typed to protocols, not concrete classes."""

    code: str = "W9034"
    description: str = "Constructor Injection: use __init__ for deps; type to Protocol, not concrete class."
    fix_type: str = "code"

    CONCRETE_SUFFIXES: ClassVar[tuple[str, ...]] = (
        "Gateway", "Repository", "Client", "Adapter", "Service",
        "Reporter", "Storage", "Checker", "Scaffolder", "Renderer",
    )

    def __init__(self, config_loader: "ConfigurationLoader | None" = None) -> None:
        self._config_loader = config_loader

    def check(self, node: astroid.nodes.NodeNG) -> list[Violation]:
        """Check __init__ of a class: params typed to concrete infra types (not Protocol) -> W9034."""
        if not isinstance(node, astroid.nodes.FunctionDef):
            return []
        if getattr(node, "name", "") != "__init__":
            return []
        parent = node.parent
        if not isinstance(parent, astroid.nodes.ClassDef):
            return []
        violations: list[Violation] = []
        args = getattr(node, "args", None)
        if not args or not getattr(args, "annotations", None):
            return []
        for i, ann in enumerate(args.annotations):
            if not ann or i >= len(args.args):
                continue
            arg_name = args.args[i].name
            if arg_name in ("self", "cls"):
                continue
            type_name = self._annotation_to_name(ann)
            if not type_name:
                continue
            bare = type_name.split(".")[-1]
            if not any(bare.endswith(s) for s in self.CONCRETE_SUFFIXES):
                continue
            if self._is_protocol_annotation(ann):
                continue
            class_name = getattr(parent, "name", "?")
            violations.append(
                Violation.from_node(
                    code=self.code,
                    message=f"Parameter '{arg_name}' in {class_name}.__init__ is typed to concrete '{bare}'. Prefer a Protocol and inject the implementation.",
                    node=node,
                    message_args=(arg_name, class_name, bare),
                )
            )
        return violations

    def _annotation_to_name(self, node: astroid.nodes.NodeNG) -> str:
        """Best-effort type name from annotation node."""
        if isinstance(node, astroid.nodes.Name):
            return getattr(node, "name", "") or ""
        if isinstance(node, astroid.nodes.Attribute):
            return getattr(node, "as_string", lambda: "")() or ""
        if isinstance(node, astroid.nodes.Subscript):
            value = getattr(node, "value", None)
            if value:
                return self._annotation_to_name(value)
        return ""

    def _is_protocol_annotation(self, node: astroid.nodes.NodeNG) -> bool:
        """True if annotation is or uses Protocol (e.g. SomeProtocol)."""
        name = self._annotation_to_name(node)
        return "Protocol" in name or name.endswith("Protocol")
