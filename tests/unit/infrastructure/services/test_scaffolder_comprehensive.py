"""Comprehensive unit tests for Scaffolder covering all high-impact methods.

These tests focus on methods identified as high-priority in TEST_PRIORITIES.md:
- File creation (_generate_instructions, init_project)
- pyproject.toml modification (_load_pyproject, _load_pyproject_toml, _perform_tool_audit)
- Makefile injection (_update_makefile)
- Template application (_apply_template_updates)
- Ruff configuration wizard (_configure_ruff_wizard, _write_ruff_config, etc.)
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from clean_architecture_linter.infrastructure.services.scaffolder import Scaffolder


class TestFileCreation:
    """Test file creation methods."""

    def test_generate_instructions_creates_file(self, tmp_path, monkeypatch) -> None:
        """Test _generate_instructions creates instructions.md file."""
        instructions_file = tmp_path / "instructions.md"
        telemetry = MagicMock()
        scaffolder = Scaffolder(telemetry)

        with patch('clean_architecture_linter.infrastructure.services.scaffolder.ConfigurationLoader') as mock_config:
            mock_config.return_value.config = {
                "layer_map": {
                    "domain": "Domain",
                    "use_cases": "UseCase"
                }
            }
            scaffolder._generate_instructions(instructions_file)

        assert instructions_file.exists()
        content = instructions_file.read_text()
        assert "Domain" in content
        assert "UseCase" in content
        telemetry.step.assert_called()

    def test_init_project_creates_agent_directory(self, tmp_path, monkeypatch) -> None:
        """Test init_project creates .agent directory."""
        monkeypatch.chdir(tmp_path)
        telemetry = MagicMock()
        scaffolder = Scaffolder(telemetry)

        with patch('pathlib.Path.exists', return_value=False), \
             patch('pathlib.Path.mkdir'), \
             patch('pathlib.Path.open', mock_open()), \
             patch.object(scaffolder, '_perform_tool_audit'), \
             patch.object(scaffolder, '_configure_ruff_wizard'):
            scaffolder.init_project(template=None, check_layers=False)

        telemetry.step.assert_any_call("Created directory: .agent")

    def test_init_project_creates_pre_flight_file(self, tmp_path, monkeypatch) -> None:
        """Test init_project creates pre-flight.md file."""
        monkeypatch.chdir(tmp_path)
        telemetry = MagicMock()
        scaffolder = Scaffolder(telemetry)

        with patch('pathlib.Path.exists', return_value=False), \
             patch('pathlib.Path.mkdir'), \
             patch('pathlib.Path.open', mock_open()), \
             patch.object(scaffolder, '_perform_tool_audit'), \
             patch.object(scaffolder, '_configure_ruff_wizard'):
            scaffolder.init_project(template=None, check_layers=False)

        telemetry.step.assert_any_call("Generated: .agent/pre-flight.md")

    def test_init_project_creates_onboarding_file(self, tmp_path, monkeypatch) -> None:
        """Test init_project creates ARCHITECTURE_ONBOARDING.md file."""
        monkeypatch.chdir(tmp_path)
        telemetry = MagicMock()
        scaffolder = Scaffolder(telemetry)

        with patch('pathlib.Path.exists', return_value=False), \
             patch('pathlib.Path.mkdir'), \
             patch('pathlib.Path.open', mock_open()), \
             patch.object(scaffolder, '_perform_tool_audit'), \
             patch.object(scaffolder, '_configure_ruff_wizard'):
            scaffolder.init_project(template=None, check_layers=False)

        telemetry.step.assert_any_call("Generated: ARCHITECTURE_ONBOARDING.md")


class TestPyprojectModification:
    """Test pyproject.toml loading and modification methods."""

    def test_load_pyproject_loads_valid_toml(self, tmp_path) -> None:
        """Test _load_pyproject loads valid TOML file."""
        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text('[project]\nname = "test"\n')

        telemetry = MagicMock()
        scaffolder = Scaffolder(telemetry)

        result = scaffolder._load_pyproject(pyproject_file)

        assert result is not None
        assert result["project"]["name"] == "test"

    def test_load_pyproject_returns_none_on_error(self, tmp_path) -> None:
        """Test _load_pyproject returns None on parse error."""
        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text('invalid toml !!!\n')

        telemetry = MagicMock()
        scaffolder = Scaffolder(telemetry)

        result = scaffolder._load_pyproject(pyproject_file)

        assert result is None

    def test_load_pyproject_toml_returns_none_when_missing(self, tmp_path, monkeypatch) -> None:
        """Test _load_pyproject_toml returns None when file doesn't exist."""
        monkeypatch.chdir(tmp_path)
        telemetry = MagicMock()
        scaffolder = Scaffolder(telemetry)

        result = scaffolder._load_pyproject_toml()

        assert result is None

    def test_load_pyproject_toml_loads_existing_file(self, tmp_path, monkeypatch) -> None:
        """Test _load_pyproject_toml loads existing pyproject.toml."""
        monkeypatch.chdir(tmp_path)
        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text('[project]\nname = "test"\n')

        telemetry = MagicMock()
        scaffolder = Scaffolder(telemetry)

        result = scaffolder._load_pyproject_toml()

        assert result is not None
        assert result["project"]["name"] == "test"

    def test_perform_tool_audit_detects_ruff(self, tmp_path, monkeypatch) -> None:
        """Test _perform_tool_audit detects Ruff in pyproject.toml."""
        monkeypatch.chdir(tmp_path)
        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text('[tool.ruff]\nline-length = 120\n')

        telemetry = MagicMock()
        scaffolder = Scaffolder(telemetry)

        with patch('builtins.print'):
            scaffolder._perform_tool_audit(template=None)

        telemetry.step.assert_called()
        assert any("ruff" in str(call) for call in telemetry.step.call_args_list)

    def test_perform_tool_audit_applies_template(self, tmp_path, monkeypatch) -> None:
        """Test _perform_tool_audit applies template updates."""
        monkeypatch.chdir(tmp_path)
        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text('[tool.clean-arch]\n')

        telemetry = MagicMock()
        scaffolder = Scaffolder(telemetry)

        with patch('builtins.print'), \
             patch.object(scaffolder, '_apply_template_updates') as mock_apply:
            scaffolder._perform_tool_audit(template="fastapi")

        mock_apply.assert_called_once()
        telemetry.step.assert_any_call("Applied template updates for: fastapi")


