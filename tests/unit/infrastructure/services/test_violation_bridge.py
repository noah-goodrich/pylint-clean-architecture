"""Tests for ViolationBridgeService."""

from unittest.mock import MagicMock

import astroid

from clean_architecture_linter.domain.entities import LinterResult
from clean_architecture_linter.infrastructure.services.violation_bridge import (
    ViolationBridgeService,
)


class TestViolationBridgeService:
    """Test violation bridge service."""

    def test_convert_linter_results_to_violations(self, tmp_path) -> None:
        """Test converting LinterResult to Violation objects."""
        test_file = tmp_path / "test.py"
        test_file.write_text("""def example():
    x = obj.a.b.c()
    return x
""")

        # Mock astroid gateway - use side_effect to return module for any file path
        astroid_gateway = MagicMock()
        module_node = astroid.parse(test_file.read_text())
        astroid_gateway.parse_file = MagicMock(return_value=module_node)

        bridge = ViolationBridgeService(astroid_gateway)

        linter_results = [
            LinterResult(
                code="W9006",
                message="Law of Demeter: Chain access (obj.a.b.c) exceeds one level",
                locations=[f"{test_file}:2"],
            )
        ]

        violations = bridge.convert_linter_results_to_violations(
            linter_results, str(test_file)
        )

        # Should find at least one violation (may find multiple nodes at line 2)
        assert len(violations) >= 1
        w9006_violations = [v for v in violations if v.code == "W9006"]
        assert len(w9006_violations) >= 1
        assert w9006_violations[0].fixable is True
        assert w9006_violations[0].is_comment_only is True

    def test_identifies_comment_only_rules(self) -> None:
        """Test that comment-only rules are identified correctly."""
        astroid_gateway = MagicMock()
        bridge = ViolationBridgeService(astroid_gateway)

        assert bridge._is_comment_only_rule("W9006") is True
        assert bridge._is_comment_only_rule("clean-arch-demeter") is True
        assert bridge._is_comment_only_rule("W9001") is True
        assert bridge._is_comment_only_rule("W9015") is False  # Type hint, not comment-only

    def test_handles_multiple_locations(self, tmp_path) -> None:
        """Test handling multiple locations for same violation."""
        test_file = tmp_path / "test.py"
        test_file.write_text("""def example():
    x = obj.a.b.c()
    y = obj2.d.e.f()
    return x, y
""")

        astroid_gateway = MagicMock()
        module_node = astroid.parse(test_file.read_text())
        astroid_gateway.parse_file = MagicMock(return_value=module_node)

        bridge = ViolationBridgeService(astroid_gateway)

        linter_results = [
            LinterResult(
                code="W9006",
                message="Law of Demeter violation",
                locations=[f"{test_file}:2", f"{test_file}:3"],
            )
        ]

        violations = bridge.convert_linter_results_to_violations(
            linter_results, str(test_file)
        )

        # Should create at least one violation per location (may find multiple nodes per line)
        assert len(violations) >= 1
        w9006_violations = [v for v in violations if v.code == "W9006"]
        assert len(w9006_violations) >= 1
        assert all(v.is_comment_only for v in w9006_violations)

    def test_handles_parse_failure_gracefully(self, tmp_path) -> None:
        """Test that parse failures are handled gracefully."""
        test_file = tmp_path / "test.py"
        test_file.write_text("invalid python syntax {[}")

        astroid_gateway = MagicMock()
        astroid_gateway.parse_file.return_value = None

        bridge = ViolationBridgeService(astroid_gateway)

        linter_results = [
            LinterResult(
                code="W9006",
                message="Test",
                locations=[f"{test_file}:1"],
            )
        ]

        violations = bridge.convert_linter_results_to_violations(
            linter_results, str(test_file)
        )

        # Should return empty list on parse failure
        assert len(violations) == 0

    def test_finds_node_at_line(self, tmp_path) -> None:
        """Test finding astroid node at specific line."""
        test_file = tmp_path / "test.py"
        test_file.write_text("""def example():
    x = 1
    y = 2
    return x + y
""")

        astroid_gateway = MagicMock()
        module_node = astroid.parse(test_file.read_text())

        bridge = ViolationBridgeService(astroid_gateway)

        # Find node at line 1 (function definition)
        node = bridge._find_node_at_line(module_node, 1)
        # Should find the function node
        assert node is not None
        assert isinstance(node, astroid.nodes.NodeNG)

    def test_handles_invalid_location_format(self, tmp_path) -> None:
        """Test handling invalid location formats."""
        test_file = tmp_path / "test.py"
        test_file.write_text("x = 1\n")

        astroid_gateway = MagicMock()
        module_node = astroid.parse(test_file.read_text())
        astroid_gateway.parse_file = MagicMock(return_value=module_node)

        bridge = ViolationBridgeService(astroid_gateway)

        linter_results = [
            LinterResult(
                code="W9006",
                message="Test",
                locations=["invalid_location"],  # No colon
            )
        ]

        violations = bridge.convert_linter_results_to_violations(
            linter_results, str(test_file)
        )

        # Should skip invalid locations
        assert len(violations) == 0

    def test_handles_invalid_line_number(self, tmp_path) -> None:
        """Test handling invalid line numbers in location."""
        test_file = tmp_path / "test.py"
        test_file.write_text("x = 1\n")

        astroid_gateway = MagicMock()
        module_node = astroid.parse(test_file.read_text())
        astroid_gateway.parse_file = MagicMock(return_value=module_node)

        bridge = ViolationBridgeService(astroid_gateway)

        linter_results = [
            LinterResult(
                code="W9006",
                message="Test",
                locations=[f"{test_file}:not_a_number"],  # Invalid line number
            )
        ]

        violations = bridge.convert_linter_results_to_violations(
            linter_results, str(test_file)
        )

        # Should skip invalid line numbers
        assert len(violations) == 0

    def test_handles_parse_exception(self, tmp_path) -> None:
        """Test handling parse exceptions gracefully."""
        test_file = tmp_path / "test.py"
        test_file.write_text("x = 1\n")

        astroid_gateway = MagicMock()
        # Make parse_file raise an exception
        astroid_gateway.parse_file = MagicMock(side_effect=Exception("Parse error"))

        bridge = ViolationBridgeService(astroid_gateway)

        linter_results = [
            LinterResult(
                code="W9006",
                message="Test",
                locations=[f"{test_file}:1"],
            )
        ]

        violations = bridge.convert_linter_results_to_violations(
            linter_results, str(test_file)
        )

        # Should return empty list on exception
        assert len(violations) == 0

    def test_find_node_at_line_handles_exception(self) -> None:
        """Test that _find_node_at_line handles exceptions."""
        astroid_gateway = MagicMock()
        bridge = ViolationBridgeService(astroid_gateway)

        # Create a mock module that will raise exception
        mock_module = MagicMock()
        mock_module.nodes_of_class = MagicMock(side_effect=Exception("Error"))

        node = bridge._find_node_at_line(mock_module, 1)
        assert node is None

    def test_find_node_at_line_finds_closest_node(self, tmp_path) -> None:
        """Test that _find_node_at_line finds closest node when exact match not found."""
        test_file = tmp_path / "test.py"
        test_file.write_text("""def example():
    x = 1
    y = 2
    return x + y
""")

        astroid_gateway = MagicMock()
        module_node = astroid.parse(test_file.read_text())
        astroid_gateway.parse_file = MagicMock(return_value=module_node)

        bridge = ViolationBridgeService(astroid_gateway)

        # Find node at line 1 (function definition)
        node = bridge._find_node_at_line(module_node, 1)
        # Should find the function node
        assert node is not None
        assert isinstance(node, astroid.nodes.NodeNG)
        assert hasattr(node, "lineno") and node.lineno == 1

        # Test finding closest when line doesn't exist
        # Search for a line that doesn't exist (line 10)
        # The function should find the closest node (Return at line 4)
        node2 = bridge._find_node_at_line(module_node, 10)
        # Should return the closest node (Return at line 4, distance = 6)
        assert node2 is not None, "Should find closest node when exact match not found"
        assert isinstance(node2, astroid.nodes.NodeNG)
        # The closest should be the Return node at line 4
        assert hasattr(node2, "lineno")
        assert node2.lineno == 4  # Return statement is closest to line 10

    def test_find_node_at_line_handles_exception_in_nodes_of_class(self) -> None:
        """Test that _find_node_at_line handles exception in nodes_of_class."""
        astroid_gateway = MagicMock()
        bridge = ViolationBridgeService(astroid_gateway)

        # Create a mock module that raises exception in nodes_of_class
        mock_module = MagicMock()
        mock_module.nodes_of_class = MagicMock(side_effect=Exception("Error"))

        node = bridge._find_node_at_line(mock_module, 1)
        # Should return None on exception (line 96-98)
        assert node is None
