"""Unit tests for AnalyzeHealthUseCase."""

import unittest
from unittest.mock import MagicMock

from excelsior_architect.domain.entities import (
    AuditResult,
    FindingScore,
    LinterResult,
    SystemicFinding,
)
from excelsior_architect.use_cases.analyze_health import AnalyzeHealthUseCase


class TestAnalyzeHealthUseCase(unittest.TestCase):
    """Test AnalyzeHealthUseCase orchestration."""

    def setUp(self) -> None:
        self.mock_clusterer = MagicMock()
        self.mock_decision_tree = MagicMock()
        self.mock_scorer = MagicMock()
        self.mock_config_loader = MagicMock()

        self.use_case = AnalyzeHealthUseCase(
            clusterer=self.mock_clusterer,
            decision_tree=self.mock_decision_tree,
            scorer=self.mock_scorer,
            config_loader=self.mock_config_loader,
        )

    def test_execute_calls_clusterer(self) -> None:
        """execute() calls clusterer.cluster with audit result."""
        audit_result = AuditResult(
            import_linter_results=[],
            ruff_results=[],
            mypy_results=[],
            excelsior_results=[],
            blocking_gate=None,
        )
        self.mock_clusterer.cluster.return_value = []
        self.mock_decision_tree.recommend.return_value = ([], [])
        self.mock_scorer.score.return_value = (100, [], "high")

        self.use_case.execute(audit_result)

        self.mock_clusterer.cluster.assert_called_once_with(audit_result)

    def test_execute_calls_decision_tree(self) -> None:
        """execute() calls decision_tree.recommend with findings."""
        audit_result = AuditResult(
            import_linter_results=[],
            ruff_results=[],
            mypy_results=[],
            excelsior_results=[],
            blocking_gate=None,
        )
        mock_findings = [
            SystemicFinding(
                id="test",
                title="Test",
                root_cause="Test",
                impact="Medium",
                score=FindingScore.compute(
                    reach=50.0, impact=5.0, confidence=0.9, effort=3.0),
                violation_codes=["TEST"],
                affected_files=["test.py"],
                violation_count=1,
                pattern_recommendation=None,
                learn_more="",
                eli5_description="",
            )
        ]
        self.mock_clusterer.cluster.return_value = mock_findings
        self.mock_decision_tree.recommend.return_value = (mock_findings, [])
        self.mock_scorer.score.return_value = (100, [], "high")

        self.use_case.execute(audit_result)

        self.mock_decision_tree.recommend.assert_called_once_with(
            mock_findings)

    def test_execute_calls_scorer_with_enriched_findings(self) -> None:
        """execute() calls scorer.score with enriched findings."""
        audit_result = AuditResult(
            import_linter_results=[],
            ruff_results=[],
            mypy_results=[],
            excelsior_results=[],
            blocking_gate=None,
        )
        mock_findings = [
            SystemicFinding(
                id="test",
                title="Test",
                root_cause="Test",
                impact="Medium",
                score=FindingScore.compute(
                    reach=50.0, impact=5.0, confidence=0.9, effort=3.0),
                violation_codes=["TEST"],
                affected_files=["test.py"],
                violation_count=1,
                pattern_recommendation=None,
                learn_more="",
                eli5_description="",
            )
        ]
        enriched_findings = mock_findings  # In real case, might be different
        self.mock_clusterer.cluster.return_value = mock_findings
        self.mock_decision_tree.recommend.return_value = (
            enriched_findings, [])
        self.mock_scorer.score.return_value = (95, [], "high")
        self.mock_config_loader.resolve_layer.return_value = "domain"

        self.use_case.execute(audit_result)

        # Check that scorer was called with enriched findings
        call_args = self.mock_scorer.score.call_args
        self.assertEqual(call_args[0][0], enriched_findings)

    def test_execute_returns_architectural_health_report(self) -> None:
        """execute() returns ArchitecturalHealthReport with all components."""
        audit_result = AuditResult(
            import_linter_results=[],
            ruff_results=[],
            mypy_results=[],
            excelsior_results=[],
            blocking_gate="quality",
        )
        mock_findings = [
            SystemicFinding(
                id="test",
                title="Test",
                root_cause="Test",
                impact="Medium",
                score=FindingScore.compute(
                    reach=50.0, impact=5.0, confidence=0.9, effort=3.0),
                violation_codes=["TEST"],
                affected_files=["test.py"],
                violation_count=1,
                pattern_recommendation=None,
                learn_more="",
                eli5_description="",
            )
        ]
        mock_patterns = [MagicMock()]
        mock_layer_health = [MagicMock()]

        self.mock_clusterer.cluster.return_value = mock_findings
        self.mock_decision_tree.recommend.return_value = (
            mock_findings, mock_patterns)
        self.mock_scorer.score.return_value = (85, mock_layer_health, "medium")
        self.mock_config_loader.resolve_layer.return_value = "domain"

        report = self.use_case.execute(audit_result)

        self.assertEqual(report.overall_score, 85)
        self.assertEqual(report.findings, mock_findings)
        self.assertEqual(report.pattern_recommendations, mock_patterns)
        self.assertEqual(report.layer_health, mock_layer_health)
        self.assertEqual(report.portability_assessment, "medium")
        self.assertEqual(report.blocking_gate, "quality")

    def test_execute_converts_linter_results_to_violation_details(self) -> None:
        """execute() converts all LinterResults to ViolationWithFixInfo."""
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
        self.mock_clusterer.cluster.return_value = []
        self.mock_decision_tree.recommend.return_value = ([], [])
        self.mock_scorer.score.return_value = (100, [], "high")
        self.mock_config_loader.resolve_layer.return_value = "domain"

        report = self.use_case.execute(audit_result)

        self.assertEqual(len(report.violation_details), 1)
        self.assertEqual(report.violation_details[0].code, "W9004")
        self.assertEqual(
            report.violation_details[0].message, "Domain uses framework")
        self.assertEqual(report.violation_details[0].locations, [
                         "src/domain/user.py:10:5"])

    def test_execute_builds_file_to_layer_mapping(self) -> None:
        """execute() builds file_to_layer mapping from audit results."""
        linter_result = LinterResult(
            code="W9004",
            message="Test",
            locations=["src/domain/user.py:10:5", "src/interface/cli.py:20:3"],
        )
        audit_result = AuditResult(
            import_linter_results=[],
            ruff_results=[],
            mypy_results=[],
            excelsior_results=[linter_result],
            blocking_gate=None,
        )
        self.mock_clusterer.cluster.return_value = []
        self.mock_decision_tree.recommend.return_value = ([], [])
        self.mock_scorer.score.return_value = (100, [], "high")
        self.mock_config_loader.resolve_layer.side_effect = lambda _, path, **kwargs: (
            "domain" if "domain" in path else "interface"
        )

        self.use_case.execute(audit_result)

        # Check that config_loader.resolve_layer was called for each file
        self.assertEqual(self.mock_config_loader.resolve_layer.call_count, 2)

    def test_execute_passes_total_violations_to_scorer(self) -> None:
        """execute() passes total violation count to scorer."""
        linter_results = [
            LinterResult(code="W9004", message="Test 1",
                         locations=["test1.py:1:1"]),
            LinterResult(code="W9006", message="Test 2",
                         locations=["test2.py:2:2"]),
            LinterResult(code="E501", message="Test 3",
                         locations=["test3.py:3:3"]),
        ]
        audit_result = AuditResult(
            import_linter_results=[linter_results[0]],
            ruff_results=[linter_results[1]],
            mypy_results=[linter_results[2]],
            excelsior_results=[],
            blocking_gate=None,
        )
        self.mock_clusterer.cluster.return_value = []
        self.mock_decision_tree.recommend.return_value = ([], [])
        self.mock_scorer.score.return_value = (100, [], "high")
        self.mock_config_loader.resolve_layer.return_value = "domain"

        self.use_case.execute(audit_result)

        # scorer.score should receive total_violations=3 as second positional arg
        call_args = self.mock_scorer.score.call_args
        self.assertEqual(call_args[0][1], 3)  # Second positional argument

    def test_execute_passes_blocking_gate_to_scorer(self) -> None:
        """execute() passes blocking_gate to scorer."""
        audit_result = AuditResult(
            import_linter_results=[],
            ruff_results=[],
            mypy_results=[],
            excelsior_results=[],
            blocking_gate="architecture",
        )
        self.mock_clusterer.cluster.return_value = []
        self.mock_decision_tree.recommend.return_value = ([], [])
        self.mock_scorer.score.return_value = (49, [], "low")

        self.use_case.execute(audit_result)

        call_args = self.mock_scorer.score.call_args
        # Fourth positional argument
        self.assertEqual(call_args[0][3], "architecture")

    def test_execute_handles_empty_locations(self) -> None:
        """execute() handles violations with no locations."""
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
        self.mock_clusterer.cluster.return_value = []
        self.mock_decision_tree.recommend.return_value = ([], [])
        self.mock_scorer.score.return_value = (100, [], "high")

        report = self.use_case.execute(audit_result)

        self.assertEqual(report.violation_details[0].location, "unknown")

    def test_execute_joins_multiple_locations(self) -> None:
        """execute() joins multiple locations with comma."""
        linter_result = LinterResult(
            code="W9004",
            message="Test",
            locations=["src/file1.py:10:5", "src/file2.py:20:10"],
        )
        audit_result = AuditResult(
            import_linter_results=[],
            ruff_results=[],
            mypy_results=[],
            excelsior_results=[linter_result],
            blocking_gate=None,
        )
        self.mock_clusterer.cluster.return_value = []
        self.mock_decision_tree.recommend.return_value = ([], [])
        self.mock_scorer.score.return_value = (100, [], "high")
        self.mock_config_loader.resolve_layer.return_value = "domain"

        report = self.use_case.execute(audit_result)

        self.assertEqual(
            report.violation_details[0].location,
            "src/file1.py:10:5, src/file2.py:20:10"
        )

    def test_execute_sets_violation_as_not_fixable(self) -> None:
        """execute() sets all violations as fixable=False by default."""
        linter_result = LinterResult(
            code="W9004",
            message="Test",
            locations=["test.py:1:1"],
        )
        audit_result = AuditResult(
            import_linter_results=[],
            ruff_results=[],
            mypy_results=[],
            excelsior_results=[linter_result],
            blocking_gate=None,
        )
        self.mock_clusterer.cluster.return_value = []
        self.mock_decision_tree.recommend.return_value = ([], [])
        self.mock_scorer.score.return_value = (100, [], "high")
        self.mock_config_loader.resolve_layer.return_value = "domain"

        report = self.use_case.execute(audit_result)

        self.assertFalse(report.violation_details[0].fixable)
        self.assertIsNone(report.violation_details[0].manual_instructions)
        self.assertFalse(report.violation_details[0].comment_only)

    def test_execute_handles_none_layer_from_config_loader(self) -> None:
        """execute() handles None return from config_loader.resolve_layer."""
        linter_result = LinterResult(
            code="W9004",
            message="Test",
            locations=["unknown_file.py:1:1"],
        )
        audit_result = AuditResult(
            import_linter_results=[],
            ruff_results=[],
            mypy_results=[],
            excelsior_results=[linter_result],
            blocking_gate=None,
        )
        self.mock_clusterer.cluster.return_value = []
        self.mock_decision_tree.recommend.return_value = ([], [])
        self.mock_scorer.score.return_value = (100, [], "high")
        self.mock_config_loader.resolve_layer.return_value = None

        report = self.use_case.execute(audit_result)

        # scorer should receive file_to_layer with "unknown" for this file as third positional arg
        call_args = self.mock_scorer.score.call_args
        file_to_layer = call_args[0][2]  # Third positional argument
        self.assertEqual(file_to_layer["unknown_file.py"], "unknown")

    def test_execute_combines_all_linter_results(self) -> None:
        """execute() combines results from all linters."""
        audit_result = AuditResult(
            import_linter_results=[
                LinterResult(code="IL001", message="Import",
                             locations=["file1.py:1:1"])
            ],
            ruff_results=[
                LinterResult(code="E501", message="Line too long",
                             locations=["file2.py:2:2"])
            ],
            mypy_results=[
                LinterResult(code="type-arg", message="Type arg",
                             locations=["file3.py:3:3"])
            ],
            excelsior_results=[
                LinterResult(code="W9004", message="Domain I/O",
                             locations=["file4.py:4:4"])
            ],
            blocking_gate=None,
        )
        self.mock_clusterer.cluster.return_value = []
        self.mock_decision_tree.recommend.return_value = ([], [])
        self.mock_scorer.score.return_value = (100, [], "high")
        self.mock_config_loader.resolve_layer.return_value = "domain"

        report = self.use_case.execute(audit_result)

        self.assertEqual(len(report.violation_details), 4)
        codes = {v.code for v in report.violation_details}
        self.assertEqual(codes, {"IL001", "E501", "type-arg", "W9004"})