class TestMakefileInjection:
    """Test Makefile update methods."""

    def test_update_makefile_injects_snippet_when_missing(self, tmp_path, monkeypatch) -> None:
        """Test _update_makefile injects handshake snippet when missing."""
        monkeypatch.chdir(tmp_path)
        makefile = tmp_path / "Makefile"
        makefile.write_text("clean:\n\trm -rf build\n")

        telemetry = MagicMock()
        scaffolder = Scaffolder(telemetry)

        scaffolder._update_makefile()

        content = makefile.read_text()
        assert "handshake:" in content
        telemetry.step.assert_called_with("Injected Stellar Handshake Protocol into Makefile.")

    def test_update_makefile_skips_when_already_present(self, tmp_path, monkeypatch) -> None:
        """Test _update_makefile skips injection when handshake already exists."""
        monkeypatch.chdir(tmp_path)
        makefile = tmp_path / "Makefile"
        makefile.write_text("handshake:\n\techo 'already here'\n")

        telemetry = MagicMock()
        scaffolder = Scaffolder(telemetry)

        scaffolder._update_makefile()

        telemetry.step.assert_called_with("Makefile already contains handshake protocol.")
        # Should not inject again
        content = makefile.read_text()
        assert content.count("handshake:") == 1

    def test_update_makefile_creates_file_if_missing(self, tmp_path, monkeypatch) -> None:
        """Test _update_makefile creates Makefile if it doesn't exist."""
        monkeypatch.chdir(tmp_path)
        telemetry = MagicMock()
        scaffolder = Scaffolder(telemetry)

        scaffolder._update_makefile()

        makefile = tmp_path / "Makefile"
        assert makefile.exists()
        assert "handshake:" in makefile.read_text()


