"""Bridge service to convert Pylint violations to Rule Violation objects."""

from typing import TYPE_CHECKING

import astroid

from excelsior_architect.domain.entities import LinterResult
from excelsior_architect.domain.protocols import AstroidProtocol, ViolationBridgeProtocol
from excelsior_architect.domain.rules import Violation

if TYPE_CHECKING:
    from excelsior_architect.domain.protocols import GuidanceServiceProtocol


class ViolationBridgeService(ViolationBridgeProtocol):
    """
    Service to bridge Pylint violations (LinterResult) to Rule Violation objects.

    This service converts violations detected by Pylint checkers into Violation
    objects that can be processed by Rule classes for governance comment injection.
    """

    def __init__(
        self,
        astroid_gateway: AstroidProtocol,
        guidance_service: "GuidanceServiceProtocol",
    ) -> None:
        self.astroid_gateway = astroid_gateway
        self._guidance = guidance_service

    def convert_linter_results_to_violations(
        self, linter_results: list[LinterResult], file_path: str
    ) -> list[Violation]:
        """
        Convert LinterResult objects to Violation objects with astroid nodes.

        Args:
            linter_results: List of violations from Pylint/Excelsior
            file_path: Path to the file containing violations

        Returns:
            List of Violation objects with astroid nodes attached
        """
        violations: list[Violation] = []

        try:
            # Parse file with astroid to get nodes
            module_node = self.astroid_gateway.parse_file(file_path)
            if not module_node:
                return violations

            for result in linter_results:
                # Extract violations for each location
                for location in result.locations:
                    # Parse location: "path:line" or "path:line:column"
                    location_parts = location.split(":")
                    if len(location_parts) < 2:
                        continue

                    try:
                        line_num = int(location_parts[1])
                    except ValueError:
                        continue

                    # Find the node at this line
                    node = self._find_node_at_line(module_node, line_num)
                    if node:
                        # Determine if this is a comment-only fix
                        is_comment_only = self._is_comment_only_rule(
                            result.code)

                        violation = Violation(
                            code=result.code,
                            message=result.message,
                            location=location,
                            node=node,
                            fixable=True,  # Governance comments are always "fixable"
                            is_comment_only=is_comment_only,
                        )
                        violations.append(violation)
        except Exception:
            # If parsing fails, return empty list
            pass

        return violations

    def _find_node_at_line(
        self, module_node: astroid.nodes.Module, line_num: int
    ) -> astroid.nodes.NodeNG | None:
        """Find the astroid node at a specific line number."""
        try:
            # Search all nodes in the module
            for node in module_node.nodes_of_class(astroid.nodes.NodeNG):
                if hasattr(node, "lineno") and node.lineno == line_num:
                    return node
            # If exact match not found, find closest node
            closest_node = None
            closest_distance = float("inf")
            for node in module_node.nodes_of_class(astroid.nodes.NodeNG):
                if hasattr(node, "lineno") and node.lineno is not None:
                    distance = abs(node.lineno - line_num)
                    if distance < closest_distance:
                        closest_distance = distance
                        closest_node = node
            return closest_node
        except Exception:
            return None

    def _is_comment_only_rule(self, rule_code: str) -> bool:
        """
        Determine if a rule should use comment-only fixes.

        Comment-only rules are those that require manual architectural changes
        but can benefit from governance comment injection.
        Source: rule_registry.yaml (comment_only: true) via injected GuidanceService.
        """
        return rule_code in self._guidance.get_comment_only_codes()
