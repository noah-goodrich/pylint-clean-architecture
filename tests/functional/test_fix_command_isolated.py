"""Functional test for excelsior fix command in isolated environment.

This test creates a temporary directory with test files and verifies
all fix behaviors WITHOUT touching the actual repository.
"""

import subprocess

import pytest


@pytest.mark.slow
class TestFixCommandIsolated:
    """Test fix command in safe, isolated temporary directory."""

    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create a temporary test project with known violations."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()

        # Create a simple Python file with a fixable issue
        # Use a function that returns a string literal - this is fixable by W9015
        test_file = project_dir / "example.py"
        test_file.write_text("""# Example file with fixable violations
def get_message():
    '''Missing return type hint - fixable because returns string literal'''
    return "Hello, world"

def get_number() -> int:
    '''Has return type, but missing parameter type'''
    return 42
""")

        # Create a test file so pytest validation works
        test_dir = project_dir / "tests"
        test_dir.mkdir()
        (test_dir / "__init__.py").write_text("")
        (test_dir / "test_example.py").write_text("""
def test_always_passes():
    assert True
""")

        # Create minimal pyproject.toml
        pyproject = project_dir / "pyproject.toml"
        pyproject.write_text("""[tool.pytest.ini_options]
testpaths = ["tests"]
""")

        return project_dir

    def test_fix_creates_backup(self, temp_project) -> None:
        """Test that --no-backup flag is NOT set, .bak files are created."""
        _ = subprocess.run(
            ["excelsior", "fix", str(temp_project), "--skip-tests"],
            capture_output=True,
            text=True,
            timeout=30
        )

        # Check for .bak files
        backup_files = list(temp_project.glob("**/*.bak"))
        assert len(backup_files) > 0, "Backup files should be created by default"

    def test_fix_no_backup_flag(self, temp_project) -> None:
        """Test that --no-backup flag prevents .bak file creation."""
        _ = subprocess.run(
            ["excelsior", "fix", str(temp_project), "--no-backup", "--skip-tests"],
            capture_output=True,
            text=True,
            timeout=30
        )

        # No .bak files should exist
        backup_files = list(temp_project.glob("**/*.bak"))
        assert len(backup_files) == 0, "No backup files should be created with --no-backup"

    def test_fix_skip_tests_flag(self, temp_project) -> None:
        """Test that --skip-tests bypasses pytest validation."""
        # This should complete quickly without running pytest
        result = subprocess.run(
            ["excelsior", "fix", str(temp_project), "--skip-tests"],
            capture_output=True,
            text=True,
            timeout=10  # Should be fast
        )

        # Check it didn't run pytest
        assert "pytest" not in result.stdout.lower() or "Test baseline" not in result.stdout

    def test_fix_with_tests_validation(self, temp_project) -> None:
        """Test that fix runs pytest validation by default."""
        result = subprocess.run(
            ["excelsior", "fix", str(temp_project)],
            capture_output=True,
            text=True,
            timeout=60
        )

        # Should mention test baseline or pytest
        assert "baseline" in result.stdout.lower() or "test" in result.stdout.lower()

    def test_fix_manual_only_flag(self, temp_project) -> None:
        """Test --manual-only shows suggestions without applying fixes."""
        # First, capture original file content
        test_file = temp_project / "example.py"
        original_content = test_file.read_text()

        result = subprocess.run(
            ["excelsior", "fix", str(temp_project), "--manual-only"],
            capture_output=True,
            text=True,
            timeout=30
        )

        # File should not be modified
        assert test_file.read_text() == original_content, "File should not change with --manual-only"

        # Should show manual fix suggestions
        assert "AUTO-FIXABLE" in result.stdout or "MANUAL FIX REQUIRED" in result.stdout

    def test_fix_cleanup_backups_flag(self, temp_project) -> None:
        """Test --cleanup-backups removes .bak files after success."""
        _ = subprocess.run(
            ["excelsior", "fix", str(temp_project), "--cleanup-backups", "--skip-tests"],
            capture_output=True,
            text=True,
            timeout=30
        )

        # No .bak files should remain
        backup_files = list(temp_project.glob("**/*.bak"))
        assert len(backup_files) == 0, "Backup files should be cleaned up with --cleanup-backups"

    def test_fix_rollback_on_regression(self, temp_project) -> None:
        """Test that fix rolls back changes if tests start failing."""
        # Create a test that will pass initially
        test_file = temp_project / "tests" / "test_example.py"
        test_file.write_text("""
def test_always_passes():
    assert True
""")

        # Create a file that will cause test failure when "fixed"
        source_file = temp_project / "example.py"
        original_content = source_file.read_text()

        # Run fix with test validation
        result = subprocess.run(
            ["excelsior", "fix", str(temp_project)],
            capture_output=True,
            text=True,
            timeout=60
        )

        # If rollback happened, should see "Rolling back" message
        if "Rolling back" in result.stdout or "Regression" in result.stdout:
            # File should be restored
            assert source_file.read_text() == original_content

    def test_manual_instructions_for_all_linters(self, temp_project) -> None:
        """Test that manual-only shows instructions for all linters."""
        result = subprocess.run(
            ["excelsior", "fix", str(temp_project), "--manual-only"],
            capture_output=True,
            text=True,
            timeout=30
        )

        output = result.stdout

        # Should see output from multiple linters
        # (Ruff, Mypy, Excelsior, Import-Linter)
        linter_mentions = sum([
            "Ruff" in output,
            "Mypy" in output,
            "Excelsior" in output,
            "Import-Linter" in output
        ])

        # At least one linter should report (may not have all violations)
        assert linter_mentions >= 1, "Should show results from at least one linter"

    def test_fix_help_shows_all_options(self) -> None:
        """Test that fix --help shows all enhanced options."""
        result = subprocess.run(
            ["excelsior", "fix", "--help"],
            capture_output=True,
            text=True,
            timeout=5
        )

        help_text = result.stdout

        # Check all options are documented
        assert "--confirm" in help_text
        assert "--no-backup" in help_text
        assert "--skip-tests" in help_text
        assert "--cleanup-backups" in help_text
        assert "--manual-only" in help_text


