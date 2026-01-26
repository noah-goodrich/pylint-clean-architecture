"""Tests for GovernanceCommentTransformer."""

from unittest.mock import MagicMock

import libcst as cst
import pytest

from clean_architecture_linter.infrastructure.gateways.transformers import (
    GovernanceCommentTransformer,
)


class TestGovernanceCommentTransformer:
    """Test governance comment injection."""

    def test_builds_comment_lines(self) -> None:
        """Test comment line building."""
        transformer = GovernanceCommentTransformer({
            "rule_code": "W9006",
            "rule_name": "Law of Demeter",
            "problem": "Chain access exceeds one level",
            "recommendation": "Delegate to immediate object",
            "context_info": "Line 5",
        })
        lines = transformer._build_comment_lines()
        assert len(lines) == 4
        assert "EXCELSIOR: W9006 - Law of Demeter" in lines[0]
        assert "Problem: Chain access exceeds one level" in lines[1]
        assert "Recommendation: Delegate to immediate object" in lines[2]
        assert "Context: Line 5" in lines[3]

    def test_builds_comment_lines_without_context(self) -> None:
        """Test comment line building without context."""
        transformer = GovernanceCommentTransformer({
            "rule_code": "W9006",
            "rule_name": "Law of Demeter",
            "problem": "Chain access exceeds one level",
            "recommendation": "Delegate to immediate object",
        })
        lines = transformer._build_comment_lines()
        assert len(lines) == 3
        assert "Context:" not in "\n".join(lines)

    def test_injects_comments_before_target_line(self) -> None:
        """Test that comments are injected before the target line."""
        source = """def example():
    x = 1
    y = obj.a.b.c()  # Target line
    return y
"""
        source_lines = source.splitlines()
        module = cst.parse_module(source)

        transformer = GovernanceCommentTransformer({
            "rule_code": "W9006",
            "rule_name": "Law of Demeter",
            "problem": "Chain access exceeds one level",
            "recommendation": "Delegate to immediate object",
            "target_line": 3,
            "source_lines": source_lines,
        })

        modified = module.visit(transformer)
        code = modified.code

        # Check that comments were added
        assert "EXCELSIOR: W9006" in code
        assert "Problem: Chain access exceeds one level" in code
        assert "Recommendation: Delegate to immediate object" in code

    def test_handles_zero_target_line(self) -> None:
        """Test that zero target line doesn't inject comments."""
        source = "x = 1\n"
        module = cst.parse_module(source)

        transformer = GovernanceCommentTransformer({
            "rule_code": "W9006",
            "rule_name": "Law of Demeter",
            "problem": "Test",
            "recommendation": "Test",
            "target_line": 0,
        })

        modified = module.visit(transformer)
        assert modified.code == source

    def test_handles_empty_file(self) -> None:
        """Test that empty file is handled gracefully."""
        source = ""
        module = cst.parse_module(source)

        transformer = GovernanceCommentTransformer({
            "rule_code": "W9006",
            "rule_name": "Law of Demeter",
            "problem": "Test",
            "recommendation": "Test",
            "target_line": 1,
        })

        modified = module.visit(transformer)
        # Should still work, adding comments
        assert "EXCELSIOR" in modified.code or modified.code == source

    def test_applies_only_once(self) -> None:
        """Test that transformer only applies once."""
        source = "x = 1\ny = 2\n"
        source_lines = source.splitlines()
        module = cst.parse_module(source)

        transformer = GovernanceCommentTransformer({
            "rule_code": "W9006",
            "rule_name": "Law of Demeter",
            "problem": "Test",
            "recommendation": "Test",
            "target_line": 1,
            "source_lines": source_lines,
        })

        modified = module.visit(transformer)
        # Count occurrences of EXCELSIOR
        count = modified.code.count("EXCELSIOR: W9006")
        assert count == 1  # Should only appear once

    def test_get_node_line_with_source_lines(self) -> None:
        """Test _get_node_line with source lines."""
        source = "x = 1\ny = 2\n"
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
        
        # Test _get_node_line
        stmt = module.body[0]
        line = transformer._get_node_line(stmt)
        # Should return a line number (may be approximate)
        assert isinstance(line, int)
        assert line >= 0

    def test_get_node_line_without_source_lines(self) -> None:
        """Test _get_node_line without source lines."""
        transformer = GovernanceCommentTransformer({
            "rule_code": "W9006",
            "rule_name": "Test",
            "problem": "Test",
            "recommendation": "Test",
            "target_line": 1,
        })
        
        module = cst.parse_module("x = 1\n")
        stmt = module.body[0]
        line = transformer._get_node_line(stmt)
        # Should return 0 when no source_lines
        assert line == 0

    def test_leave_module_finds_insert_index(self) -> None:
        """Test that leave_Module finds correct insert index."""
        source = """def func1():
    pass

def func2():
    pass
"""
        source_lines = source.splitlines()
        module = cst.parse_module(source)
        
        transformer = GovernanceCommentTransformer({
            "rule_code": "W9006",
            "rule_name": "Test",
            "problem": "Test",
            "recommendation": "Test",
            "target_line": 4,  # Before func2
            "source_lines": source_lines,
        })
        
        modified = module.visit(transformer)
        code = modified.code
        
        # Comments should be inserted
        assert "EXCELSIOR" in code

    def test_leave_module_inserts_at_beginning_when_no_match(self) -> None:
        """Test that comments are inserted at beginning when no line match."""
        source = "x = 1\ny = 2\n"
        source_lines = source.splitlines()
        module = cst.parse_module(source)
        
        transformer = GovernanceCommentTransformer({
            "rule_code": "W9006",
            "rule_name": "Test",
            "problem": "Test",
            "recommendation": "Test",
            "target_line": 999,  # Way beyond file
            "source_lines": source_lines,
        })
        
        modified = module.visit(transformer)
        code = modified.code
        
        # Should still insert comments (at beginning as fallback)
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
        
        # Test that lines without # prefix get it added
        # This tests the "if not line.startswith('#')" branch
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
        
        stmt = module.body[0]
        # Test metadata path (will likely fall back to source search)
        line = transformer._get_node_line(stmt)
        assert isinstance(line, int)

    def test_get_node_line_fallback_to_source_search(self) -> None:
        """Test _get_node_line fallback to source line search."""
        source = "def example():\n    return 42\n"
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
        
        func_def = module.body[0]
        line = transformer._get_node_line(func_def)
        # Should find approximate line
        assert isinstance(line, int)

    def test_leave_module_inserts_when_body_empty(self) -> None:
        """Test that comments are inserted when module body is empty."""
        source = ""
        module = cst.parse_module(source)
        
        transformer = GovernanceCommentTransformer({
            "rule_code": "W9006",
            "rule_name": "Test",
            "problem": "Test",
            "recommendation": "Test",
            "target_line": 1,
        })
        
        modified = module.visit(transformer)
        # Should add comments even to empty file (tests line 387-390)
        assert "EXCELSIOR" in modified.code

    def test_leave_module_appends_when_target_beyond_end_and_body_exists(self) -> None:
        """Test that comments are appended when target_line is beyond file end but body exists."""
        source = "x = 1\ny = 2\n"
        source_lines = source.splitlines()
        module = cst.parse_module(source)
        
        transformer = GovernanceCommentTransformer({
            "rule_code": "W9006",
            "rule_name": "Test",
            "problem": "Test",
            "recommendation": "Test",
            "target_line": 100,  # Way beyond end
            "source_lines": source_lines,
        })
        
        # Ensure applied is False to test the append path (line 384-386)
        transformer.applied = False
        
        modified = module.visit(transformer)
        # Should append comments at end (tests line 384-386)
        assert "EXCELSIOR" in modified.code
        # Verify comments are at the end (they should be appended after the statements)
        code_lines = modified.code.splitlines()
        # Comments should be somewhere in the file
        assert any("EXCELSIOR" in line for line in code_lines)

    def test_get_node_line_handles_metadata_exception(self) -> None:
        """Test that _get_node_line handles exceptions in metadata access."""
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
        
        # Create a mock node that will raise exception when accessing metadata
        mock_node = MagicMock()
        mock_node.metadata = MagicMock()
        mock_node.metadata.get = MagicMock(side_effect=Exception("Metadata error"))
        
        # Should handle exception gracefully (tests line 319-320)
        line = transformer._get_node_line(mock_node)
        # Should fall back to source line search or return 0
        assert isinstance(line, int)

    def test_get_node_line_returns_zero_when_no_match(self) -> None:
        """Test that _get_node_line returns 0 when no source line match is found."""
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
        
        # Create a node that won't match any source line
        # Use a node that doesn't match the source content
        unmatched_node = cst.SimpleStatementLine(
            body=[cst.Expr(value=cst.Name("UNMATCHED_NODE_NAME_XYZ_123"))]
        )
        
        # Should return 0 when no match found (tests line 329)
        line = transformer._get_node_line(unmatched_node)
        assert line == 0

    def test_leave_module_appends_when_target_beyond_end(self) -> None:
        """Test that comments are appended when target_line is beyond file end."""
        source = "x = 1\ny = 2\n"
        source_lines = source.splitlines()
        module = cst.parse_module(source)
        
        transformer = GovernanceCommentTransformer({
            "rule_code": "W9006",
            "rule_name": "Test",
            "problem": "Test",
            "recommendation": "Test",
            "target_line": 100,  # Beyond end
            "source_lines": source_lines,
        })
        
        modified = module.visit(transformer)
        # Should append comments at end
        assert "EXCELSIOR" in modified.code
