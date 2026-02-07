"""Unit tests for StubCreatorService: stub generation for end-user projects."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from excelsior_architect.infrastructure.services.stub_creator import (
    StubCreatorService,
)
from excelsior_architect.infrastructure.services.stub_authority import (
    StubAuthority,
)


class TestStubCreatorServiceCreateStub:
    """Tests for StubCreatorService.create_stub."""

    def test_creates_stub_in_project_stubs_directory(self) -> None:
        """Stubs are created in {project_root}/stubs/, not bundled stubs."""
        svc = StubCreatorService()
        with tempfile.TemporaryDirectory() as tmp:
            # Create a minimal pyproject.toml
            (Path(tmp) / "pyproject.toml").write_text(
                "[project]\nname = 'test-project'\n"
            )

            ok, msg = svc.create_stub(
                "my_custom_lib",
                tmp,
                use_stubgen=False,  # Skip stubgen, use minimal stub
            )

            assert ok is True
            assert msg == "minimal"

            stub_path = Path(tmp) / "stubs" / "my_custom_lib.pyi"
            assert stub_path.exists()
            content = stub_path.read_text()
            assert "Stub for my_custom_lib" in content

    def test_creates_nested_stub_path(self) -> None:
        """Nested module stubs are created with correct directory structure."""
        svc = StubCreatorService()
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) /
             "pyproject.toml").write_text("[project]\nname = 'test'\n")

            ok, _ = svc.create_stub(
                "some_pkg.submodule.api", tmp, use_stubgen=False)

            assert ok is True
            stub_path = Path(tmp) / "stubs" / "some_pkg" / \
                "submodule" / "api.pyi"
            assert stub_path.exists()

    def test_updates_pyproject_mypy_path(self) -> None:
        """Creating a stub adds 'stubs' to mypy_path in pyproject.toml."""
        svc = StubCreatorService()
        with tempfile.TemporaryDirectory() as tmp:
            pyproject = Path(tmp) / "pyproject.toml"
            pyproject.write_text("[project]\nname = 'test'\n")

            svc.create_stub("my_lib", tmp, use_stubgen=False)

            content = pyproject.read_text()
            assert "[tool.mypy]" in content
            assert 'mypy_path = "stubs"' in content

    def test_does_not_overwrite_existing_stub_by_default(self) -> None:
        """Existing stubs are not overwritten unless overwrite=True."""
        svc = StubCreatorService()
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) /
             "pyproject.toml").write_text("[project]\nname = 'test'\n")
            stubs_dir = Path(tmp) / "stubs"
            stubs_dir.mkdir()
            existing_stub = stubs_dir / "my_lib.pyi"
            existing_stub.write_text("# Existing content\n")

            ok, msg = svc.create_stub("my_lib", tmp, use_stubgen=False)

            assert ok is False
            assert msg == "exists"
            assert existing_stub.read_text() == "# Existing content\n"

    def test_overwrites_existing_stub_when_requested(self) -> None:
        """Existing stubs are overwritten when overwrite=True."""
        svc = StubCreatorService()
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) /
             "pyproject.toml").write_text("[project]\nname = 'test'\n")
            stubs_dir = Path(tmp) / "stubs"
            stubs_dir.mkdir()
            existing_stub = stubs_dir / "my_lib.pyi"
            existing_stub.write_text("# Existing content\n")

            ok, msg = svc.create_stub(
                "my_lib", tmp, use_stubgen=False, overwrite=True)

            assert ok is True
            assert "Stub for my_lib" in existing_stub.read_text()


class TestStubCreatorAndAuthorityIntegration:
    """Integration tests: stubs created by StubCreatorService are found by StubAuthority."""

    def test_user_generated_stub_is_found_by_stub_authority(self) -> None:
        """StubAuthority finds stubs created by StubCreatorService in user's project."""
        creator = StubCreatorService()
        authority = StubAuthority()

        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) /
             "pyproject.toml").write_text("[project]\nname = 'test'\n")

            # User generates a stub for their custom library
            creator.create_stub("my_custom_lib", tmp, use_stubgen=False)

            # StubAuthority can find it when given the project root
            stub_path = authority.get_stub_path("my_custom_lib", tmp)

            assert stub_path is not None
            assert "my_custom_lib.pyi" in stub_path

    def test_user_stub_with_class_attribute_is_resolvable(self) -> None:
        """StubAuthority resolves attributes from user-generated stubs."""
        authority = StubAuthority()

        with tempfile.TemporaryDirectory() as tmp:
            stubs_dir = Path(tmp) / "stubs"
            stubs_dir.mkdir()
            (stubs_dir / "my_api.pyi").write_text(
                "class MyClient:\n"
                "    base_url: str\n"
                "    timeout: int\n"
            )

            # Resolve attribute type
            attr_type = authority.get_attribute_type(
                "my_api", "MyClient", "base_url", tmp)

            assert attr_type == "builtins.str"

    def test_bundled_stubs_take_precedence_over_project_stubs(self) -> None:
        """Bundled stubs (astroid, etc.) are found even if project has same module."""
        authority = StubAuthority()

        with tempfile.TemporaryDirectory() as tmp:
            # Create a "competing" project stub for astroid
            stubs_dir = Path(tmp) / "stubs"
            stubs_dir.mkdir()
            (stubs_dir / "astroid").mkdir()
            (stubs_dir / "astroid" / "__init__.pyi").write_text(
                "# User's broken astroid stub\n"
                "class ClassDef:\n"
                "    pass  # No attributes!\n"
            )

            # Bundled stub should still be found (has proper attributes)
            attr_type = authority.get_attribute_type(
                "astroid.nodes", "ClassDef", "locals", tmp)

            # Should resolve from bundled stub, not user's broken stub
            assert attr_type == "builtins.dict"


class TestStubCreatorExtractW9019Modules:
    """Tests for extracting module names from W9019 violations."""

    def test_extracts_module_from_w9019_message(self) -> None:
        """W9019 messages with 'Dependency X is uninferable' are parsed correctly."""
        svc = StubCreatorService()

        results = [
            MagicMock(code="W9019",
                      message="Dependency snowflake.connector is uninferable"),
            MagicMock(code="W9019", message="Dependency pandas is uninferable"),
            # Not W9019
            MagicMock(code="W9001", message="Some other violation"),
        ]

        modules = svc.extract_w9019_modules(results)

        assert modules == {"snowflake.connector", "pandas"}

    def test_returns_empty_for_no_w9019(self) -> None:
        """Returns empty set when no W9019 violations present."""
        svc = StubCreatorService()

        results = [
            MagicMock(code="W9001", message="Some violation"),
        ]

        modules = svc.extract_w9019_modules(results)

        assert modules == set()
