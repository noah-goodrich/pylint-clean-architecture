"""Domain analysis: violation clustering, design pattern recommendations, health scoring.

Pure domain logic, no I/O. All classes operate on in-memory data structures.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from excelsior_architect.domain.entities import (
    AuditResult,
    DesignPatternRecommendation,
    FindingScore,
    LinterResult,
    LayerHealth,
    SystemicFinding,
)

if TYPE_CHECKING:
    from excelsior_architect.domain.protocols import GuidanceServiceProtocol
    from excelsior_architect.domain.registry_types import RuleRegistryEntry


class ViolationClusterer:
    """
    Clusters violations from an AuditResult into root-cause SystemicFindings.

    Pure domain logic: groups by rule code, sub-clusters by file, cross-correlates
    to identify architectural hotspots. Title and root cause from registry when available.
    """

    def __init__(self, guidance: "GuidanceServiceProtocol") -> None:
        self._guidance = guidance

    def cluster(self, audit_result: AuditResult) -> list[SystemicFinding]:
        """
        Produce systemic findings from all linter results.

        Combines import_linter, ruff, mypy, excelsior results; groups by rule code;
        sub-clusters by affected file; produces one SystemicFinding per significant
        cluster.
        """
        # Flatten all results with (category, result)
        flat: list[tuple[str, LinterResult]] = []
        if audit_result.import_linter_results:
            for r in audit_result.import_linter_results:
                flat.append(("contracts", r))
        for r in audit_result.ruff_results:
            flat.append(("code_quality", r))
        for r in audit_result.mypy_results:
            flat.append(("type_integrity", r))
        for r in audit_result.excelsior_results:
            flat.append(("architectural", r))

        # Group by rule code
        by_code: dict[str, list[tuple[str, LinterResult]]] = {}
        for category, res in flat:
            by_code.setdefault(res.code, []).append((category, res))

        total_files = self._total_files_from_flat(flat)
        findings: list[SystemicFinding] = []
        for code, items in by_code.items():
            # Affected files: unique file paths from locations
            files_set: set[str] = set()
            for _cat, res in items:
                for loc in res.locations:
                    # Location format: "path:line" or "path:line:col"
                    file_part = loc.split(":")[0] if ":" in loc else loc
                    if file_part:
                        files_set.add(file_part)
            affected_files = sorted(files_set)
            violation_count = sum(len(res.locations) for _cat, res in items)
            if violation_count == 0:
                violation_count = len(items)

            finding_id = self._finding_id(code, affected_files)
            title = self._title_for_code(code)
            root_cause = self._root_cause_for_code(code, len(affected_files))
            impact = self._impact_for_code(code)
            score = self._score_for_code(
                code, len(affected_files), total_files)
            learn_more = self._learn_more_for_code(code)
            eli5 = self._eli5_for_code(code)

            findings.append(
                SystemicFinding(
                    id=finding_id,
                    title=title,
                    root_cause=root_cause,
                    impact=impact,
                    score=score,
                    violation_codes=[code],
                    affected_files=affected_files,
                    violation_count=violation_count,
                    pattern_recommendation=None,
                    learn_more=learn_more,
                    eli5_description=eli5,
                )
            )

        return findings

    def _total_files_from_flat(
        self, flat: list[tuple[str, LinterResult]]
    ) -> int:
        """Count unique file paths across all results."""
        files: set[str] = set()
        for _cat, res in flat:
            for loc in res.locations:
                file_part = loc.split(":")[0] if ":" in loc else loc
                if file_part:
                    files.add(file_part)
        return len(files) if files else 1

    def _score_for_code(
        self, code: str, affected_file_count: int, total_files: int
    ) -> FindingScore:
        """Build FindingScore from registry (impact, confidence, effort) and reach."""
        reach = (affected_file_count / total_files *
                 100.0) if total_files else 0.0
        entry = self._entry_for_code(code)
        impact = 5.0
        confidence = 0.9
        effort = 3.0
        if entry:
            if "impact_weight" in entry and entry["impact_weight"] is not None:
                impact = float(entry["impact_weight"])
            if "confidence" in entry and entry["confidence"] is not None:
                confidence = float(entry["confidence"])
            if "effort_category" in entry and entry["effort_category"] is not None:
                effort = float(entry["effort_category"])
        return FindingScore.compute(reach=reach, impact=impact, confidence=confidence, effort=effort)

    def _learn_more_for_code(self, code: str) -> str:
        """First reference URL from registry, or 'excelsior plan <code>'."""
        entry = self._entry_for_code(code)
        if entry and entry.get("references") and isinstance(entry["references"], list):
            refs = entry["references"]
            if refs and isinstance(refs[0], str):
                return str(refs[0])
        return f"excelsior plan {code}"

    def _eli5_for_code(self, code: str) -> str:
        """One-sentence explanation for ELI5 mode (from registry)."""
        entry = self._entry_for_code(code)
        if entry and entry.get("eli5_description"):
            return str(entry["eli5_description"])
        return ""

    def _finding_id(self, code: str, files: list[str]) -> str:
        """Generate a stable finding id from rule code and primary file."""
        primary = files[0] if files else "unknown"
        safe = primary.replace("/", "_").replace(".", "_")[:30]
        return f"{code.lower()}-{safe}"

    def _entry_for_code(self, code: str) -> "RuleRegistryEntry | None":
        """Resolve registry entry for a rule code (excelsior, ruff, mypy)."""
        entry = self._guidance.get_excelsior_entry(code)
        if entry:
            return entry
        entry = self._guidance.get_entry("ruff", code)
        if entry:
            return entry
        entry = self._guidance.get_entry("mypy", code)
        if entry:
            return entry
        return self._guidance.get_entry("excelsior", code)

    def _title_for_code(self, code: str) -> str:
        """Human-readable title for a rule code (from registry when available)."""
        entry = self._entry_for_code(code)
        if entry:
            display = entry.get("display_name") or entry.get(
                "short_description")
            if display:
                return str(display)
        return f"Rule {code}"

    def _root_cause_for_code(self, code: str, file_count: int) -> str:
        """One-line root cause description (from registry short_description when available)."""
        entry = self._entry_for_code(code)
        if entry and entry.get("short_description"):
            short = str(entry["short_description"])
            return f"{short} in {file_count} file(s)"
        return f"Violations of {code} in {file_count} file(s)"

    def _impact_for_code(self, code: str) -> str:
        """Short impact statement."""
        if code == "W9004":
            return "Prevents portability; violates dependency rule."
        if code == "W9006":
            return "Tight coupling; harder to test and change."
        if code == "W9010":
            return "Low cohesion; harder to maintain and extend."
        if code == "W9201":
            return "Contract violations; abstraction leaks."
        if code == "W9017":
            return "Layer boundaries unclear."
        if code == "R0801":
            return "Maintenance burden; fix in one place may be missed elsewhere."
        return "Architectural or quality concern."


class DesignPatternDecisionTree:
    """
    Maps code smells (rule codes / finding types) to GoF design pattern recommendations.

    Codifies the decision tree from Alina Kovtun's article: choose pattern based on
    pain point (creational, structural, behavioral). Pure domain logic, no I/O.
    """

    def recommend(
        self, findings: list[SystemicFinding]
    ) -> tuple[list[SystemicFinding], list[DesignPatternRecommendation]]:
        """
        Enrich findings with pattern recommendations; return standalone recommendations too.

        Returns (findings_with_patterns, pattern_recommendations).
        """
        pattern_recs: list[DesignPatternRecommendation] = []
        enriched: list[SystemicFinding] = []

        for finding in findings:
            rec = self._recommendation_for_finding(finding)
            if rec:
                pattern_recs.append(rec)
                enriched.append(
                    SystemicFinding(
                        id=finding.id,
                        title=finding.title,
                        root_cause=finding.root_cause,
                        impact=finding.impact,
                        score=finding.score,
                        violation_codes=finding.violation_codes,
                        affected_files=finding.affected_files,
                        violation_count=finding.violation_count,
                        pattern_recommendation=rec,
                        learn_more=finding.learn_more,
                        eli5_description=finding.eli5_description,
                    )
                )
            else:
                enriched.append(finding)

        return (enriched, pattern_recs)

    def _recommendation_for_finding(
        self, finding: SystemicFinding
    ) -> DesignPatternRecommendation | None:
        """Return a design pattern recommendation for this finding, or None."""
        codes = set(finding.violation_codes)
        if "W9004" in codes:
            return DesignPatternRecommendation(
                pattern="Adapter",
                category="structural",
                trigger="Domain/use-case layer uses framework or I/O directly",
                rationale="Protect domain from framework-specific types and I/O.",
                example_fix="Create a domain protocol (e.g. ASTAnalyzerProtocol) and an infrastructure adapter (e.g. AstroidAdapter) implementing it.",
                affected_files=finding.affected_files[:5],
                related_violations=["W9004"],
            )
        if "W9006" in codes:
            return DesignPatternRecommendation(
                pattern="Facade",
                category="structural",
                trigger="Chained access (Law of Demeter violation)",
                rationale="Encapsulate traversal behind a single interface.",
                example_fix="Introduce a Facade or Mediator that hides the chain; callers use the facade instead of reaching through objects.",
                affected_files=finding.affected_files[:5],
                related_violations=["W9006"],
            )
        if "W9010" in codes:
            return DesignPatternRecommendation(
                pattern="Facade",
                category="structural",
                trigger="God file / too many responsibilities",
                rationale="Single class coordinates too many concerns.",
                example_fix="Split into focused services; introduce a Facade (orchestrator) that delegates to them.",
                affected_files=finding.affected_files[:5],
                related_violations=["W9010"],
            )
        if "W9201" in codes:
            return DesignPatternRecommendation(
                pattern="Adapter",
                category="structural",
                trigger="Infrastructure class does not implement domain protocol",
                rationale="Formalize the translation layer as an Adapter implementing a domain protocol.",
                example_fix="Define a protocol in domain; make the infrastructure class implement it (adapter).",
                affected_files=finding.affected_files[:5],
                related_violations=["W9201"],
            )
        return None


class HealthScorer:
    """
    Computes overall health score, per-layer health, and portability assessment.

    Pure domain logic: no I/O. Requires file-to-layer mapping (from config).
    """

    def score(
        self,
        findings: list[SystemicFinding],
        total_violations: int,
        file_to_layer: dict[str, str],
        blocking_gate: str | None,
    ) -> tuple[int, list[LayerHealth], str]:
        """
        Return (overall_score 0-100, layer_health list, portability_assessment).

        file_to_layer: map from file path (or pattern) to layer name, e.g. {"domain/": "domain"}.
        """
        # Weight by priority score
        weighted = sum(
            f.score.priority * f.violation_count for f in findings
        )
        if total_violations == 0:
            overall = 100
        else:
            # Rough scale: 0 violations = 100; many violations = low score
            overall = max(0, 100 - min(weighted, 100))
            if blocking_gate:
                overall = min(overall, 49)

        # Per-layer: aggregate by layer from affected_files in findings
        layer_counts: dict[str, list[str]] = {}
        for finding in findings:
            for path in finding.affected_files:
                layer = self._layer_for_file(path, file_to_layer)
                layer_counts.setdefault(layer, []).append(path)
        layer_health_list: list[LayerHealth] = []
        for layer, paths in sorted(layer_counts.items()):
            files_set = set(paths)
            file_count = len(files_set)
            violation_count = sum(
                f.violation_count
                for f in findings
                if any(p in f.affected_files for p in files_set)
            )
            density = violation_count / file_count if file_count else 0.0
            hotspot_files = sorted(files_set)[:5]
            primary_issues = [f.id for f in findings if any(
                p in f.affected_files for p in files_set)][:3]
            layer_health_list.append(
                LayerHealth(
                    layer=layer,
                    file_count=file_count,
                    violation_count=violation_count,
                    violation_density=density,
                    hotspot_files=hotspot_files,
                    primary_issues=primary_issues,
                )
            )

        # Portability: high-priority findings or domain I/O -> low
        critical_count = sum(1 for f in findings if f.score.priority >= 50)
        if critical_count >= 2 or any("W9004" in f.violation_codes for f in findings):
            portability = "low"
        elif critical_count >= 1 or total_violations > 30:
            portability = "medium"
        else:
            portability = "high"

        return (overall, layer_health_list, portability)

    def _layer_for_file(self, path: str, file_to_layer: dict[str, str]) -> str:
        """Resolve layer for a file path using prefix/key matching."""
        for prefix, layer in file_to_layer.items():
            if prefix in path or path.startswith(prefix):
                return layer
        return "unknown"
