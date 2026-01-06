"""Domain Immutability checks (W9401)."""

import astroid
from pylint.checkers import BaseChecker
from clean_architecture_linter.config import ConfigurationLoader
from clean_architecture_linter.helpers import get_node_layer


class ImmutabilityChecker(BaseChecker):
    """W9401: Domain Immutability enforcement."""

    name = "clean-arch-immutability"
    msgs = {
        "W9401": (
            "Domain Mutability Violation: Class %s must be immutable. Use @dataclass(frozen=True).",
            "domain-mutability-violation",
            "Classes in domain/entities.py or decorated with @dataclass must use (frozen=True).",
        ),
    }

    def __init__(self, linter=None):
        super().__init__(linter)
        self.config_loader = ConfigurationLoader()

    def visit_classdef(self, node):
        """
        Check for domain entity immutability.
        """
        # 1. Resolve architectural layer
        layer = get_node_layer(node, self.config_loader)
        if layer != "Domain":
            return

        # 2. Identify if this is in entities.py
        root = node.root()
        file_path = getattr(root, "file", "")
        current_module = root.name
        normalized_path = file_path.replace("\\", "/")
        is_entities = (
            "domain/entities.py" in normalized_path or
            current_module.endswith("domain.entities")
        )

        # 3. Check for @dataclass decorator
        has_dataclass = False
        is_frozen = False
        if node.decorators:
            for decorator in node.decorators.nodes:
                if self._is_dataclass_decorator(decorator):
                    has_dataclass = True
                    if self._is_frozen_dataclass(decorator):
                        is_frozen = True
                    break

        # 4. Enforce rules
        # Rule: All classes in domain/entities.py MUST be frozen dataclasses
        if is_entities:
            if not (has_dataclass and is_frozen):
                self.add_message("domain-mutability-violation", node=node, args=(node.name,))
                return

        # Rule: Any class decorated with @dataclass in Domain layer MUST be frozen
        if has_dataclass and not is_frozen:
            self.add_message("domain-mutability-violation", node=node, args=(node.name,))

    def _is_dataclass_decorator(self, node):
        """Check if decorator is @dataclass."""
        if isinstance(node, astroid.nodes.Name):
            return node.name == "dataclass"
        if isinstance(node, astroid.nodes.Attribute):
            return node.attrname == "dataclass"
        if isinstance(node, astroid.nodes.Call):
            func = node.func
            if isinstance(func, astroid.nodes.Name):
                return func.name == "dataclass"
            if isinstance(func, astroid.nodes.Attribute):
                return func.attrname == "dataclass"
        return False

    def _is_frozen_dataclass(self, node):
        """Check if @dataclass(frozen=True) is used."""
        if not isinstance(node, astroid.nodes.Call):
            return False # Bare @dataclass is not frozen by default

        for keyword in node.keywords or []:
            if keyword.arg == "frozen":
                if isinstance(keyword.value, astroid.nodes.Const):
                    return bool(keyword.value.value)
        return False
