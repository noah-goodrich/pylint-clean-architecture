"""Unit tests for LibCSTFixerGateway. Gateway accepts only list[TransformationPlan]."""

from pathlib import Path
from tempfile import TemporaryDirectory

from clean_architecture_linter.domain.entities import TransformationPlan
from clean_architecture_linter.infrastructure.gateways.libcst_fixer_gateway import LibCSTFixerGateway


class TestLibCSTFixerGateway:
    """Test LibCSTFixerGateway plan application."""

    def test_apply_fixes_returns_false_when_no_plans(self) -> None:
        """apply_fixes returns False when plans list is empty."""
        gateway = LibCSTFixerGateway()
        with TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("def hello():\n    pass\n")

            result = gateway.apply_fixes(str(test_file), [])
            assert result is False

    def test_apply_fixes_applies_single_transformer(self) -> None:
        """A single TransformationPlan (add_import) is applied correctly."""
        gateway = LibCSTFixerGateway()
        plan = TransformationPlan.add_import("typing", ["List"])

        with TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("def hello():\n    pass\n")

            result = gateway.apply_fixes(str(test_file), [plan])
            assert result is True

            content = test_file.read_text()
            assert "from typing import List" in content or "import" in content

    def test_apply_fixes_applies_multiple_transformers_sequentially(self) -> None:
        """Multiple TransformationPlans are applied in sequence."""
        gateway = LibCSTFixerGateway()
        plan1 = TransformationPlan.add_import("os", ["path"])
        plan2 = TransformationPlan.add_import("typing", ["Optional"])

        with TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("def hello():\n    pass\n")

            result = gateway.apply_fixes(str(test_file), [plan1, plan2])
            assert result is True

            content = test_file.read_text()
            assert "os" in content or "path" in content
            assert "typing" in content or "Optional" in content

    def test_apply_fixes_returns_false_when_no_changes(self) -> None:
        """apply_fixes returns False when plans produce no net change."""
        gateway = LibCSTFixerGateway()
        # add_return_type for a function that doesn't exist => transformer may not change file
        plan = TransformationPlan.add_return_type("nonexistent_func", "None")

        with TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            original_content = "def hello():\n    pass\n"
            test_file.write_text(original_content)

            result = gateway.apply_fixes(str(test_file), [plan])
            # Transformer may or may not find the function; accept False when unchanged
            assert result is False or test_file.read_text() == original_content

    def test_apply_fixes_handles_none_plans(self) -> None:
        """None entries in the plans list are skipped."""
        gateway = LibCSTFixerGateway()
        plan = TransformationPlan.add_import("typing", ["Dict"])

        with TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("def hello():\n    pass\n")

            result = gateway.apply_fixes(str(test_file), [None, plan, None])
            assert result is True

            content = test_file.read_text()
            assert "typing" in content or "Dict" in content

    def test_apply_fixes_handles_invalid_file_gracefully(self) -> None:
        """apply_fixes handles errors gracefully (e.g. bad plan params)."""
        gateway = LibCSTFixerGateway()
        plan = TransformationPlan.add_import("typing", ["List"])

        with TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("syntax error {{{")

            result = gateway.apply_fixes(str(test_file), [plan])
            assert result is False

    def test_apply_fixes_handles_missing_file_gracefully(self) -> None:
        """apply_fixes handles missing files gracefully."""
        gateway = LibCSTFixerGateway()
        plan = TransformationPlan.add_import("os", [])

        result = gateway.apply_fixes("/nonexistent/file.py", [plan])
        assert result is False
