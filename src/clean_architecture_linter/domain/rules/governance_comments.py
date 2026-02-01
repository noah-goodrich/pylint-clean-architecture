"""Governance Comment Rules - Inject contextual guidance for manual-fix violations."""

from typing import Optional

import astroid  # type: ignore[import-untyped]

from clean_architecture_linter.domain.entities import TransformationPlan
from clean_architecture_linter.domain.protocols import LinterAdapterProtocol
from clean_architecture_linter.domain.rules import Violation


class LawOfDemeterRule:
    """
    Rule for W9006: Law of Demeter violations.

    Injects governance comments above violations to provide contextual
    guidance for both humans and AI (Cursor) to understand and fix the issue.

    This is a COMMENT-ONLY fix - it does NOT modify code structure.
    """

    code: str = "W9006"
    description: str = (
        "Law of Demeter: Chain access exceeds one level. "
        "Governance comment will be injected to guide fix."
    )
    fix_type: str = "comment"

    def __init__(self) -> None:
        pass

    def check(self, node: astroid.nodes.NodeNG) -> list[Violation]:
        """
        Check for Law of Demeter violations.

        Note: Violations are detected by Pylint's CouplingChecker. This check()
        is a no-op in the fix pipeline; violations are supplied by Pylint.
        fix() is invoked with those Violation instances.
        """
        return []

    def fix(self, violation: Violation) -> Optional[TransformationPlan]:
        """
        Return a transformation plan for governance comment injection.

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

        return TransformationPlan.governance_comment(
            rule_code=self.code,
            rule_name="Law of Demeter",
            problem=problem,
            recommendation=recommendation,
            context_info=context_info,
            target_line=target_line,
        )

    def get_fix_instructions(self, violation: Violation) -> str:
        """Provide human/AI instructions for manual fix."""
        return (
            "Extract this chain into a delegated method on the immediate dependency "
            "to preserve encapsulation. Do not use temporary variables as a workaround - "
            "this is a linter cheat that bypasses the architectural issue."
        )


class GenericGovernanceCommentRule:
    """
    Generic governance comment rule for all comment-only violations.

    Uses adapter's manual fix instructions to generate standardized
    governance comments for any rule that requires manual architectural fixes.
    """

    def __init__(
        self,
        rule_code: str,
        rule_name: str,
        adapter: Optional[LinterAdapterProtocol] = None,
    ) -> None:
        """
        Initialize generic governance comment rule.

        Args:
            rule_code: The rule code (e.g., "W9201", "W9001", "W9016")
            rule_name: Human-readable rule name (e.g., "Contract Integrity")
            adapter: Optional adapter instance for fetching instructions (via protocol)
        """
        self.code = rule_code
        self.rule_name = rule_name
        self._adapter = adapter

    def check(self, node: astroid.nodes.NodeNG) -> list[Violation]:
        """
        Check for violations.

        Note: Violations are detected by Pylint checkers. This check()
        is a no-op in the fix pipeline; violations are supplied by Pylint.
        """
        return []

    def fix(self, violation: Violation) -> Optional[TransformationPlan]:
        """
        Return a transformation plan for governance comment injection.

        Uses adapter's manual fix instructions to build the comment.
        """
        if violation.code != self.code:
            return None

        # Extract line number from violation location
        location_parts = violation.location.split(":")
        target_line = int(location_parts[1]) if len(location_parts) > 1 else 0

        # Get manual fix instructions from adapter if available
        manual_instructions = "Review and fix the violation manually."
        if self._adapter:
            manual_instructions = self._adapter.get_manual_fix_instructions(self.code)

        # Build problem description from violation message
        problem = violation.message
        # Truncate if too long (keep first sentence or first 120 chars)
        if len(problem) > 120:
            if "." in problem:
                problem = problem.split(".")[0] + "."
            else:
                problem = problem[:117] + "..."

        # Use manual instructions as recommendation
        recommendation = manual_instructions

        # Build context
        context_info = f"Violation detected at line {target_line}."

        return TransformationPlan.governance_comment(
            rule_code=self.code,
            rule_name=self.rule_name,
            problem=problem,
            recommendation=recommendation,
            context_info=context_info,
            target_line=target_line,
        )


# Rule name mapping for common architectural violations
RULE_NAME_MAP = {
    "W9001": "Illegal Dependency",
    "clean-arch-dependency": "Illegal Dependency",
    "W9003": "Protected Member Access",
    "clean-arch-visibility": "Protected Member Access",
    "W9004": "Forbidden I/O",
    "clean-arch-resources": "Forbidden I/O",
    "W9005": "Delegation Anti-Pattern",
    "clean-arch-delegation": "Delegation Anti-Pattern",
    "W9007": "Naked Return",
    "W9009": "Missing Abstraction",
    "W9010": "God File",
    "clean-arch-god-file": "God File",
    "W9011": "Deep Structure",
    "clean-arch-layer": "Deep Structure",
    "W9012": "Defensive None Check",
    "W9013": "Illegal I/O Operation",
    "W9201": "Contract Integrity",
    "contract-integrity-violation": "Contract Integrity",
    "W9301": "DI Violation",
    "clean-arch-di": "DI Violation",
    "W9016": "Banned Any",
    "banned-any-usage": "Banned Any",
    "W9501": "Anti-Bypass",
    "clean-arch-bypass": "Anti-Bypass",
}


def create_governance_rule(
    rule_code: str,
    adapter: Optional[LinterAdapterProtocol] = None,
) -> Optional[GenericGovernanceCommentRule]:
    """
    Factory function to create appropriate governance comment rule.

    Returns:
        LawOfDemeterRule for W9006; GenericGovernanceCommentRule for others;
        None if not comment-only.
    """
    if rule_code == "W9006" or rule_code == "clean-arch-demeter":
        return LawOfDemeterRule()

    rule_name = RULE_NAME_MAP.get(
        rule_code, rule_code.replace("-", " ").title())
    return GenericGovernanceCommentRule(rule_code, rule_name, adapter)