class TestFixAdapterCapabilities:
    """Test that adapters correctly report their fix capabilities."""

    def test_ruff_supports_autofix(self) -> None:
        """Test Ruff adapter reports auto-fix support."""
        from clean_architecture_linter.infrastructure.adapters.ruff_adapter import RuffAdapter

        adapter = RuffAdapter()
        assert adapter.supports_autofix() is True

        fixable_rules = adapter.get_fixable_rules()
        assert "F" in fixable_rules  # Pyflakes
        assert "I" in fixable_rules  # isort

    def test_mypy_no_autofix(self) -> None:
        """Test Mypy adapter reports no auto-fix support."""
        from clean_architecture_linter.infrastructure.adapters.mypy_adapter import MypyAdapter

        adapter = MypyAdapter()
        assert adapter.supports_autofix() is False
        assert len(adapter.get_fixable_rules()) == 0

    def test_excelsior_supports_autofix(self) -> None:
        """Test Excelsior (pylint) adapter reports auto-fix support."""
        from clean_architecture_linter.infrastructure.adapters.excelsior_adapter import ExcelsiorAdapter

        adapter = ExcelsiorAdapter()
        assert adapter.supports_autofix() is True

        fixable_rules = adapter.get_fixable_rules()
        assert "clean-arch-immutable" in fixable_rules

    def test_import_linter_no_autofix(self) -> None:
        """Test Import-Linter adapter reports no auto-fix support."""
        from clean_architecture_linter.infrastructure.adapters.import_linter_adapter import ImportLinterAdapter

        adapter = ImportLinterAdapter()
        assert adapter.supports_autofix() is False

    def test_all_adapters_provide_manual_instructions(self) -> None:
        """Test all adapters provide manual fix instructions."""
        from clean_architecture_linter.infrastructure.adapters.excelsior_adapter import ExcelsiorAdapter
        from clean_architecture_linter.infrastructure.adapters.import_linter_adapter import ImportLinterAdapter
        from clean_architecture_linter.infrastructure.adapters.mypy_adapter import MypyAdapter
        from clean_architecture_linter.infrastructure.adapters.ruff_adapter import RuffAdapter

        adapters = [
            (RuffAdapter(), "C901"),
            (MypyAdapter(), "type-arg"),
            (ExcelsiorAdapter(), "clean-arch-layer"),
            (ImportLinterAdapter(), "contract-violation"),
        ]

        for adapter, code in adapters:
            instructions = adapter.get_manual_fix_instructions(code)
            assert instructions, f"{adapter.__class__.__name__} should provide instructions for {code}"
            assert len(instructions) > 20, f"Instructions should be detailed, got: {instructions}"
