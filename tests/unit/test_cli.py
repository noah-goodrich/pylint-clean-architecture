import argparse
from unittest.mock import MagicMock, patch
from pathlib import Path
from clean_architecture_linter.cli import init_command, _update_makefile

def test_init_command_creates_files():
    telemetry = MagicMock()

    with patch("clean_architecture_linter.cli.Path.exists", return_value=False), \
         patch("clean_architecture_linter.cli.Path.mkdir"), \
         patch("clean_architecture_linter.cli.Path.open", create=True) as mock_open, \
         patch("clean_architecture_linter.cli.argparse.ArgumentParser.parse_args") as mock_args:

        mock_args.return_value = argparse.Namespace(template=None, check_layers=False)

        init_command(telemetry)

        # Verify telemetry steps
        telemetry.step.assert_any_call("Created directory: .agent")
        telemetry.step.assert_any_call("Generated: .agent/instructions.md")
        telemetry.step.assert_any_call("Generated: ARCHITECTURE_ONBOARDING.md")

        # Verify file creation
        assert mock_open.call_count >= 3

def test_update_makefile_injects_snippet():
    telemetry = MagicMock()

    with patch("clean_architecture_linter.cli.Path.exists", return_value=True), \
         patch("clean_architecture_linter.cli.Path.open") as mock_open:

        mock_file = MagicMock()
        mock_file.read.return_value = "clean:\n\trm -rf"
        mock_open.return_value.__enter__.return_value = mock_file

        _update_makefile(telemetry)

        # Verify telemetry
        telemetry.step.assert_any_call("Injected Stellar Handshake Protocol into Makefile.")
        # Verify write called
        mock_file.write.assert_called()

def test_check_layers_calls_telemetry():
    telemetry = MagicMock()
    with patch("clean_architecture_linter.cli.ConfigurationLoader") as mock_conf:
        mock_conf.return_value.config = {"layer_map": {"src": "Domain"}}
        from clean_architecture_linter.cli import _check_layers
        _check_layers(telemetry)
        telemetry.step.assert_any_call("Active Layer Configuration:")
        telemetry.step.assert_any_call("  src -> Domain")

def test_apply_template_updates_fastapi():
    data = {"tool": {"clean-arch": {}}}
    from clean_architecture_linter.cli import _apply_template_updates
    _apply_template_updates(data, "fastapi")
    layer_map = data["tool"]["clean-arch"]["layer_map"]
    assert layer_map["routers"] == "Interface"

def test_generate_instructions_creates_file():
    telemetry = MagicMock()
    path = MagicMock(spec=Path)
    with patch("clean_architecture_linter.cli.ConfigurationLoader") as mock_conf:
        mock_conf.return_value.config = {"layer_map": {"src": "Domain"}}
        from clean_architecture_linter.cli import _generate_instructions
        _generate_instructions(telemetry, path)
        path.open.assert_called_once_with("w", encoding="utf-8")

def test_main():
    with patch("clean_architecture_linter.cli.ExcelsiorContainer") as mock_cont, \
         patch("clean_architecture_linter.cli.init_command") as mock_init, \
         patch("sys.argv", ["excelsior", "init"]):

        telemetry = MagicMock()
        mock_cont.return_value.get.return_value = telemetry

        from clean_architecture_linter.cli import main
        main()

        telemetry.handshake.assert_called_once()
        mock_init.assert_called_once_with(telemetry)
