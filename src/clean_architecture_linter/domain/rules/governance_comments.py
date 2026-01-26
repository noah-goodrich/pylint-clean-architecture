"""Governance Comment Rules - Inject contextual guidance for manual-fix violations."""

from typing import TYPE_CHECKING, List, Optional

import astroid  # type: ignore[import-untyped]

if TYPE_CHECKING:
    import libcst as cst

from clean_architecture_linter.domain.rules import Violation
from clean_architecture_linter.infrastructure.gateways.transformers import (
    GovernanceCommentTransformer,
)


class LawOfDemeterRule:
    """
    Rule for W9006: Law of Demeter violations.

    Injects governance comments above violations to provide contextual
    guidance for both humans and AI (Cursor) to understand and fix the issue.
    """

    code: str = "W9006"
    description: str = (
        "Law of Demeter: Chain access exceeds one level. "
        "Governance comment will be injected to guide fix."
    )

    def __init__(self) -> None:
        pass

    def check(self, node: astroid.nodes.NodeNG) -> List[Violation]:
        """
        Check for Law of Demeter violations.

        Note: This is a simplified implementation. In practice, violations
        are detected by Pylint's CouplingChecker. This method would ideally
        bridge from Pylint violations or re-check using astroid.

        For now, this returns an empty list - violations come from Pylint,
        and we'll handle them in fix() when called with a Violation.
        """
        # TODO: Bridge from Pylint violations or re-implement detection
        return []

    def fix(self, violation: Violation) -> Optional["cst.CSTTransformer"]:
        """
        Return a transformer that injects governance comment above the violation.

        The comment provides:
        - Rule code and name
        - Specific problem description
        - Actionable recommendation
        - Contextual details
        """
        if violation.code != self.code:
            return None

        # Extract line number from violation location
        # Location format: "path:line:column" or "path:line"
        location_parts = violation.location.split(":")
        target_line = int(location_parts[1]) if len(location_parts) > 1 else 0

        # Extract chain information from message
        # Message format: "Law of Demeter: Chain access (%s) exceeds one level..."
        chain_info = ""
        if "%s" in violation.message or "Chain access" in violation.message:
            # Try to extract the chain from message
            # Example: "Law of Demeter: Chain access (repo.session.query) exceeds one level"
            if "(" in violation.message and ")" in violation.message:
                start = violation.message.find("(") + 1
                end = violation.message.find(")")
                chain_info = violation.message[start:end]

        # Build problem description
        problem = f"Chain access '{chain_info}' exceeds one level of indirection."
        if chain_info:
            # Try to identify the immediate object and the stranger
            parts = chain_info.split(".")
            if len(parts) >= 2:
                immediate_obj = parts[0]
                stranger_path = ".".join(parts[1:])
                problem = (
                    f"Logic reaches through '{immediate_obj}' to '{stranger_path}'. "
                    f"Chain access exceeds one level of indirection."
                )

        # Build recommendation
        recommendation = (
            "Delegate this call to a method on the immediate object. "
            "Add a method that encapsulates the chain operation."
        )
        if chain_info and "." in chain_info:
            parts = chain_info.split(".")
            if len(parts) >= 2:
                immediate_obj = parts[0]
                action = parts[-1] if parts else "operation"
                recommendation = (
                    f"Add a method to '{immediate_obj}' that performs this operation. "
                    f"Example: {immediate_obj}.{action}() instead of {chain_info}."
                )

        # Build context
        context_info = f"Violation detected at line {target_line}."

        return GovernanceCommentTransformer({
            "rule_code": self.code,
            "rule_name": "Law of Demeter",
            "problem": problem,
            "recommendation": recommendation,
            "context_info": context_info,
            "target_line": target_line,
        })

    def get_fix_instructions(self, violation: Violation) -> str:
        """Provide human/AI instructions for manual fix."""
        return (
            "Extract this chain into a delegated method on the immediate dependency "
            "to preserve encapsulation. Do not use temporary variables as a workaround - "
            "this is a linter cheat that bypasses the architectural issue."
        )
