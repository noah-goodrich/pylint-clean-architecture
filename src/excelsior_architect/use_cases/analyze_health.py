"""Use Case: Analyze Health - Produce ArchitecturalHealthReport from AuditResult."""

from typing import TYPE_CHECKING

from excelsior_architect.domain.analysis import (
    DesignPatternDecisionTree,
    HealthScorer,
    ViolationClusterer,
)
from excelsior_architect.domain.entities import (
    ArchitecturalHealthReport,
    AuditResult,
    LinterResult,
    ViolationWithFixInfo,
)

if TYPE_CHECKING:
    from excelsior_architect.domain.config import ConfigurationLoader


class AnalyzeHealthUseCase:
    """
    Orchestrate violation clustering, pattern recommendations, and health scoring.

    Takes AuditResult (all linters' results), produces ArchitecturalHealthReport
    with systemic findings, pattern recommendations, layer health, and scores.
    """

    def __init__(
        self,
        clusterer: ViolationClusterer,
        decision_tree: DesignPatternDecisionTree,
        scorer: HealthScorer,
        config_loader: "ConfigurationLoader",
    ) -> None:
        self.clusterer = clusterer
        self.decision_tree = decision_tree
        self.scorer = scorer
        self.config_loader = config_loader

    def execute(self, audit_result: AuditResult) -> ArchitecturalHealthReport:
        """
        Build full architectural health report from audit result.

        Flow: cluster -> recommend patterns -> score -> report.
        """
        findings = self.clusterer.cluster(audit_result)
        enriched_findings, pattern_recommendations = self.decision_tree.recommend(
            findings
        )

        violation_details = self._violation_details_from_audit(audit_result)
        total_violations = len(violation_details)
        file_to_layer = self._file_to_layer(audit_result)

        overall_score, layer_health, portability = self.scorer.score(
            enriched_findings,
            total_violations,
            file_to_layer,
            audit_result.blocking_gate,
        )

        return ArchitecturalHealthReport(
            overall_score=overall_score,
            findings=enriched_findings,
            pattern_recommendations=pattern_recommendations,
            layer_health=layer_health,
            violation_details=violation_details,
            portability_assessment=portability,
            blocking_gate=audit_result.blocking_gate,
        )

    def _violation_details_from_audit(
        self, audit_result: AuditResult
    ) -> list[ViolationWithFixInfo]:
        """Convert all LinterResults to ViolationWithFixInfo (minimal enrichment)."""
        out: list[ViolationWithFixInfo] = []
        for res in (
            audit_result.import_linter_results
            + audit_result.ruff_results
            + audit_result.mypy_results
            + audit_result.excelsior_results
        ):
            location_str = ", ".join(
                res.locations) if res.locations else "unknown"
            out.append(
                ViolationWithFixInfo(
                    code=res.code,
                    message=res.message,
                    location=location_str,
                    locations=res.locations,
                    fixable=False,
                    manual_instructions=None,
                    comment_only=False,
                )
            )
        return out

    def _file_to_layer(self, audit_result: AuditResult) -> dict[str, str]:
        """Build file path -> layer name map from all locations in audit result."""
        files: set[str] = set()
        for res in (
            audit_result.import_linter_results
            + audit_result.ruff_results
            + audit_result.mypy_results
            + audit_result.excelsior_results
        ):
            for loc in res.locations:
                file_part = loc.split(":")[0] if ":" in loc else loc
                if file_part:
                    files.add(file_part)
        file_to_layer: dict[str, str] = {}
        for path in files:
            layer = self.config_loader.resolve_layer("", path, node=None)
            file_to_layer[path] = layer if layer else "unknown"
        return file_to_layer
