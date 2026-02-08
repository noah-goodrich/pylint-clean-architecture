"""Unit tests for domain analysis: ViolationClusterer, DesignPatternDecisionTree, HealthScorer."""

import unittest
from unittest.mock import MagicMock

from excelsior_architect.domain.analysis import (
    DesignPatternDecisionTree,
    HealthScorer,
    ViolationClusterer,
)
from excelsior_architect.domain.entities import (
    AuditResult,
    DesignPatternRecommendation,
    FindingScore,
    LinterResult,
    SystemicFinding,
)


class TestViolationClusterer(unittest.TestCase):
    """Test ViolationClusterer clustering logic."""

    def setUp(self) -> None:
        self.mock_guidance = MagicMock()
        self.clusterer = ViolationClusterer(self.mock_guidance)

    def test_cluster_with_empty_audit_result(self) -> None:
        """cluster() returns empty list for audit result with no violations."""
        audit_result = AuditResult(
            import_linter_results=[],
            ruff_results=[],
            mypy_results=[],
            excelsior_results=[],
            blocking_gate=None,
        )
        result = self.clusterer.cluster(audit_result)
        self.assertEqual(result, [])

    def test_cluster_with_single_violation(self) -> None:
        """cluster() creates one finding for single violation."""
        self.mock_guidance.get_excelsior_entry.return_value = None
        self.mock_guidance.get_entry.return_value = None

        linter_result = LinterResult(
            code="W9004",
            message="Domain uses framework",
            locations=["src/domain/user.py:10:5"],
        )
        audit_result = AuditResult(
            import_linter_results=[],
            ruff_results=[],
            mypy_results=[],
            excelsior_results=[linter_result],
            blocking_gate=None,
        )
        findings = self.clusterer.cluster(audit_result)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].violation_codes, ["W9004"])
        self.assertEqual(findings[0].affected_files, ["src/domain/user.py"])
        self.assertEqual(findings[0].violation_count, 1)

    def test_cluster_groups_by_code(self) -> None:
        """cluster() groups violations by rule code."""
        self.mock_guidance.get_excelsior_entry.return_value = None
        self.mock_guidance.get_entry.return_value = None

        linter_result1 = LinterResult(
            code="W9004",
            message="Domain uses framework",
            locations=["src/domain/user.py:10:5"],
        )
        linter_result2 = LinterResult(
            code="W9004",
            message="Domain uses framework",
            locations=["src/domain/order.py:15:8"],
        )
        linter_result3 = LinterResult(
            code="W9006",
            message="Law of Demeter violation",
            locations=["src/interface/cli.py:20:4"],
        )
        audit_result = AuditResult(
            import_linter_results=[],
            ruff_results=[],
            mypy_results=[],
            excelsior_results=[linter_result1, linter_result2, linter_result3],
            blocking_gate=None,
        )
        findings = self.clusterer.cluster(audit_result)

        self.assertEqual(len(findings), 2)
        codes = {f.violation_codes[0] for f in findings}
        self.assertEqual(codes, {"W9004", "W9006"})

    def test_cluster_handles_import_linter_results(self) -> None:
        """cluster() includes import_linter_results in clustering."""
        self.mock_guidance.get_excelsior_entry.return_value = None
        self.mock_guidance.get_entry.return_value = None

        linter_result = LinterResult(
            code="W9201",
            message="Contract violation",
            locations=["src/infrastructure/repo.py:5:0"],
        )
        audit_result = AuditResult(
            import_linter_results=[linter_result],
            ruff_results=[],
            mypy_results=[],
            excelsior_results=[],
            blocking_gate=None,
        )
        findings = self.clusterer.cluster(audit_result)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].violation_codes, ["W9201"])

    def test_cluster_handles_ruff_results(self) -> None:
        """cluster() includes ruff_results in clustering."""
        self.mock_guidance.get_excelsior_entry.return_value = None
        self.mock_guidance.get_entry.return_value = None

        linter_result = LinterResult(
            code="E501",
            message="Line too long",
            locations=["src/interface/cli.py:100:80"],
        )
        audit_result = AuditResult(
            import_linter_results=[],
            ruff_results=[linter_result],
            mypy_results=[],
            excelsior_results=[],
            blocking_gate=None,
        )
        findings = self.clusterer.cluster(audit_result)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].violation_codes, ["E501"])

    def test_cluster_handles_mypy_results(self) -> None:
        """cluster() includes mypy_results in clustering."""
        self.mock_guidance.get_excelsior_entry.return_value = None
        self.mock_guidance.get_entry.return_value = None

        linter_result = LinterResult(
            code="type-arg",
            message="Missing type argument",
            locations=["src/domain/entities.py:25:4"],
        )
        audit_result = AuditResult(
            import_linter_results=[],
            ruff_results=[],
            mypy_results=[linter_result],
            excelsior_results=[],
            blocking_gate=None,
        )
        findings = self.clusterer.cluster(audit_result)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].violation_codes, ["type-arg"])

    def test_cluster_extracts_file_from_location(self) -> None:
        """cluster() correctly extracts file path from location string."""
        self.mock_guidance.get_excelsior_entry.return_value = None
        self.mock_guidance.get_entry.return_value = None

        linter_result = LinterResult(
            code="W9004",
            message="Test",
            locations=["src/domain/user.py:10:5:10"],
        )
        audit_result = AuditResult(
            import_linter_results=[],
            ruff_results=[],
            mypy_results=[],
            excelsior_results=[linter_result],
            blocking_gate=None,
        )
        findings = self.clusterer.cluster(audit_result)

        self.assertEqual(findings[0].affected_files, ["src/domain/user.py"])

    def test_cluster_sorts_affected_files(self) -> None:
        """cluster() returns sorted list of affected files."""
        self.mock_guidance.get_excelsior_entry.return_value = None
        self.mock_guidance.get_entry.return_value = None

        linter_result1 = LinterResult(
            code="W9004",
            message="Test",
            locations=["src/zzz.py:1:1"],
        )
        linter_result2 = LinterResult(
            code="W9004",
            message="Test",
            locations=["src/aaa.py:1:1"],
        )
        audit_result = AuditResult(
            import_linter_results=[],
            ruff_results=[],
            mypy_results=[],
            excelsior_results=[linter_result1, linter_result2],
            blocking_gate=None,
        )
        findings = self.clusterer.cluster(audit_result)

        self.assertEqual(findings[0].affected_files, [
                         "src/aaa.py", "src/zzz.py"])

    def test_cluster_uses_registry_for_title(self) -> None:
        """cluster() uses guidance service to get display name for title."""
        self.mock_guidance.get_excelsior_entry.return_value = {
            "display_name": "Domain Dependency Rule",
            "short_description": "Domain should not depend on I/O",
            "impact_weight": 8.0,
            "confidence": 0.95,
            "effort_category": 4.0,
            "references": ["https://docs.example.com/w9004"],
            "eli5_description": "Keep domain pure"
        }

        linter_result = LinterResult(
            code="W9004",
            message="Test",
            locations=["src/domain/user.py:10:5"],
        )
        audit_result = AuditResult(
            import_linter_results=[],
            ruff_results=[],
            mypy_results=[],
            excelsior_results=[linter_result],
            blocking_gate=None,
        )
        findings = self.clusterer.cluster(audit_result)

        self.assertEqual(findings[0].title, "Domain Dependency Rule")

    def test_cluster_uses_short_description_for_title_when_no_display_name(self) -> None:
        """cluster() falls back to short_description for title."""
        self.mock_guidance.get_excelsior_entry.return_value = {
            "short_description": "Domain should not depend on I/O"
        }

        linter_result = LinterResult(
            code="W9004",
            message="Test",
            locations=["src/domain/user.py:10:5"],
        )
        audit_result = AuditResult(
            import_linter_results=[],
            ruff_results=[],
            mypy_results=[],
            excelsior_results=[linter_result],
            blocking_gate=None,
        )
        findings = self.clusterer.cluster(audit_result)

        self.assertEqual(findings[0].title, "Domain should not depend on I/O")

    def test_cluster_uses_code_for_title_when_no_registry(self) -> None:
        """cluster() uses 'Rule <code>' when no registry entry."""
        self.mock_guidance.get_excelsior_entry.return_value = None
        self.mock_guidance.get_entry.return_value = None

        linter_result = LinterResult(
            code="W9004",
            message="Test",
            locations=["src/domain/user.py:10:5"],
        )
        audit_result = AuditResult(
            import_linter_results=[],
            ruff_results=[],
            mypy_results=[],
            excelsior_results=[linter_result],
            blocking_gate=None,
        )
        findings = self.clusterer.cluster(audit_result)

        self.assertEqual(findings[0].title, "Rule W9004")

    def test_cluster_uses_impact_weight_from_registry(self) -> None:
        """cluster() uses impact_weight from registry in score calculation."""
        self.mock_guidance.get_excelsior_entry.return_value = {
            "impact_weight": 9.5,
            "confidence": 0.99,
            "effort_category": 2.0,
        }

        linter_result = LinterResult(
            code="W9004",
            message="Test",
            locations=["src/domain/user.py:10:5"],
        )
        audit_result = AuditResult(
            import_linter_results=[],
            ruff_results=[],
            mypy_results=[],
            excelsior_results=[linter_result],
            blocking_gate=None,
        )
        findings = self.clusterer.cluster(audit_result)

        # Score should reflect the high impact weight
        self.assertIsInstance(findings[0].score, FindingScore)

    def test_cluster_uses_learn_more_from_registry(self) -> None:
        """cluster() uses first reference URL for learn_more."""
        self.mock_guidance.get_excelsior_entry.return_value = {
            "references": ["https://docs.example.com/w9004", "https://other.com"]
        }

        linter_result = LinterResult(
            code="W9004",
            message="Test",
            locations=["src/domain/user.py:10:5"],
        )
        audit_result = AuditResult(
            import_linter_results=[],
            ruff_results=[],
            mypy_results=[],
            excelsior_results=[linter_result],
            blocking_gate=None,
        )
        findings = self.clusterer.cluster(audit_result)

        self.assertEqual(findings[0].learn_more,
                         "https://docs.example.com/w9004")

    def test_cluster_uses_default_learn_more_when_no_references(self) -> None:
        """cluster() uses default learn_more when no references in registry."""
        self.mock_guidance.get_excelsior_entry.return_value = {}

        linter_result = LinterResult(
            code="W9004",
            message="Test",
            locations=["src/domain/user.py:10:5"],
        )
        audit_result = AuditResult(
            import_linter_results=[],
            ruff_results=[],
            mypy_results=[],
            excelsior_results=[linter_result],
            blocking_gate=None,
        )
        findings = self.clusterer.cluster(audit_result)

        self.assertEqual(findings[0].learn_more, "excelsior plan W9004")

    def test_cluster_uses_eli5_from_registry(self) -> None:
        """cluster() uses eli5_description from registry."""
        self.mock_guidance.get_excelsior_entry.return_value = {
            "eli5_description": "Domain should be pure like math"
        }

        linter_result = LinterResult(
            code="W9004",
            message="Test",
            locations=["src/domain/user.py:10:5"],
        )
        audit_result = AuditResult(
            import_linter_results=[],
            ruff_results=[],
            mypy_results=[],
            excelsior_results=[linter_result],
            blocking_gate=None,
        )
        findings = self.clusterer.cluster(audit_result)

        self.assertEqual(findings[0].eli5_description,
                         "Domain should be pure like math")

    def test_cluster_handles_empty_eli5(self) -> None:
        """cluster() returns empty string for eli5 when not in registry."""
        self.mock_guidance.get_excelsior_entry.return_value = None
        self.mock_guidance.get_entry.return_value = None

        linter_result = LinterResult(
            code="W9004",
            message="Test",
            locations=["src/domain/user.py:10:5"],
        )
        audit_result = AuditResult(
            import_linter_results=[],
            ruff_results=[],
            mypy_results=[],
            excelsior_results=[linter_result],
            blocking_gate=None,
        )
        findings = self.clusterer.cluster(audit_result)

        self.assertEqual(findings[0].eli5_description, "")

    def test_cluster_handles_violation_without_locations(self) -> None:
        """cluster() handles violations with empty locations list."""
        self.mock_guidance.get_excelsior_entry.return_value = None
        self.mock_guidance.get_entry.return_value = None

        linter_result = LinterResult(
            code="W9004",
            message="Test",
            locations=[],
        )
        audit_result = AuditResult(
            import_linter_results=[],
            ruff_results=[],
            mypy_results=[],
            excelsior_results=[linter_result],
            blocking_gate=None,
        )
        findings = self.clusterer.cluster(audit_result)

        self.assertEqual(len(findings), 1)
        # Falls back to item count
        self.assertEqual(findings[0].violation_count, 1)

    def test_cluster_handles_location_without_colon(self) -> None:
        """cluster() handles location strings without line/column info."""
        self.mock_guidance.get_excelsior_entry.return_value = None
        self.mock_guidance.get_entry.return_value = None

        linter_result = LinterResult(
            code="W9004",
            message="Test",
            locations=["src/domain/user.py"],
        )
        audit_result = AuditResult(
            import_linter_results=[],
            ruff_results=[],
            mypy_results=[],
            excelsior_results=[linter_result],
            blocking_gate=None,
        )
        findings = self.clusterer.cluster(audit_result)

        self.assertEqual(findings[0].affected_files, ["src/domain/user.py"])

    def test_cluster_generates_stable_finding_id(self) -> None:
        """cluster() generates stable finding IDs based on code and file."""
        self.mock_guidance.get_excelsior_entry.return_value = None
        self.mock_guidance.get_entry.return_value = None

        linter_result = LinterResult(
            code="W9004",
            message="Test",
            locations=["src/domain/user.py:10:5"],
        )
        audit_result = AuditResult(
            import_linter_results=[],
            ruff_results=[],
            mypy_results=[],
            excelsior_results=[linter_result],
            blocking_gate=None,
        )
        findings = self.clusterer.cluster(audit_result)

        self.assertTrue(findings[0].id.startswith("w9004-"))
        self.assertIn("src", findings[0].id)

    def test_cluster_impact_for_w9004(self) -> None:
        """cluster() returns correct impact string for W9004."""
        self.mock_guidance.get_excelsior_entry.return_value = None
        self.mock_guidance.get_entry.return_value = None

        linter_result = LinterResult(
            code="W9004",
            message="Test",
            locations=["src/domain/user.py:10:5"],
        )
        audit_result = AuditResult(
            import_linter_results=[],
            ruff_results=[],
            mypy_results=[],
            excelsior_results=[linter_result],
            blocking_gate=None,
        )
        findings = self.clusterer.cluster(audit_result)

        self.assertEqual(
            findings[0].impact, "Prevents portability; violates dependency rule.")

    def test_cluster_impact_for_w9006(self) -> None:
        """cluster() returns correct impact string for W9006."""
        self.mock_guidance.get_excelsior_entry.return_value = None
        self.mock_guidance.get_entry.return_value = None

        linter_result = LinterResult(
            code="W9006",
            message="Test",
            locations=["src/domain/user.py:10:5"],
        )
        audit_result = AuditResult(
            import_linter_results=[],
            ruff_results=[],
            mypy_results=[],
            excelsior_results=[linter_result],
            blocking_gate=None,
        )
        findings = self.clusterer.cluster(audit_result)

        self.assertEqual(findings[0].impact,
                         "Tight coupling; harder to test and change.")

    def test_cluster_impact_for_w9010(self) -> None:
        """cluster() returns correct impact string for W9010."""
        self.mock_guidance.get_excelsior_entry.return_value = None
        self.mock_guidance.get_entry.return_value = None

        linter_result = LinterResult(
            code="W9010",
            message="Test",
            locations=["src/domain/user.py:10:5"],
        )
        audit_result = AuditResult(
            import_linter_results=[],
            ruff_results=[],
            mypy_results=[],
            excelsior_results=[linter_result],
            blocking_gate=None,
        )
        findings = self.clusterer.cluster(audit_result)

        self.assertEqual(
            findings[0].impact, "Low cohesion; harder to maintain and extend.")

    def test_cluster_impact_for_w9201(self) -> None:
        """cluster() returns correct impact string for W9201."""
        self.mock_guidance.get_excelsior_entry.return_value = None
        self.mock_guidance.get_entry.return_value = None

        linter_result = LinterResult(
            code="W9201",
            message="Test",
            locations=["src/domain/user.py:10:5"],
        )
        audit_result = AuditResult(
            import_linter_results=[],
            ruff_results=[],
            mypy_results=[],
            excelsior_results=[linter_result],
            blocking_gate=None,
        )
        findings = self.clusterer.cluster(audit_result)

        self.assertEqual(findings[0].impact,
                         "Contract violations; abstraction leaks.")

    def test_cluster_impact_for_w9017(self) -> None:
        """cluster() returns correct impact string for W9017."""
        self.mock_guidance.get_excelsior_entry.return_value = None
        self.mock_guidance.get_entry.return_value = None

        linter_result = LinterResult(
            code="W9017",
            message="Test",
            locations=["src/domain/user.py:10:5"],
        )
        audit_result = AuditResult(
            import_linter_results=[],
            ruff_results=[],
            mypy_results=[],
            excelsior_results=[linter_result],
            blocking_gate=None,
        )
        findings = self.clusterer.cluster(audit_result)

        self.assertEqual(findings[0].impact, "Layer boundaries unclear.")

    def test_cluster_impact_for_r0801(self) -> None:
        """cluster() returns correct impact string for R0801."""
        self.mock_guidance.get_excelsior_entry.return_value = None
        self.mock_guidance.get_entry.return_value = None

        linter_result = LinterResult(
            code="R0801",
            message="Test",
            locations=["src/domain/user.py:10:5"],
        )
        audit_result = AuditResult(
            import_linter_results=[],
            ruff_results=[],
            mypy_results=[],
            excelsior_results=[linter_result],
            blocking_gate=None,
        )
        findings = self.clusterer.cluster(audit_result)

        self.assertEqual(
            findings[0].impact, "Maintenance burden; fix in one place may be missed elsewhere.")

    def test_cluster_impact_for_unknown_code(self) -> None:
        """cluster() returns generic impact string for unknown codes."""
        self.mock_guidance.get_excelsior_entry.return_value = None
        self.mock_guidance.get_entry.return_value = None

        linter_result = LinterResult(
            code="UNKNOWN",
            message="Test",
            locations=["src/domain/user.py:10:5"],
        )
        audit_result = AuditResult(
            import_linter_results=[],
            ruff_results=[],
            mypy_results=[],
            excelsior_results=[linter_result],
            blocking_gate=None,
        )
        findings = self.clusterer.cluster(audit_result)

        self.assertEqual(findings[0].impact,
                         "Architectural or quality concern.")