class TestTemplateApplication:
    """Test template update methods."""

    def test_apply_template_updates_fastapi(self) -> None:
        """Test _apply_template_updates applies FastAPI template."""
        telemetry = MagicMock()
        scaffolder = Scaffolder(telemetry)

        data = {"tool": {"clean-arch": {}}}
        scaffolder._apply_template_updates(data, "fastapi")

        layer_map = data["tool"]["clean-arch"]["layer_map"]
        assert layer_map["routers"] == "Interface"
        assert layer_map["services"] == "UseCase"
        assert layer_map["schemas"] == "Interface"

    def test_apply_template_updates_sqlalchemy(self) -> None:
        """Test _apply_template_updates applies SQLAlchemy template."""
        telemetry = MagicMock()
        scaffolder = Scaffolder(telemetry)

        data = {"tool": {"clean-arch": {}}}
        scaffolder._apply_template_updates(data, "sqlalchemy")

        layer_map = data["tool"]["clean-arch"]["layer_map"]
        assert layer_map["models"] == "Infrastructure"
        assert layer_map["repositories"] == "Infrastructure"
        
        base_class_map = data["tool"]["clean-arch"]["base_class_map"]
        assert base_class_map["Base"] == "Infrastructure"
        assert base_class_map["DeclarativeBase"] == "Infrastructure"

    def test_apply_template_updates_handles_missing_tool_section(self) -> None:
        """Test _apply_template_updates handles missing tool section."""
        telemetry = MagicMock()
        scaffolder = Scaffolder(telemetry)

        data = {}
        scaffolder._apply_template_updates(data, "fastapi")

        # Should not raise, but also not modify
        assert "tool" not in data or "clean-arch" not in data.get("tool", {})

    def test_apply_template_updates_handles_invalid_template(self) -> None:
        """Test _apply_template_updates handles unknown template."""
        telemetry = MagicMock()
        scaffolder = Scaffolder(telemetry)

        data = {"tool": {"clean-arch": {}}}
        original_data = json.dumps(data, sort_keys=True)
        
        scaffolder._apply_template_updates(data, "unknown_template")

        # Should not modify data
        assert json.dumps(data, sort_keys=True) == original_data


