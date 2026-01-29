"""Unit tests for checker (Pylint plugin registration)."""

from unittest.mock import MagicMock, patch

from clean_architecture_linter.interface.checker import register


class TestCheckerRegister:
    """Test register(linter) entry point."""

    def test_register_prints_banner(self) -> None:
        """register() prints EXCELSIOR banner."""
        linter = MagicMock()
        with patch(
            "clean_architecture_linter.interface.checker.ExcelsiorContainer.get_instance"
        ) as get_instance:
            container = MagicMock()
            container.get.side_effect = lambda name: MagicMock()
            get_instance.return_value = container

            register(linter)

            get_instance.assert_called_once()
            linter.register_checker.assert_called()
            linter.register_reporter.assert_called_once()