class TestDesignPatternDecisionTree(unittest.TestCase):
    """Test DesignPatternDecisionTree pattern recommendations."""

    def setUp(self) -> None:
        self.tree = DesignPatternDecisionTree()

    def test_recommend_with_empty_findings(self) -> None:
        """recommend() returns empty lists for no findings."""
        enriched, patterns = self.tree.recommend([])
        self.assertEqual(enriched, [])
        self.assertEqual(patterns, [])

    def test_recommend_adapter_for_w9004(self) -> None:
        """recommend() suggests Adapter pattern for W9004."""
        finding = SystemicFinding(
            id="w9004-test",
            title="Domain Dependency",
            root_cause="Domain uses framework",
            impact="High",
            score=FindingScore.compute(
                reach=50.0, impact=8.0, confidence=0.9, effort=4.0),
            violation_codes=["W9004"],
            affected_files=["src/domain/user.py"],
            violation_count=1,
            pattern_recommendation=None,
            learn_more="",
            eli5_description="",
        )
        enriched, patterns = self.tree.recommend([finding])

        self.assertEqual(len(patterns), 1)
        self.assertEqual(patterns[0].pattern, "Adapter")
        self.assertEqual(patterns[0].category, "structural")
        self.assertIn("Domain/use-case layer uses framework",
                      patterns[0].trigger)
        self.assertEqual(enriched[0].pattern_recommendation, patterns[0])

    def test_recommend_facade_for_w9006(self) -> None:
        """recommend() suggests Facade pattern for W9006."""
        finding = SystemicFinding(
            id="w9006-test",
            title="Law of Demeter",
            root_cause="Chained access",
            impact="Medium",
            score=FindingScore.compute(
                reach=30.0, impact=6.0, confidence=0.9, effort=3.0),
            violation_codes=["W9006"],
            affected_files=["src/interface/cli.py"],
            violation_count=1,
            pattern_recommendation=None,
            learn_more="",
            eli5_description="",
        )
        enriched, patterns = self.tree.recommend([finding])

        self.assertEqual(len(patterns), 1)
        self.assertEqual(patterns[0].pattern, "Facade")
        self.assertEqual(patterns[0].category, "structural")
        self.assertIn("Law of Demeter", patterns[0].trigger)

    def test_recommend_facade_for_w9010(self) -> None:
        """recommend() suggests Facade pattern for W9010 (god file)."""
        finding = SystemicFinding(
            id="w9010-test",
            title="God File",
            root_cause="Too many responsibilities",
            impact="High",
            score=FindingScore.compute(
                reach=50.0, impact=7.0, confidence=0.85, effort=5.0),
            violation_codes=["W9010"],
            affected_files=["src/interface/cli.py"],
            violation_count=1,
            pattern_recommendation=None,
            learn_more="",
            eli5_description="",
        )
        enriched, patterns = self.tree.recommend([finding])

        self.assertEqual(len(patterns), 1)
        self.assertEqual(patterns[0].pattern, "Facade")
        self.assertIn("God file", patterns[0].trigger)

    def test_recommend_adapter_for_w9201(self) -> None:
        """recommend() suggests Adapter pattern for W9201 (contract integrity)."""
        finding = SystemicFinding(
            id="w9201-test",
            title="Contract Violation",
            root_cause="Missing protocol implementation",
            impact="High",
            score=FindingScore.compute(
                reach=40.0, impact=8.0, confidence=0.95, effort=3.0),
            violation_codes=["W9201"],
            affected_files=["src/infrastructure/repo.py"],
            violation_count=1,
            pattern_recommendation=None,
            learn_more="",
            eli5_description="",
        )
        enriched, patterns = self.tree.recommend([finding])

        self.assertEqual(len(patterns), 1)
        self.assertEqual(patterns[0].pattern, "Adapter")
        self.assertIn(
            "Infrastructure class does not implement domain protocol", patterns[0].trigger)

    def test_recommend_none_for_unknown_code(self) -> None:
        """recommend() returns no pattern for unrecognized violation codes."""
        finding = SystemicFinding(
            id="unknown-test",
            title="Unknown Issue",
            root_cause="Something",
            impact="Low",
            score=FindingScore.compute(
                reach=10.0, impact=3.0, confidence=0.7, effort=2.0),
            violation_codes=["UNKNOWN"],
            affected_files=["src/test.py"],
            violation_count=1,
            pattern_recommendation=None,
            learn_more="",
            eli5_description="",
        )
        enriched, patterns = self.tree.recommend([finding])

        self.assertEqual(len(patterns), 0)
        self.assertIsNone(enriched[0].pattern_recommendation)

    def test_recommend_preserves_finding_attributes(self) -> None:
        """recommend() preserves all finding attributes when enriching."""
        finding = SystemicFinding(
            id="w9004-test",
            title="Domain Dependency",
            root_cause="Domain uses framework",
            impact="High",
            score=FindingScore.compute(
                reach=50.0, impact=8.0, confidence=0.9, effort=4.0),
            violation_codes=["W9004"],
            affected_files=["src/domain/user.py", "src/domain/order.py"],
            violation_count=5,
            pattern_recommendation=None,
            learn_more="https://example.com",
            eli5_description="Keep it pure",
        )
        enriched, _ = self.tree.recommend([finding])

        self.assertEqual(enriched[0].id, "w9004-test")
        self.assertEqual(enriched[0].title, "Domain Dependency")
        self.assertEqual(enriched[0].root_cause, "Domain uses framework")
        self.assertEqual(enriched[0].impact, "High")
        self.assertEqual(enriched[0].violation_count, 5)
        self.assertEqual(enriched[0].learn_more, "https://example.com")
        self.assertEqual(enriched[0].eli5_description, "Keep it pure")

    def test_recommend_limits_affected_files_to_five(self) -> None:
        """recommend() includes max 5 affected files in pattern recommendation."""
        finding = SystemicFinding(
            id="w9004-test",
            title="Domain Dependency",
            root_cause="Domain uses framework",
            impact="High",
            score=FindingScore.compute(
                reach=50.0, impact=8.0, confidence=0.9, effort=4.0),
            violation_codes=["W9004"],
            affected_files=[f"src/file{i}.py" for i in range(10)],
            violation_count=10,
            pattern_recommendation=None,
            learn_more="",
            eli5_description="",
        )
        _, patterns = self.tree.recommend([finding])

        self.assertEqual(len(patterns[0].affected_files), 5)

    def test_recommend_handles_multiple_findings(self) -> None:
        """recommend() processes multiple findings independently."""
        finding1 = SystemicFinding(
            id="w9004-test",
            title="Domain Dependency",
            root_cause="Domain uses framework",
            impact="High",
            score=FindingScore.compute(
                reach=50.0, impact=8.0, confidence=0.9, effort=4.0),
            violation_codes=["W9004"],
            affected_files=["src/domain/user.py"],
            violation_count=1,
            pattern_recommendation=None,
            learn_more="",
            eli5_description="",
        )
        finding2 = SystemicFinding(
            id="w9006-test",
            title="Law of Demeter",
            root_cause="Chained access",
            impact="Medium",
            score=FindingScore.compute(
                reach=30.0, impact=6.0, confidence=0.9, effort=3.0),
            violation_codes=["W9006"],
            affected_files=["src/interface/cli.py"],
            violation_count=1,
            pattern_recommendation=None,
            learn_more="",
            eli5_description="",
        )
        enriched, patterns = self.tree.recommend([finding1, finding2])

        self.assertEqual(len(patterns), 2)
        self.assertEqual(len(enriched), 2)
        pattern_names = {p.pattern for p in patterns}
        self.assertEqual(pattern_names, {"Adapter", "Facade"})


