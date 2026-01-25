import unittest
from unittest.mock import MagicMock, patch

from clean_architecture_linter.infrastructure.services.scaffolder import Scaffolder


class TestScaffolder(unittest.TestCase):
    def test_init_project_creates_files(self) -> None:
        telemetry = MagicMock()
        scaffolder = Scaffolder(telemetry)

        # We mock Path at the module level of scaffolder
        with patch("clean_architecture_linter.infrastructure.services.scaffolder.Path.exists", return_value=False), \
             patch("clean_architecture_linter.infrastructure.services.scaffolder.Path.mkdir"), \
             patch("clean_architecture_linter.infrastructure.services.scaffolder.Path.open", create=True) as mock_open:

            scaffolder.init_project(template=None, check_layers=False)

            # Verify telemetry steps
            telemetry.step.assert_any_call("Created directory: .agent")
            telemetry.step.assert_any_call("Generated: .agent/instructions.md")
            telemetry.step.assert_any_call("Generated: ARCHITECTURE_ONBOARDING.md")

            # Verify file creation
            assert mock_open.call_count >= 3

    def test_update_makefile_injects_snippet(self) -> None:
        telemetry = MagicMock()
        scaffolder = Scaffolder(telemetry)

        with patch("clean_architecture_linter.infrastructure.services.scaffolder.Path.exists", return_value=True), \
             patch("clean_architecture_linter.infrastructure.services.scaffolder.Path.open") as mock_open:

            mock_file = MagicMock()
            mock_file.read.return_value = "clean:\n\trm -rf"
            mock_open.return_value.__enter__.return_value = mock_file

            scaffolder._update_makefile()

            # Verify telemetry
            telemetry.step.assert_any_call("Injected Stellar Handshake Protocol into Makefile.")
            # Verify write called
            mock_file.write.assert_called()

    def test_check_layers_calls_telemetry(self) -> None:
        telemetry = MagicMock()
        scaffolder = Scaffolder(telemetry)

        with patch("clean_architecture_linter.infrastructure.services.scaffolder.ConfigurationLoader") as mock_conf:
            mock_conf.return_value.config = {"layer_map": {"src": "Domain"}}
            scaffolder._check_layers()
            telemetry.step.assert_any_call("Active Layer Configuration:")
            telemetry.step.assert_any_call("  src -> Domain")

    def test_apply_template_updates_fastapi(self) -> None:
        data = {"tool": {"clean-arch": {}}}
        scaffolder = Scaffolder(MagicMock())
        scaffolder._apply_template_updates(data, "fastapi")
        layer_map = data["tool"]["clean-arch"]["layer_map"]
        assert layer_map["routers"] == "Interface"

if __name__ == "__main__":
    unittest.main()
