"""Unit tests for LibCSTFixerGateway."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock

import libcst as cst

from clean_architecture_linter.infrastructure.gateways.libcst_fixer_gateway import LibCSTFixerGateway


class TestLibCSTFixerGateway:
    """Test LibCSTFixerGateway transformer application."""

    def test_apply_fixes_returns_false_when_no_transformers(self) -> None:
        """Test that apply_fixes returns False when transformers list is empty."""
        gateway = LibCSTFixerGateway()
        with TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("def hello():\n    pass\n")

            result = gateway.apply_fixes(str(test_file), [])
            assert result is False

    def test_apply_fixes_applies_single_transformer(self) -> None:
        """Test that a single transformer is applied correctly."""
        gateway = LibCSTFixerGateway()

        class AddCommentTransformer(cst.CSTTransformer):
            def leave_Module(self, original_node: cst.Module, updated_node: cst.Module) -> cst.Module:
                # Add a comment at the top
                new_body = [
                    cst.SimpleStatementLine(body=[cst.Expr(value=cst.SimpleString('"""Added comment"""'))]),
                    *updated_node.body
                ]
                return updated_node.with_changes(body=new_body)

        with TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("def hello():\n    pass\n")

            result = gateway.apply_fixes(str(test_file), [AddCommentTransformer()])
            assert result is True

            # Verify file was modified
            content = test_file.read_text()
            assert "Added comment" in content

    def test_apply_fixes_applies_multiple_transformers_sequentially(self) -> None:
        """Test that multiple transformers are applied in sequence."""
        gateway = LibCSTFixerGateway()

        class FirstTransformer(cst.CSTTransformer):
            def leave_Module(self, original_node: cst.Module, updated_node: cst.Module) -> cst.Module:
                # Add comment at module level
                new_body = [
                    cst.SimpleStatementLine(body=[cst.Expr(value=cst.SimpleString('"""First"""'))]),
                    *updated_node.body
                ]
                return updated_node.with_changes(body=new_body)

        class SecondTransformer(cst.CSTTransformer):
            def leave_Module(self, original_node: cst.Module, updated_node: cst.Module) -> cst.Module:
                # Add another comment at module level
                new_body = [
                    cst.SimpleStatementLine(body=[cst.Expr(value=cst.SimpleString('"""Second"""'))]),
                    *updated_node.body
                ]
                return updated_node.with_changes(body=new_body)

        with TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("def hello():\n    pass\n")

            result = gateway.apply_fixes(
                str(test_file),
                [FirstTransformer(), SecondTransformer()]
            )
            assert result is True

            content = test_file.read_text()
            assert "First" in content
            assert "Second" in content

    def test_apply_fixes_returns_false_when_no_changes(self) -> None:
        """Test that apply_fixes returns False when transformers don't modify code."""
        gateway = LibCSTFixerGateway()

        class NoOpTransformer(cst.CSTTransformer):
            pass  # Does nothing

        with TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            original_content = "def hello():\n    pass\n"
            test_file.write_text(original_content)

            result = gateway.apply_fixes(str(test_file), [NoOpTransformer()])
            assert result is False

            # Verify file was not modified
            assert test_file.read_text() == original_content

    def test_apply_fixes_handles_none_transformers(self) -> None:
        """Test that None transformers are skipped."""
        gateway = LibCSTFixerGateway()

        class WorkingTransformer(cst.CSTTransformer):
            def leave_Module(self, original_node: cst.Module, updated_node: cst.Module) -> cst.Module:
                new_body = [
                    cst.SimpleStatementLine(body=[cst.Expr(value=cst.SimpleString('"""Working"""'))]),
                    *updated_node.body
                ]
                return updated_node.with_changes(body=new_body)

        with TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("def hello():\n    pass\n")

            # Mix of None and working transformers
            result = gateway.apply_fixes(
                str(test_file),
                [None, WorkingTransformer(), None]
            )
            assert result is True

            content = test_file.read_text()
            assert "Working" in content

    def test_apply_fixes_handles_invalid_file_gracefully(self) -> None:
        """Test that apply_fixes handles errors gracefully."""
        gateway = LibCSTFixerGateway()

        class BadTransformer(cst.CSTTransformer):
            def leave_Module(self, original_node: cst.Module, updated_node: cst.Module) -> cst.Module:
                # This will cause an error
                raise ValueError("Test error")

        with TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("def hello():\n    pass\n")

            result = gateway.apply_fixes(str(test_file), [BadTransformer()])
            assert result is False

    def test_apply_fixes_handles_missing_file_gracefully(self) -> None:
        """Test that apply_fixes handles missing files gracefully."""
        gateway = LibCSTFixerGateway()
        transformer = Mock(spec=cst.CSTTransformer)

        result = gateway.apply_fixes("/nonexistent/file.py", [transformer])
        assert result is False
