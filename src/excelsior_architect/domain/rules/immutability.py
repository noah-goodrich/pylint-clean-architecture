"""Domain Immutability Rule (W9601) - Detection + auto-fix for frozen dataclasses."""

from typing import TYPE_CHECKING, Literal

import astroid

from excelsior_architect.domain.entities import TransformationPlan
from excelsior_architect.domain.rules import BaseRule, Violation

if TYPE_CHECKING:
    from excelsior_architect.domain.config import ConfigurationLoader
    from excelsior_architect.domain.protocols import PythonProtocol


class DomainImmutabilityRule(BaseRule):
    """
    Rule for W9601: Domain Immutability violations.

    - Detection: Domain layer classes must be immutable (frozen dataclasses),
      and attributes must not be reassigned outside of constructors.
    - Fix: Converts Domain classes to frozen dataclasses via TransformationPlan.
    """

    code: str = "W9601"
    description: str = (
        "Domain Immutability: Domain entities must be immutable. "
        "Auto-fix: Converts to frozen dataclass."
    )
    fix_type: Literal["code"] = "code"

    def __init__(
        self,
        python_gateway: "PythonProtocol | None" = None,
        config_loader: "ConfigurationLoader | None" = None,
    ) -> None:
        # python_gateway + config_loader are required for AST-side detection,
        # but optional for fix-only usage in the plan-fix pipeline.
        self._python_gateway = python_gateway
        self._config_loader = config_loader

    # --------------------------------------------------------------------- #
    # BaseRule-style detection entrypoint
    # --------------------------------------------------------------------- #

    def check(self, node: astroid.nodes.NodeNG) -> list[Violation]:
        """
        Check for Domain Immutability violations.

        When constructed with python_gateway + config_loader, this can be used
        directly from the ImmutabilityChecker. In the fix pipeline, violations
        typically come from the checker and this method is a no-op.
        """
        # If gateways are not wired (plan-fix pipeline), detection is a no-op.
        if self._python_gateway is None or self._config_loader is None:
            return []

        if isinstance(node, astroid.nodes.AssignAttr):
            return self.check_assignattr(node)
        if isinstance(node, astroid.nodes.ClassDef):
            return self.check_classdef(node)
        return []

    # --------------------------------------------------------------------- #
    # AST-side detection helpers (used by both checker and check())
    # --------------------------------------------------------------------- #

    def check_assignattr(self, node: astroid.nodes.NodeNG) -> list[Violation]:
        """Check AssignAttr for W9601. Returns at most one violation."""
        from excelsior_architect.domain.layer_registry import LayerRegistry

        if self._python_gateway is None or self._config_loader is None:
            return []
        if not hasattr(node, "attrname"):
            return []

        layer = self._python_gateway.get_node_layer(node, self._config_loader)
        if layer != LayerRegistry.LAYER_DOMAIN:
            return []

        frame = getattr(node, "frame", lambda: None)()
        if frame and getattr(frame, "name", None) in ("__init__", "__new__"):
            return []

        return [
            Violation.from_node(
                code=self.code,
                message=f"Domain immutability: attribute assignment in {layer}.",
                node=node,
                message_args=(layer,),
            )
        ]

    def check_classdef(self, node: astroid.nodes.NodeNG) -> list[Violation]:
        """Check ClassDef for W9601 (dataclass not frozen). Returns at most one violation."""
        from excelsior_architect.domain.layer_registry import LayerRegistry

        if self._python_gateway is None or self._config_loader is None:
            return []
        if not hasattr(node, "decorators") or not node.decorators:
            return []

        layer = self._python_gateway.get_node_layer(node, self._config_loader)
        if layer != LayerRegistry.LAYER_DOMAIN:
            return []

        is_dataclass, is_frozen = self._dataclass_frozen_from_decorators(
            getattr(node.decorators, "nodes", [])
        )
        if not is_dataclass or is_frozen:
            return []

        return [
            Violation.from_node(
                code=self.code,
                message=(
                    f"Domain immutability: dataclass in {layer} must be frozen."
                ),
                node=node,
                message_args=(layer,),
            )
        ]

    def _dataclass_frozen_from_decorators(
        self, decorators: list[astroid.nodes.NodeNG]
    ) -> tuple[bool, bool]:
        is_dataclass = False
        is_frozen = False
        for dec in decorators or []:
            if self._is_dataclass_name(dec):
                is_dataclass = True
            elif hasattr(dec, "keywords") and dec.keywords:
                if self._is_dataclass_name(getattr(dec, "func", None)):
                    is_dataclass = True
                for kw in dec.keywords:
                    if (
                        getattr(kw, "arg", None) == "frozen"
                        and getattr(getattr(kw, "value", None), "value", None)
                        is True
                    ):
                        is_frozen = True
                        break
        return (is_dataclass, is_frozen)

    def _is_dataclass_name(self, n: astroid.nodes.NodeNG | None) -> bool:
        if n is None:
            return False
        if hasattr(n, "name"):
            return getattr(n, "name", None) == "dataclass"
        if hasattr(n, "attrname"):
            return getattr(n, "attrname", None) == "dataclass"
        return False

    # --------------------------------------------------------------------- #
    # Fix pipeline
    # --------------------------------------------------------------------- #

    def fix(self, violation: Violation) -> TransformationPlan | None:
        """
        Return a transformation plan to convert class to frozen dataclass.

        Safety checks:
        - Aborts if custom __setattr__ is detected
        - Only applies to Domain layer classes
        """
        if violation.code not in (self.code, "domain-immutability-violation"):
            return None

        # Check for custom __setattr__ - abort if found
        # Only check methods defined in this class, not inherited ones
        node = violation.node
        if isinstance(node, astroid.nodes.ClassDef):
            # Check only methods defined directly in this class (not inherited)
            for method in node.locals.get("__setattr__", []):
                if isinstance(method, astroid.nodes.FunctionDef):
                    # Custom __setattr__ detected - cannot safely convert
                    return None

        # Extract class name from violation
        class_name = None
        if isinstance(node, astroid.nodes.ClassDef):
            class_name = node.name
        elif isinstance(node, astroid.nodes.AssignAttr):
            # For attribute assignment violations, get the class
            frame = node.frame()
            if isinstance(frame, astroid.nodes.ClassDef):
                class_name = frame.name

        if not class_name:
            return None

        # Return plan - fixer gateway will interpret and apply
        return TransformationPlan.freeze_dataclass(class_name)

    def get_fix_instructions(self, violation: Violation) -> str:
        """Provide human/AI instructions for manual fix."""
        return (
            "Convert the class to a frozen dataclass: "
            "1. Add @dataclass(frozen=True) decorator "
            "2. Add 'from dataclasses import dataclass' import "
            "3. Remove any custom __setattr__ methods"
        )
