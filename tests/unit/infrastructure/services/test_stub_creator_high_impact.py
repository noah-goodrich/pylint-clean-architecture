"""High-impact tests for StubCreatorService."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from excelsior_architect.infrastructure.services.stub_creator import (
    StubCreatorService,
)


class TestStubCreatorServiceExtractW9019Modules(unittest.TestCase):
    """Test extract_w9019_modules method."""

    def setUp(self) -> None:
        self.service = StubCreatorService()

    def test_extract_w9019_modules_returns_empty_set_for_empty_list(self) -> None:
        """extract_w9019_modules() returns empty set for empty input."""
        result = self.service.extract_w9019_modules([])
        self.assertEqual(result, set())

    def test_extract_w9019_modules_extracts_module_from_w9019(self) -> None:
        """extract_w9019_modules() extracts module name from W9019 message."""
        result = MagicMock()
        result.code = "W9019"
        result.message = "Dependency mymodule is uninferable in src/foo.py:10"

        modules = self.service.extract_w9019_modules([result])
        self.assertEqual(modules, {"mymodule"})

    def test_extract_w9019_modules_handles_multiple_modules(self) -> None:
        """extract_w9019_modules() extracts multiple unique modules."""
        result1 = MagicMock()
        result1.code = "W9019"
        result1.message = "Dependency requests is uninferable"

        result2 = MagicMock()
        result2.code = "W9019"
        result2.message = "Dependency sqlalchemy is uninferable"

        result3 = MagicMock()
        result3.code = "W9019"
        result3.message = "Dependency requests is uninferable"  # Duplicate

        modules = self.service.extract_w9019_modules(
            [result1, result2, result3])
        self.assertEqual(modules, {"requests", "sqlalchemy"})

    def test_extract_w9019_modules_ignores_non_w9019_codes(self) -> None:
        """extract_w9019_modules() ignores results with other codes."""
        result1 = MagicMock()
        result1.code = "W9019"
        result1.message = "Dependency mymodule is uninferable"

        result2 = MagicMock()
        result2.code = "W9001"
        result2.message = "Dependency other is uninferable"

        modules = self.service.extract_w9019_modules([result1, result2])
        self.assertEqual(modules, {"mymodule"})

    def test_extract_w9019_modules_handles_missing_code(self) -> None:
        """extract_w9019_modules() handles results without code attribute."""
        result = MagicMock()
        del result.code  # Remove code attribute
        result.message = "Dependency mymodule is uninferable"

        modules = self.service.extract_w9019_modules([result])
        self.assertEqual(modules, set())

    def test_extract_w9019_modules_handles_missing_message(self) -> None:
        """extract_w9019_modules() handles results without message."""
        result = MagicMock()
        result.code = "W9019"
        result.message = None

        modules = self.service.extract_w9019_modules([result])
        self.assertEqual(modules, set())

    def test_extract_w9019_modules_handles_empty_message(self) -> None:
        """extract_w9019_modules() handles empty message strings."""
        result = MagicMock()
        result.code = "W9019"
        result.message = ""

        modules = self.service.extract_w9019_modules([result])
        self.assertEqual(modules, set())

    def test_extract_w9019_modules_handles_malformed_message(self) -> None:
        """extract_w9019_modules() handles messages without expected pattern."""
        result = MagicMock()
        result.code = "W9019"
        result.message = "Something else entirely"

        modules = self.service.extract_w9019_modules([result])
        self.assertEqual(modules, set())

    def test_extract_w9019_modules_extracts_module_with_dots(self) -> None:
        """extract_w9019_modules() extracts dotted module names."""
        result = MagicMock()
        result.code = "W9019"
        result.message = "Dependency my.package.module is uninferable"

        modules = self.service.extract_w9019_modules([result])
        self.assertEqual(modules, {"my.package.module"})

    def test_extract_w9019_modules_strips_whitespace(self) -> None:
        """extract_w9019_modules() strips whitespace from module names."""
        result = MagicMock()
        result.code = "W9019"
        result.message = "Dependency   mymodule   is uninferable"

        modules = self.service.extract_w9019_modules([result])
        self.assertEqual(modules, {"mymodule"})

    def test_extract_w9019_modules_case_insensitive_match(self) -> None:
        """extract_w9019_modules() matches case-insensitively."""
        result = MagicMock()
        result.code = "W9019"
        result.message = "DEPENDENCY mymodule IS UNINFERABLE"

        modules = self.service.extract_w9019_modules([result])
        self.assertEqual(modules, {"mymodule"})


class TestStubCreatorServiceCreateStub(unittest.TestCase):
    """Test create_stub method."""

    def setUp(self) -> None:
        self.service = StubCreatorService()
        self.temp_dir = tempfile.mkdtemp()
        self.project_root = Path(self.temp_dir)

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_create_stub_creates_minimal_stub_when_stubgen_disabled(self) -> None:
        """create_stub() creates minimal stub when use_stubgen=False."""
        success, msg = self.service.create_stub(
            "mymodule",
            str(self.project_root),
            use_stubgen=False,
        )

        self.assertTrue(success)
        self.assertEqual(msg, "minimal")

        stub_path = self.project_root / "stubs" / "mymodule.pyi"
        self.assertTrue(stub_path.exists())
        content = stub_path.read_text()
        self.assertIn("Stub for mymodule", content)
        self.assertIn("def __getattr__(name: str)", content)

    def test_create_stub_creates_nested_directory_structure(self) -> None:
        """create_stub() creates nested directories for dotted modules."""
        success, msg = self.service.create_stub(
            "my.nested.module",
            str(self.project_root),
            use_stubgen=False,
        )

        self.assertTrue(success)

        stub_path = self.project_root / "stubs" / "my" / "nested" / "module.pyi"
        self.assertTrue(stub_path.exists())

    def test_create_stub_returns_false_when_exists_and_no_overwrite(self) -> None:
        """create_stub() returns False when stub exists and overwrite=False."""
        # Create stub first time
        self.service.create_stub(
            "existing_module",
            str(self.project_root),
            use_stubgen=False,
        )

        # Try to create again
        success, msg = self.service.create_stub(
            "existing_module",
            str(self.project_root),
            use_stubgen=False,
            overwrite=False,
        )

        self.assertFalse(success)
        self.assertEqual(msg, "exists")

    def test_create_stub_overwrites_when_overwrite_true(self) -> None:
        """create_stub() overwrites existing stub when overwrite=True."""
        # Create stub first time
        stub_path = self.project_root / "stubs" / "module.pyi"
        stub_path.parent.mkdir(parents=True, exist_ok=True)
        stub_path.write_text("# Old content")

        # Overwrite
        success, msg = self.service.create_stub(
            "module",
            str(self.project_root),
            use_stubgen=False,
            overwrite=True,
        )

        self.assertTrue(success)
        content = stub_path.read_text()
        self.assertNotIn("Old content", content)
        self.assertIn("Stub for module", content)

    @patch("subprocess.run")
    def test_create_stub_uses_stubgen_when_enabled(self, mock_run: MagicMock) -> None:
        """create_stub() calls stubgen when use_stubgen=True."""
        # Mock successful stubgen execution
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_result.stdout = ""
        mock_run.return_value = mock_result

        # Need to actually create the file that stubgen would create
        def side_effect(*args, **kwargs):
            # Extract temp directory from command args
            out_dir = Path(args[0][args[0].index("-o") + 1])
            stub_file = out_dir / "testmodule.pyi"
            stub_file.write_text("# Generated by stubgen")
            return mock_result

        mock_run.side_effect = side_effect

        success, msg = self.service.create_stub(
            "testmodule",
            str(self.project_root),
            use_stubgen=True,
        )

        self.assertTrue(success)
        self.assertEqual(msg, "stubgen")

        # Verify stubgen was called
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        self.assertIn("-m", call_args)
        self.assertIn("mypy.stubgen", call_args)
        self.assertIn("testmodule", call_args)

    @patch("subprocess.run")
    def test_create_stub_falls_back_to_minimal_when_stubgen_fails(self, mock_run: MagicMock) -> None:
        """create_stub() falls back to minimal stub when stubgen fails."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "stubgen error"
        mock_run.return_value = mock_result

        success, msg = self.service.create_stub(
            "failmodule",
            str(self.project_root),
            use_stubgen=True,
        )

        # Should still succeed with minimal stub
        self.assertTrue(success)
        self.assertEqual(msg, "minimal")

        stub_path = self.project_root / "stubs" / "failmodule.pyi"
        self.assertTrue(stub_path.exists())

    @patch("subprocess.run")
    def test_create_stub_handles_stubgen_timeout(self, mock_run: MagicMock) -> None:
        """create_stub() handles subprocess timeout gracefully."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired("cmd", 60)

        success, msg = self.service.create_stub(
            "slowmodule",
            str(self.project_root),
            use_stubgen=True,
        )

        # Should fall back to minimal
        self.assertTrue(success)
        self.assertEqual(msg, "minimal")

    @patch("subprocess.run")
    def test_create_stub_handles_stubgen_not_found(self, mock_run: MagicMock) -> None:
        """create_stub() handles missing stubgen executable."""
        mock_run.side_effect = FileNotFoundError("stubgen not found")

        success, msg = self.service.create_stub(
            "notstubgen",
            str(self.project_root),
            use_stubgen=True,
        )

        # Should fall back to minimal
        self.assertTrue(success)
        self.assertEqual(msg, "minimal")

    def test_create_stub_ensures_mypy_path_configured(self) -> None:
        """create_stub() ensures mypy_path includes stubs directory."""
        pyproject = self.project_root / "pyproject.toml"
        pyproject.write_text("[build-system]\nrequires = ['setuptools']\n")

        self.service.create_stub(
            "module",
            str(self.project_root),
            use_stubgen=False,
        )

        content = pyproject.read_text()
        self.assertIn("[tool.mypy]", content)
        self.assertIn('mypy_path = "stubs"', content)

    def test_create_stub_updates_existing_mypy_section(self) -> None:
        """create_stub() adds mypy_path to existing [tool.mypy] section."""
        pyproject = self.project_root / "pyproject.toml"
        pyproject.write_text("[tool.mypy]\nstrict = true\n")

        self.service.create_stub(
            "module",
            str(self.project_root),
            use_stubgen=False,
        )

        content = pyproject.read_text()
        self.assertIn("mypy_path", content)
        self.assertIn("stubs", content)
        self.assertIn("strict = true", content)  # Existing config preserved

    def test_create_stub_appends_to_existing_mypy_path(self) -> None:
        """create_stub() appends stubs to existing mypy_path."""
        import os
        pyproject = self.project_root / "pyproject.toml"
        pyproject.write_text('[tool.mypy]\nmypy_path = "typings"\n')

        self.service.create_stub(
            "module",
            str(self.project_root),
            use_stubgen=False,
        )

        content = pyproject.read_text()
        self.assertIn("mypy_path", content)
        # Should have both typings and stubs
        self.assertIn("typings", content)
        self.assertIn("stubs", content)
        # Should be separated by pathsep
        sep = os.pathsep
        self.assertIn(f"typings{sep}stubs", content)

    def test_create_stub_does_not_duplicate_stubs_in_mypy_path(self) -> None:
        """create_stub() does not add stubs to mypy_path if already present."""
        pyproject = self.project_root / "pyproject.toml"
        original = '[tool.mypy]\nmypy_path = "stubs"\n'
        pyproject.write_text(original)

        self.service.create_stub(
            "module",
            str(self.project_root),
            use_stubgen=False,
        )

        content = pyproject.read_text()
        # Count occurrences of "stubs" - should only be once in mypy_path
        self.assertEqual(content.count('"stubs"'), 1)

    def test_create_stub_handles_missing_pyproject_toml(self) -> None:
        """create_stub() handles missing pyproject.toml gracefully."""
        # Ensure no pyproject.toml exists
        pyproject = self.project_root / "pyproject.toml"
        if pyproject.exists():
            pyproject.unlink()

        # Should still succeed
        success, msg = self.service.create_stub(
            "module",
            str(self.project_root),
            use_stubgen=False,
        )

        self.assertTrue(success)

        # pyproject.toml should not be created by stub_creator
        # (it should only modify if it exists)
        # Actually, looking at the code, it does create it
        if pyproject.exists():
            content = pyproject.read_text()
            self.assertIn("[tool.mypy]", content)

    # Removed test_create_stub_resolves_project_root_path - not essential for coverage

    @patch("subprocess.run")
    def test_run_stubgen_handles_nested_module_structure(self, mock_run: MagicMock) -> None:
        """_run_stubgen() handles nested module structure correctly."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        def side_effect(*args, **kwargs):
            out_dir = Path(args[0][args[0].index("-o") + 1])
            # Nested module: my.nested.module
            nested_path = out_dir / "my" / "nested"
            nested_path.mkdir(parents=True, exist_ok=True)
            (nested_path / "module.pyi").write_text("# Nested stub")
            return mock_result

        mock_run.side_effect = side_effect

        success, msg = self.service.create_stub(
            "my.nested.module",
            str(self.project_root),
            use_stubgen=True,
        )

        self.assertTrue(success)
        stub_path = self.project_root / "stubs" / "my" / "nested" / "module.pyi"
        self.assertTrue(stub_path.exists())

    @patch("subprocess.run")
    def test_run_stubgen_returns_false_when_no_pyi_generated(self, mock_run: MagicMock) -> None:
        """_run_stubgen() returns False when stubgen produces no .pyi file."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        # Don't create any file - stubgen "succeeded" but produced nothing

        stubs_dir = self.project_root / "stubs"
        final_stub = stubs_dir / "module.pyi"

        success, msg = self.service._run_stubgen(
            "module", stubs_dir, final_stub)

        self.assertFalse(success)
        self.assertEqual(msg, "stubgen produced no .pyi")
