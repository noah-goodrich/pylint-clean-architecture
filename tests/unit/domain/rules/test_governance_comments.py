"""Tests for governance comment rules."""

import astroid

from excelsior_architect.domain.entities import TransformationType
from excelsior_architect.domain.rules import Violation
from excelsior_architect.domain.rules.governance_comments import (
    GenericGovernanceCommentRule,
    LawOfDemeterRule,
)


class TestLawOfDemeterRule:
    """Test LawOfDemeterRule."""

    def test_rule_attributes(self) -> None:
        """Test rule has correct attributes."""
        rule = LawOfDemeterRule()
        assert rule.code == "W9006"
        assert "Law of Demeter" in rule.description

    def test_check_returns_empty_list(self) -> None:
        """Test that check returns empty (violations come from Pylint)."""
        rule = LawOfDemeterRule()
        module_node = astroid.parse("x = 1\n")
        violations = rule.check(module_node)
        assert violations == []

    def test_fix_returns_transformer_for_w9006(self) -> None:
        """Test that fix returns transformer for W9006 violations."""
        rule = LawOfDemeterRule()
        node = astroid.parse("x = obj.a.b.c()\n").body[0].value

        violation = Violation(
            code="W9006",
            message="Law of Demeter: Chain access (obj.a.b.c) exceeds one level",
            location="test.py:1",
            node=node,
            fixable=True,
            is_comment_only=True,
        )

        plan = rule.fix(violation)
        assert plan is not None
        assert plan.transformation_type == TransformationType.ADD_GOVERNANCE_COMMENT
        assert plan.params.get("target_line") is not None

    def test_fix_returns_none_for_wrong_code(self) -> None:
        """Test that fix returns None for non-W9006 violations."""
        rule = LawOfDemeterRule()
        node = astroid.parse("x = 1\n").body[0]

        violation = Violation(
            code="W9001",  # Wrong code
            message="Test",
            location="test.py:1",
            node=node,
            fixable=True,
        )

        transformer = rule.fix(violation)
        assert transformer is None

    def test_fix_extracts_chain_info_from_message(self) -> None:
        """Test that fix extracts chain information from message."""
        rule = LawOfDemeterRule()
        node = astroid.parse("x = obj.a.b.c()\n").body[0].value

        violation = Violation(
            code="W9006",
            message="Law of Demeter: Chain access (repo.session.query) exceeds one level",
            location="test.py:5",
            node=node,
            fixable=True,
            is_comment_only=True,
        )

        plan = rule.fix(violation)
        assert plan is not None
        assert plan.params.get("rule_code") == "W9006"
        assert plan.params.get("target_line") == 5

    def test_fix_builds_problem_description(self) -> None:
        """Test that fix builds appropriate problem description."""
        rule = LawOfDemeterRule()
        node = astroid.parse("x = obj.a.b.c()\n").body[0].value

        violation = Violation(
            code="W9006",
            message="Law of Demeter: Chain access (repo.session.query) exceeds one level",
            location="test.py:10",
            node=node,
            fixable=True,
            is_comment_only=True,
        )

        plan = rule.fix(violation)
        assert plan is not None
        problem = plan.params.get("problem", "")
        assert "repo" in problem or "session" in problem

    def test_fix_builds_recommendation(self) -> None:
        """Test that fix builds actionable recommendation."""
        rule = LawOfDemeterRule()
        node = astroid.parse("x = obj.a.b.c()\n").body[0].value

        violation = Violation(
            code="W9006",
            message="Law of Demeter: Chain access (repo.session.query) exceeds one level",
            location="test.py:10",
            node=node,
            fixable=True,
            is_comment_only=True,
        )

        plan = rule.fix(violation)
        assert plan is not None
        rec = plan.params.get("recommendation", "").lower()
        assert "delegate" in rec or "method" in rec

    def test_get_fix_instructions(self) -> None:
        """Test that get_fix_instructions returns helpful guidance."""
        rule = LawOfDemeterRule()
        node = astroid.parse("x = 1\n").body[0]

        violation = Violation(
            code="W9006",
            message="Test",
            location="test.py:1",
            node=node,
            fixable=True,
        )

        instructions = rule.get_fix_instructions(violation)
        assert "delegate" in instructions.lower()
        assert "encapsulation" in instructions.lower()

    def test_fix_handles_missing_chain_info(self) -> None:
        """Test that fix handles messages without chain info."""
        rule = LawOfDemeterRule()
        node = astroid.parse("x = 1\n").body[0]

        violation = Violation(
            code="W9006",
            message="Law of Demeter violation",  # No chain info
            location="test.py:1",
            node=node,
            fixable=True,
            is_comment_only=True,
        )

        transformer = rule.fix(violation)
        assert transformer is not None
        # Should still create transformer with default problem/recommendation

    def test_fix_extracts_line_number_from_location(self) -> None:
        """Test that fix extracts line number from location."""
        rule = LawOfDemeterRule()
        node = astroid.parse("x = 1\n").body[0]

        violation = Violation(
            code="W9006",
            message="Test",
            location="test.py:42",
            node=node,
            fixable=True,
            is_comment_only=True,
        )

        plan = rule.fix(violation)
        assert plan is not None
        assert plan.params.get("target_line") == 42

    def test_fix_handles_location_without_line(self) -> None:
        """Test that fix handles location without line number."""
        rule = LawOfDemeterRule()
        node = astroid.parse("x = 1\n").body[0]

        violation = Violation(
            code="W9006",
            message="Test",
            location="test.py",  # No line number
            node=node,
            fixable=True,
            is_comment_only=True,
        )

        transformer = rule.fix(violation)
        # Should handle gracefully, target_line might be 0
        assert transformer is not None


class TestGenericGovernanceCommentRule:
    """Test GenericGovernanceCommentRule for non-LoD comment-only rules."""

    def test_fix_returns_transformer_for_matching_code(self) -> None:
        """GenericGovernanceCommentRule.fix returns transformer for matching violation."""
        rule = GenericGovernanceCommentRule("W9201", "Contract Integrity")
        node = astroid.parse("class Foo: pass\n").body[0]

        violation = Violation(
            code="W9201",
            message="Contract Integrity Violation: Class X must inherit from Protocol.",
            location="test.py:10",
            node=node,
            fixable=True,
            is_comment_only=True,
        )

        plan = rule.fix(violation)
        assert plan is not None
        assert plan.params.get("rule_code") == "W9201"
        assert plan.params.get("rule_name") == "Contract Integrity"
        assert plan.params.get("target_line") == 10

    def test_fix_returns_none_for_wrong_code(self) -> None:
        """GenericGovernanceCommentRule.fix returns None for non-matching violation."""
        rule = GenericGovernanceCommentRule("W9201", "Contract Integrity")
        node = astroid.parse("x = 1\n").body[0]

        violation = Violation(
            code="W9006",
            message="Other",
            location="test.py:1",
            node=node,
            fixable=True,
            is_comment_only=True,
        )

        assert rule.fix(violation) is None

    def test_fix_truncates_long_problem_message(self) -> None:
        """GenericGovernanceCommentRule.fix truncates problem message over 120 chars."""
        rule = GenericGovernanceCommentRule("W9016", "Banned Any")
        node = astroid.parse("x = 1\n").body[0]

        long_msg = "A" * 130
        violation = Violation(
            code="W9016",
            message=long_msg,
            location="test.py:1",
            node=node,
            fixable=True,
            is_comment_only=True,
        )

        plan = rule.fix(violation)
        assert plan is not None
        assert len(plan.params.get("problem", "")) <= 120
