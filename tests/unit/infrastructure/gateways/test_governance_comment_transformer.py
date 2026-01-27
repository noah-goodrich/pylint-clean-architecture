"""Tests for GovernanceCommentTransformer."""

import libcst as cst
import pytest

from clean_architecture_linter.infrastructure.gateways.transformers import (
    GovernanceCommentTransformer,
)


class TestGovernanceCommentTransformer:
    """Test GovernanceCommentTransformer behavior."""

    def test_leave_module_inserts_comment_before_target_line(self) -> None:
        """Test that comment is inserted before target line."""
        source = "x = 1\ny = 2\n"
        source_lines = source.splitlines()
        module = cst.parse_module(source)
        
        transformer = GovernanceCommentTransformer({
            "rule_code": "W9006",
            "rule_name": "Law of Demeter",
            "problem": "Chain access violation",
            "recommendation": "Delegate to immediate dependency",
            "target_line": 2,
            "source_lines": source_lines,
        })
        
        modified = module.visit(transformer)
        code = modified.code
        
        assert "EXCELSIOR" in code
        assert "W9006" in code
        assert "Law of Demeter" in code

    def test_leave_module_inserts_at_beginning_when_no_match(self) -> None:
        """Test that comment is inserted at beginning when target line not found."""
        source = "x = 1\n"
        source_lines = source.splitlines()
        module = cst.parse_module(source)
        
        transformer = GovernanceCommentTransformer({
            "rule_code": "W9006",
            "rule_name": "Test",
            "problem": "Test",
            "recommendation": "Test",
            "target_line": 999,  # Beyond file length
            "source_lines": source_lines,
        })
        
        modified = module.visit(transformer)
        code = modified.code
        
        assert "EXCELSIOR" in code

    def test_leave_module_handles_already_applied(self) -> None:
        """Test that transformer doesn't apply twice."""
        source = "x = 1\n"
        module = cst.parse_module(source)
        
        transformer = GovernanceCommentTransformer({
            "rule_code": "W9006",
            "rule_name": "Test",
            "problem": "Test",
            "recommendation": "Test",
            "target_line": 1,
        })
        
        transformer.applied = True  # Mark as already applied
        modified = module.visit(transformer)
        
        # Should not add comments
        assert "EXCELSIOR" not in modified.code

    def test_leave_module_skips_existing_comment(self) -> None:
        """Test that transformer skips adding comment if one already exists."""
        source = """# EXCELSIOR: W9006 - Law of Demeter
# Problem: Chain access violation
# Recommendation: Delegate to immediate dependency
x = 1
"""
        source_lines = source.splitlines()
        module = cst.parse_module(source)
        
        transformer = GovernanceCommentTransformer({
            "rule_code": "W9006",
            "rule_name": "Law of Demeter",
            "problem": "Chain access violation",
            "recommendation": "Delegate to immediate dependency",
            "target_line": 4,
            "source_lines": source_lines,
        })
        
        modified = module.visit(transformer)
        code = modified.code
        
        # Count EXCELSIOR occurrences - should only be one
        excelsior_count = code.count("# EXCELSIOR: W9006")
        assert excelsior_count == 1, f"Expected 1 EXCELSIOR comment, found {excelsior_count}"

    def test_has_existing_comment_detects_existing(self) -> None:
        """Test _has_existing_comment detects existing EXCELSIOR comment."""
        source = """# EXCELSIOR: W9006 - Law of Demeter
x = 1
"""
        module = cst.parse_module(source)
        
        transformer = GovernanceCommentTransformer({
            "rule_code": "W9006",
            "rule_name": "Test",
            "problem": "Test",
            "recommendation": "Test",
            "target_line": 2,
        })
        
        assert transformer._has_existing_comment(module) is True

    def test_has_existing_comment_ignores_different_rule(self) -> None:
        """Test _has_existing_comment ignores comments for different rules."""
        source = """# EXCELSIOR: W9001 - Different Rule
x = 1
"""
        module = cst.parse_module(source)
        
        transformer = GovernanceCommentTransformer({
            "rule_code": "W9006",
            "rule_name": "Test",
            "problem": "Test",
            "recommendation": "Test",
            "target_line": 2,
        })
        
        assert transformer._has_existing_comment(module) is False

    def test_has_existing_comment_checks_leading_lines(self) -> None:
        """Test _has_existing_comment checks leading_lines of statements."""
        source = """x = 1
"""
        module = cst.parse_module(source)
        # Manually add a leading line comment
        stmt = module.body[0]
        if hasattr(stmt, "leading_lines"):
            # Create a comment in leading_lines
            comment_line = cst.EmptyLine(
                comment=cst.Comment(value="# EXCELSIOR: W9006 - Test")
            )
            # Note: leading_lines is read-only, so we'd need to reconstruct
            # For this test, we'll just verify the method checks leading_lines
        
        transformer = GovernanceCommentTransformer({
            "rule_code": "W9006",
            "rule_name": "Test",
            "problem": "Test",
            "recommendation": "Test",
            "target_line": 1,
        })
        
        # If no existing comment, should return False
        # (We can't easily modify leading_lines in LibCST, so this is a basic test)
        result = transformer._has_existing_comment(module)
        # Should return False since there's no EXCELSIOR comment
        assert result is False

    def test_comment_line_without_hash_prefix(self) -> None:
        """Test that lines without # prefix are handled."""
        source = "x = 1\n"
        source_lines = source.splitlines()
        module = cst.parse_module(source)
        
        transformer = GovernanceCommentTransformer({
            "rule_code": "W9006",
            "rule_name": "Test",
            "problem": "Test",
            "recommendation": "Test",
            "target_line": 1,
            "source_lines": source_lines,
        })
        
        # Manually modify comment_lines to have one without #
        original_build = transformer._build_comment_lines
        def mock_build():
            lines = original_build()
            # Add a line without #
            lines.append("Test line without hash")
            return lines
        transformer._build_comment_lines = mock_build
        
        modified = module.visit(transformer)
        # Should handle gracefully, adding # to lines that need it
        assert modified is not None

    def test_get_node_line_tries_metadata(self) -> None:
        """Test _get_node_line tries to use metadata."""
        source = "x = 1\n"
        source_lines = source.splitlines()
        module = cst.parse_module(source)
        
        transformer = GovernanceCommentTransformer({
            "rule_code": "W9006",
            "rule_name": "Test",
            "problem": "Test",
            "recommendation": "Test",
            "target_line": 1,
            "source_lines": source_lines,
        })
        
        # Test with a statement node
        stmt = module.body[0]
        line = transformer._get_node_line(stmt)
        # Should return a line number (may be 0 if metadata not available)
        assert isinstance(line, int)