class TestRuffWizard:
    """Test Ruff configuration wizard methods."""

    def test_ruff_wizard_can_use_toml_returns_true_python311(self) -> None:
        """Test _ruff_wizard_can_use_toml returns True on Python 3.11+."""
        telemetry = MagicMock()
        scaffolder = Scaffolder(telemetry)

        with patch('sys.version_info', (3, 11, 0)):
            result = scaffolder._ruff_wizard_can_use_toml()

        assert result is True

    def test_ruff_wizard_can_use_toml_checks_tomli_availability(self) -> None:
        """Test _ruff_wizard_can_use_toml checks tomli availability on older Python."""
        telemetry = MagicMock()
        scaffolder = Scaffolder(telemetry)

        with patch('sys.version_info', (3, 10, 0)), \
             patch('importlib.util.find_spec', return_value=None):
            result = scaffolder._ruff_wizard_can_use_toml()

        assert result is False
        scaffolder.telemetry.step.assert_called()

    def test_ruff_wizard_has_existing_config_detects_ruff(self, tmp_path, monkeypatch) -> None:
        """Test _ruff_wizard_has_existing_config detects existing Ruff config."""
        monkeypatch.chdir(tmp_path)
        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text('[tool.ruff]\nline-length = 100\n')

        telemetry = MagicMock()
        scaffolder = Scaffolder(telemetry)

        result = scaffolder._ruff_wizard_has_existing_config()

        assert result is True

    def test_ruff_wizard_has_existing_config_detects_excelsior_ruff(self, tmp_path, monkeypatch) -> None:
        """Test _ruff_wizard_has_existing_config detects excelsior.ruff config."""
        monkeypatch.chdir(tmp_path)
        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text('[tool.excelsior.ruff]\nline-length = 100\n')

        telemetry = MagicMock()
        scaffolder = Scaffolder(telemetry)

        result = scaffolder._ruff_wizard_has_existing_config()

        assert result is True

    def test_ruff_wizard_prompt_overwrite_returns_false_on_no(self) -> None:
        """Test _ruff_wizard_prompt_overwrite returns False when user says no."""
        telemetry = MagicMock()
        scaffolder = Scaffolder(telemetry)

        with patch('builtins.input', return_value='n'), \
             patch('builtins.print'):
            result = scaffolder._ruff_wizard_prompt_overwrite()

        assert result is False

    def test_ruff_wizard_prompt_overwrite_returns_true_on_yes(self) -> None:
        """Test _ruff_wizard_prompt_overwrite returns True when user says yes."""
        telemetry = MagicMock()
        scaffolder = Scaffolder(telemetry)

        with patch('builtins.input', return_value='y'):
            result = scaffolder._ruff_wizard_prompt_overwrite()

        assert result is True

    def test_write_ruff_config_writes_to_pyproject(self, tmp_path, monkeypatch) -> None:
        """Test _write_ruff_config writes Ruff config to pyproject.toml."""
        monkeypatch.chdir(tmp_path)
        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text('[project]\nname = "test"\n')

        telemetry = MagicMock()
        scaffolder = Scaffolder(telemetry)

        mock_tomli_w = MagicMock()
        mock_tomli_w.dump = MagicMock()
        
        # Inject mock into sys.modules before the import happens
        import sys
        original_tomli_w = sys.modules.get('tomli_w')
        sys.modules['tomli_w'] = mock_tomli_w
        try:
            scaffolder._write_ruff_config(120, 10, ["E", "F"])
        finally:
            if original_tomli_w is not None:
                sys.modules['tomli_w'] = original_tomli_w
            elif 'tomli_w' in sys.modules:
                del sys.modules['tomli_w']

        mock_tomli_w.dump.assert_called_once()
        # Check that config structure is correct
        call_args = mock_tomli_w.dump.call_args[0]
        data = call_args[0]
        assert data["tool"]["excelsior"]["ruff"]["line-length"] == 120
        assert data["tool"]["excelsior"]["ruff"]["lint"]["mccabe"]["max-complexity"] == 10

    def test_write_ruff_config_falls_back_to_text_append(self, tmp_path, monkeypatch) -> None:
        """Test _write_ruff_config falls back to text append when tomli_w unavailable."""
        monkeypatch.chdir(tmp_path)
        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text('[project]\nname = "test"\n')

        telemetry = MagicMock()
        scaffolder = Scaffolder(telemetry)

        # Remove tomli_w from sys.modules to force ImportError
        import sys
        original_tomli_w = sys.modules.pop('tomli_w', None)
        try:
            with patch('builtins.print'):
                scaffolder._write_ruff_config(120, 10, ["E", "F"])
        finally:
            if original_tomli_w is not None:
                sys.modules['tomli_w'] = original_tomli_w

        # Should append text
        content = pyproject_file.read_text()
        assert "[tool.excelsior.ruff]" in content
        assert "line-length = 120" in content

    def test_configure_ruff_wizard_skips_in_non_interactive(self, tmp_path, monkeypatch) -> None:
        """Test _configure_ruff_wizard skips in non-interactive mode."""
        monkeypatch.chdir(tmp_path)
        telemetry = MagicMock()
        scaffolder = Scaffolder(telemetry)

        with patch('sys.stdin.isatty', return_value=False):
            scaffolder._configure_ruff_wizard()

        # Should not prompt or write
        assert not (tmp_path / "pyproject.toml").exists()

    def test_check_layers_displays_layer_map(self, tmp_path, monkeypatch) -> None:
        """Test _check_layers displays active layer configuration."""
        monkeypatch.chdir(tmp_path)
        telemetry = MagicMock()
        scaffolder = Scaffolder(telemetry)

        with patch('clean_architecture_linter.infrastructure.services.scaffolder.ConfigurationLoader') as mock_config:
            mock_config.return_value.config = {
                "layer_map": {
                    "domain": "Domain",
                    "use_cases": "UseCase"
                }
            }
            scaffolder._check_layers()

        telemetry.step.assert_any_call("Active Layer Configuration:")
        telemetry.step.assert_any_call("  domain -> Domain")
        telemetry.step.assert_any_call("  use_cases -> UseCase")

    def test_check_layers_handles_missing_layer_map(self, tmp_path, monkeypatch) -> None:
        """Test _check_layers handles missing layer_map."""
        monkeypatch.chdir(tmp_path)
        telemetry = MagicMock()
        scaffolder = Scaffolder(telemetry)

        with patch('clean_architecture_linter.infrastructure.services.scaffolder.ConfigurationLoader') as mock_config:
            mock_config.return_value.config = {}
            scaffolder._check_layers()

        telemetry.error.assert_called()
