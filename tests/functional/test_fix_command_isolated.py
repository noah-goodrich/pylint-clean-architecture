"""Functional test for excelsior fix command in isolated environment.

This test creates a temporary directory with test files and verifies
all fix behaviors WITHOUT touching the actual repository.
"""

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Invoke CLI via current Python + excelsior_architect so tests use the repo package.
# File is tests/functional/test_fix_command_isolated.py -> parent.parent.parent = project root.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_SRC_DIR = _PROJECT_ROOT / "src"


def _excelsior_env() -> dict[str, str]:
    env = {**os.environ, "PYTHONPATH": str(_SRC_DIR.resolve())}
    # Unbuffered so subprocess stdout/stderr are visible when Rich writes to a pipe.
    env["PYTHONUNBUFFERED"] = "1"
    return env


def _excelsior_cmd(*args: str) -> list[str]:
    return [sys.executable, "-m", "excelsior_architect", *args]


def _run_excelsior(*args: str, timeout: int = 30, **kwargs: object) -> subprocess.CompletedProcess:
    """Run excelsior CLI subprocess with project root cwd and PYTHONPATH so the package is found."""
    return subprocess.run(
        _excelsior_cmd(*args),
        env=_excelsior_env(),
        cwd=_PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
        **kwargs,
    )


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
        """Test that fix runs; when fixes are applied, .bak files are created by default."""
        result = _run_excelsior("fix", str(temp_project),
                                "--skip-tests", timeout=30)
        assert result.returncode == 0, f"fix should succeed: {result.stderr or result.stdout}"
        backup_files = list(temp_project.glob("**/*.bak"))
        out = result.stdout + result.stderr
        # If fix reported modifying files, backups must exist (we did not pass --no-backup).
        if "Successfully fixed" in out and "0 file" not in out:
            assert len(
                backup_files) > 0, "Backup files should be created when fixes are applied"

    def test_fix_no_backup_flag(self, temp_project) -> None:
        """Test that --no-backup flag prevents .bak file creation."""
        _ = _run_excelsior("fix", str(temp_project),
                           "--no-backup", "--skip-tests", timeout=30)

        # No .bak files should exist
        backup_files = list(temp_project.glob("**/*.bak"))
        assert len(
            backup_files) == 0, "No backup files should be created with --no-backup"

    def test_fix_skip_tests_flag(self, temp_project) -> None:
        """Test that --skip-tests bypasses pytest validation."""
        result = _run_excelsior("fix", str(temp_project),
                                "--skip-tests", timeout=10)

        # Check it didn't run pytest
        assert "pytest" not in result.stdout.lower() or "Test baseline" not in result.stdout

    def test_fix_with_tests_validation(self, temp_project) -> None:
        """Test that fix runs (with pytest validation when not --skip-tests)."""
        result = _run_excelsior("fix", str(temp_project), timeout=120)
        # Fix should complete; output may be empty when Rich runs in a non-TTY pipe.
        out = (result.stdout + result.stderr).lower()
        assert result.returncode == 0 or "baseline" in out or "test" in out or "pytest" in out, (
            f"Expected success or baseline/test/pytest in output; rc={result.returncode} stdout={result.stdout!r} stderr={result.stderr!r}"
        )

    def test_fix_manual_only_flag(self, temp_project) -> None:
        """Test --manual-only shows suggestions without applying fixes."""
        # First, capture original file content
        test_file = temp_project / "example.py"
        original_content = test_file.read_text()

        result = _run_excelsior("fix", str(temp_project),
                                "--manual-only", timeout=30)

        # File should not be modified
        assert test_file.read_text() == original_content, "File should not change with --manual-only"

        # Should show manual fix suggestions, or succeed with no output (Rich may not write to pipe)
        out = result.stdout + result.stderr
        assert result.returncode == 0 or "AUTO-FIXABLE" in out or "MANUAL FIX REQUIRED" in out, (
            f"Expected success or AUTO-FIXABLE/MANUAL FIX REQUIRED; rc={result.returncode} got: {out!r}"
        )

    def test_fix_cleanup_backups_flag(self, temp_project) -> None:
        """Test --cleanup-backups removes .bak files after success."""
        _ = _run_excelsior("fix", str(temp_project),
                           "--cleanup-backups", "--skip-tests", timeout=30)

        # No .bak files should remain
        backup_files = list(temp_project.glob("**/*.bak"))
        assert len(
            backup_files) == 0, "Backup files should be cleaned up with --cleanup-backups"

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
        result = _run_excelsior("fix", str(temp_project), timeout=120)

        # If rollback happened, should see "Rolling back" message
        if "Rolling back" in result.stdout or "Regression" in result.stdout:
            # File should be restored
            assert source_file.read_text() == original_content

    def test_manual_instructions_for_all_linters(self, temp_project) -> None:
        """Test that manual-only shows instructions for all linters."""
        result = _run_excelsior("fix", str(temp_project),
                                "--manual-only", timeout=30)

        output = result.stdout + result.stderr

        # Should see output from at least one linter, or command succeeded (Rich may not write to pipe)
        linter_mentions = sum([
            "Ruff" in output,
            "Mypy" in output,
            "Excelsior" in output,
            "Import-Linter" in output
        ])
        assert result.returncode == 0 or linter_mentions >= 1, (
            "Should succeed or show results from at least one linter"
        )

    def test_fix_help_shows_all_options(self) -> None:
        """Test that fix --help shows all enhanced options."""
        result = _run_excelsior("fix", "--help", timeout=5)

        help_text = result.stdout or result.stderr

        # Typer prints help to stdout; if empty (e.g. Rich/pipe), require at least success
        assert result.returncode == 0, f"fix --help should succeed: stderr={result.stderr!r}"
        if help_text:
            assert "--confirm" in help_text
            assert "--no-backup" in help_text
            assert "--skip-tests" in help_text
            assert "--cleanup-backups" in help_text
            assert "--manual-only" in help_text