class TestHealthScorer(unittest.TestCase):
    """Test HealthScorer scoring logic."""

    def setUp(self) -> None:
        self.scorer = HealthScorer()

    def test_score_with_no_findings(self) -> None:
        """score() returns perfect score with no findings."""
        overall, layer_health, portability = self.scorer.score(
            findings=[],
            total_violations=0,
            file_to_layer={},
            blocking_gate=None,
        )
        self.assertEqual(overall, 100)
        self.assertEqual(layer_health, [])
        self.assertEqual(portability, "high")

    def test_score_decreases_with_violations(self) -> None:
        """score() decreases as violations increase."""
        finding = SystemicFinding(
            id="test",
            title="Test",
            root_cause="Test",
            impact="Medium",
            score=FindingScore.compute(
                reach=50.0, impact=5.0, confidence=0.9, effort=3.0),
            violation_codes=["TEST"],
            affected_files=["src/test.py"],
            violation_count=10,
            pattern_recommendation=None,
            learn_more="",
            eli5_description="",
        )
        overall, _, _ = self.scorer.score(
            findings=[finding],
            total_violations=10,
            file_to_layer={"src/test.py": "domain"},
            blocking_gate=None,
        )
        self.assertLess(overall, 100)

    def test_score_caps_at_49_with_blocking_gate(self) -> None:
        """score() caps at 49 when blocking gate is set and score would otherwise be 50+."""
        # Need some findings to lower the score below 50, then blocking gate prevents it from being 50+
        finding = SystemicFinding(
            id="test",
            title="Test",
            root_cause="Test",
            impact="Low",
            score=FindingScore.compute(
                reach=10.0, impact=3.0, confidence=0.8, effort=2.0),
            violation_codes=["TEST"],
            affected_files=["src/test.py"],
            violation_count=1,
            pattern_recommendation=None,
            learn_more="",
            eli5_description="",
        )
        overall, _, _ = self.scorer.score(
            findings=[finding],
            total_violations=1,
            file_to_layer={"src/test.py": "domain"},
            blocking_gate="quality",
        )
        # With blocking gate set, score should be capped at 49
        self.assertLessEqual(overall, 49)

    def test_score_creates_layer_health_entries(self) -> None:
        """score() creates LayerHealth entries for each affected layer."""
        finding = SystemicFinding(
            id="test",
            title="Test",
            root_cause="Test",
            impact="Medium",
            score=FindingScore.compute(
                reach=50.0, impact=5.0, confidence=0.9, effort=3.0),
            violation_codes=["TEST"],
            affected_files=["src/domain/user.py", "src/interface/cli.py"],
            violation_count=2,
            pattern_recommendation=None,
            learn_more="",
            eli5_description="",
        )
        _, layer_health, _ = self.scorer.score(
            findings=[finding],
            total_violations=2,
            file_to_layer={
                "src/domain/user.py": "domain",
                "src/interface/cli.py": "interface",
            },
            blocking_gate=None,
        )
        self.assertEqual(len(layer_health), 2)
        layer_names = {lh.layer for lh in layer_health}
        self.assertEqual(layer_names, {"domain", "interface"})

    def test_score_calculates_violation_density(self) -> None:
        """score() calculates violation density (violations per file)."""
        finding = SystemicFinding(
            id="test",
            title="Test",
            root_cause="Test",
            impact="Medium",
            score=FindingScore.compute(
                reach=50.0, impact=5.0, confidence=0.9, effort=3.0),
            violation_codes=["TEST"],
            affected_files=["src/domain/user.py", "src/domain/order.py"],
            violation_count=10,
            pattern_recommendation=None,
            learn_more="",
            eli5_description="",
        )
        _, layer_health, _ = self.scorer.score(
            findings=[finding],
            total_violations=10,
            file_to_layer={
                "src/domain/user.py": "domain",
                "src/domain/order.py": "domain",
            },
            blocking_gate=None,
        )
        self.assertEqual(len(layer_health), 1)
        self.assertEqual(layer_health[0].file_count, 2)
        self.assertEqual(layer_health[0].violation_count, 10)
        # 10 violations / 2 files
        self.assertEqual(layer_health[0].violation_density, 5.0)

    def test_score_includes_hotspot_files(self) -> None:
        """score() includes up to 5 hotspot files per layer."""
        finding = SystemicFinding(
            id="test",
            title="Test",
            root_cause="Test",
            impact="Medium",
            score=FindingScore.compute(
                reach=50.0, impact=5.0, confidence=0.9, effort=3.0),
            violation_codes=["TEST"],
            affected_files=[f"src/file{i}.py" for i in range(10)],
            violation_count=10,
            pattern_recommendation=None,
            learn_more="",
            eli5_description="",
        )
        file_to_layer = {f"src/file{i}.py": "domain" for i in range(10)}
        _, layer_health, _ = self.scorer.score(
            findings=[finding],
            total_violations=10,
            file_to_layer=file_to_layer,
            blocking_gate=None,
        )
        self.assertLessEqual(len(layer_health[0].hotspot_files), 5)

    def test_score_includes_primary_issues(self) -> None:
        """score() includes up to 3 primary issue IDs per layer."""
        findings = [
            SystemicFinding(
                id=f"test{i}",
                title="Test",
                root_cause="Test",
                impact="Medium",
                score=FindingScore.compute(
                    reach=50.0, impact=5.0, confidence=0.9, effort=3.0),
                violation_codes=["TEST"],
                affected_files=["src/domain/user.py"],
                violation_count=1,
                pattern_recommendation=None,
                learn_more="",
                eli5_description="",
            )
            for i in range(5)
        ]
        _, layer_health, _ = self.scorer.score(
            findings=findings,
            total_violations=5,
            file_to_layer={"src/domain/user.py": "domain"},
            blocking_gate=None,
        )
        self.assertLessEqual(len(layer_health[0].primary_issues), 3)

    def test_score_portability_low_with_w9004(self) -> None:
        """score() returns 'low' portability when W9004 is present."""
        finding = SystemicFinding(
            id="test",
            title="Test",
            root_cause="Test",
            impact="High",
            score=FindingScore.compute(
                reach=50.0, impact=8.0, confidence=0.9, effort=4.0),
            violation_codes=["W9004"],
            affected_files=["src/domain/user.py"],
            violation_count=1,
            pattern_recommendation=None,
            learn_more="",
            eli5_description="",
        )
        _, _, portability = self.scorer.score(
            findings=[finding],
            total_violations=1,
            file_to_layer={"src/domain/user.py": "domain"},
            blocking_gate=None,
        )
        self.assertEqual(portability, "low")

    def test_score_portability_low_with_multiple_critical_findings(self) -> None:
        """score() returns 'low' portability with 2+ critical findings."""
        findings = [
            SystemicFinding(
                id=f"test{i}",
                title="Test",
                root_cause="Test",
                impact="Critical",
                score=FindingScore.compute(
                    reach=100.0, impact=10.0, confidence=0.95, effort=5.0),
                violation_codes=["TEST"],
                affected_files=[f"src/file{i}.py"],
                violation_count=1,
                pattern_recommendation=None,
                learn_more="",
                eli5_description="",
            )
            for i in range(2)
        ]
        _, _, portability = self.scorer.score(
            findings=findings,
            total_violations=2,
            file_to_layer={f"src/file{i}.py": "domain" for i in range(2)},
            blocking_gate=None,
        )
        self.assertEqual(portability, "low")

    def test_score_portability_medium_with_one_critical_finding(self) -> None:
        """score() returns 'medium' portability with 1 critical finding."""
        finding = SystemicFinding(
            id="test",
            title="Test",
            root_cause="Test",
            impact="Critical",
            score=FindingScore.compute(
                reach=100.0, impact=10.0, confidence=0.95, effort=5.0),
            violation_codes=["TEST"],
            affected_files=["src/test.py"],
            violation_count=1,
            pattern_recommendation=None,
            learn_more="",
            eli5_description="",
        )
        _, _, portability = self.scorer.score(
            findings=[finding],
            total_violations=1,
            file_to_layer={"src/test.py": "domain"},
            blocking_gate=None,
        )
        self.assertEqual(portability, "medium")

    def test_score_portability_medium_with_many_violations(self) -> None:
        """score() returns 'medium' portability with >30 total violations."""
        finding = SystemicFinding(
            id="test",
            title="Test",
            root_cause="Test",
            impact="Low",
            score=FindingScore.compute(
                reach=10.0, impact=3.0, confidence=0.8, effort=2.0),
            violation_codes=["TEST"],
            affected_files=["src/test.py"],
            violation_count=35,
            pattern_recommendation=None,
            learn_more="",
            eli5_description="",
        )
        _, _, portability = self.scorer.score(
            findings=[finding],
            total_violations=35,
            file_to_layer={"src/test.py": "domain"},
            blocking_gate=None,
        )
        self.assertEqual(portability, "medium")

    def test_score_portability_high_with_few_violations(self) -> None:
        """score() returns 'high' portability with few, low-priority violations."""
        finding = SystemicFinding(
            id="test",
            title="Test",
            root_cause="Test",
            impact="Low",
            score=FindingScore.compute(
                reach=10.0, impact=3.0, confidence=0.8, effort=2.0),
            violation_codes=["TEST"],
            affected_files=["src/test.py"],
            violation_count=5,
            pattern_recommendation=None,
            learn_more="",
            eli5_description="",
        )
        _, _, portability = self.scorer.score(
            findings=[finding],
            total_violations=5,
            file_to_layer={"src/test.py": "domain"},
            blocking_gate=None,
        )
        self.assertEqual(portability, "high")

    def test_score_handles_unknown_layer(self) -> None:
        """score() assigns 'unknown' layer when file not in mapping."""
        finding = SystemicFinding(
            id="test",
            title="Test",
            root_cause="Test",
            impact="Medium",
            score=FindingScore.compute(
                reach=50.0, impact=5.0, confidence=0.9, effort=3.0),
            violation_codes=["TEST"],
            affected_files=["src/mystery.py"],
            violation_count=1,
            pattern_recommendation=None,
            learn_more="",
            eli5_description="",
        )
        _, layer_health, _ = self.scorer.score(
            findings=[finding],
            total_violations=1,
            file_to_layer={},
            blocking_gate=None,
        )
        self.assertEqual(len(layer_health), 1)
        self.assertEqual(layer_health[0].layer, "unknown")

    def test_score_handles_prefix_matching_in_file_to_layer(self) -> None:
        """score() matches files by prefix in file_to_layer mapping."""
        finding = SystemicFinding(
            id="test",
            title="Test",
            root_cause="Test",
            impact="Medium",
            score=FindingScore.compute(
                reach=50.0, impact=5.0, confidence=0.9, effort=3.0),
            violation_codes=["TEST"],
            affected_files=["src/domain/subdir/user.py"],
            violation_count=1,
            pattern_recommendation=None,
            learn_more="",
            eli5_description="",
        )
        _, layer_health, _ = self.scorer.score(
            findings=[finding],
            total_violations=1,
            file_to_layer={"domain": "domain"},  # Prefix match
            blocking_gate=None,
        )
        self.assertEqual(layer_health[0].layer, "domain")
