"""Domain Immutability Rule (W9601) - Auto-fix for frozen dataclasses."""

from typing import TYPE_CHECKING, Optional

import astroid  # type: ignore[import-untyped]

if TYPE_CHECKING:
    import libcst as cst

from clean_architecture_linter.domain.rules import Violation
from clean_architecture_linter.infrastructure.gateways.transformers import (
    FreezeDataclassTransformer,
)


class DomainImmutabilityRule:
    """
    Rule for W9601: Domain Immutability violations.

    Automatically converts Domain layer classes to frozen dataclasses.
    """

    code: str = "W9601"
    description: str = (
        "Domain Immutability: Domain entities must be immutable. "
        "Auto-fix: Converts to frozen dataclass."
    )
    fix_type: str = "code"

    def __init__(self) -> None:
        pass

    def check(self, node: astroid.nodes.NodeNG) -> list[Violation]:
        """
        Check for Domain Immutability violations.

        Note: Violations are detected by ImmutabilityChecker (Pylint checker).
        This check() is a no-op in the fix pipeline; violations are supplied
        by Pylint. fix() is invoked with those Violation instances.
        """
        return []

    def fix(self, violation: Violation) -> Optional["cst.CSTTransformer"]:
        """
        Return a transformer that converts class to frozen dataclass.

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

        # Use FreezeDataclassTransformer to add frozen=True
        return FreezeDataclassTransformer({
            "class_name": class_name
        })

    def get_fix_instructions(self, violation: Violation) -> str:
        """Provide human/AI instructions for manual fix."""
        return (
            "Convert the class to a frozen dataclass: "
            "1. Add @dataclass(frozen=True) decorator "
            "2. Add 'from dataclasses import dataclass' import "
            "3. Remove any custom __setattr__ methods"
        )