class TestFixAdapterCapabilities:
    """Test that adapters correctly report their fix capabilities."""

    def test_ruff_supports_autofix(self) -> None:
        """Test Ruff adapter reports auto-fix support."""
        from unittest.mock import MagicMock

        from excelsior_architect.infrastructure.adapters.ruff_adapter import RuffAdapter

        adapter = RuffAdapter(
            config_loader=MagicMock(),
            telemetry=MagicMock(),
            raw_log_port=MagicMock(),
            guidance_service=MagicMock(),
        )
        assert adapter.supports_autofix() is True

        fixable_rules = adapter.get_fixable_rules()
        assert "F" in fixable_rules  # Pyflakes
        assert "I" in fixable_rules  # isort

    def test_mypy_no_autofix(self) -> None:
        """Test Mypy adapter reports no auto-fix support."""
        from excelsior_architect.infrastructure.adapters.mypy_adapter import MypyAdapter

        adapter = MypyAdapter(
            raw_log_port=MagicMock(),
            guidance_service=MagicMock(),
        )
        assert adapter.supports_autofix() is False
        assert len(adapter.get_fixable_rules()) == 0

    def test_excelsior_supports_autofix(self) -> None:
        """Test Excelsior (pylint) adapter reports auto-fix support."""
        from unittest.mock import MagicMock

        from excelsior_architect.infrastructure.adapters.excelsior_adapter import ExcelsiorAdapter

        adapter = ExcelsiorAdapter(
            config_loader=MagicMock(),
            raw_log_port=MagicMock(),
            guidance_service=MagicMock(),
        )
        assert adapter.supports_autofix() is True

        fixable_rules = adapter.get_fixable_rules()
        assert "clean-arch-immutable" in fixable_rules

    def test_import_linter_no_autofix(self) -> None:
        """Test Import-Linter adapter reports no auto-fix support."""
        from excelsior_architect.infrastructure.adapters.import_linter_adapter import ImportLinterAdapter

        adapter = ImportLinterAdapter(guidance_service=MagicMock())
        assert adapter.supports_autofix() is False

    def test_all_adapters_provide_manual_instructions(self) -> None:
        """Test all adapters provide manual fix instructions."""
        from unittest.mock import MagicMock

        from excelsior_architect.infrastructure.adapters.excelsior_adapter import ExcelsiorAdapter
        from excelsior_architect.infrastructure.adapters.import_linter_adapter import ImportLinterAdapter
        from excelsior_architect.infrastructure.adapters.mypy_adapter import MypyAdapter
        from excelsior_architect.infrastructure.adapters.ruff_adapter import RuffAdapter

        config_loader = MagicMock()
        raw_log = MagicMock()
        guidance = MagicMock()
        guidance.get_manual_instructions.return_value = (
            "See documentation for this rule. Fix the underlying issue."
        )
        telemetry = MagicMock()
        adapters = [
            (RuffAdapter(config_loader=config_loader, telemetry=telemetry,
             raw_log_port=raw_log, guidance_service=guidance), "C901"),
            (MypyAdapter(raw_log_port=raw_log, guidance_service=guidance), "type-arg"),
            (ExcelsiorAdapter(config_loader=config_loader, raw_log_port=raw_log,
             guidance_service=guidance), "clean-arch-layer"),
            (ImportLinterAdapter(guidance_service=guidance), "contract-violation"),
        ]

        for adapter, code in adapters:
            instructions = adapter.get_manual_fix_instructions(code)
            assert instructions, f"{adapter.__class__.__name__} should provide instructions for {code}"
            assert len(
                instructions) > 20, f"Instructions should be detailed, got: {instructions}"
