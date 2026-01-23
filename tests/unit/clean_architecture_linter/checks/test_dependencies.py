import unittest

from clean_architecture_linter.checks.dependencies import DependencyChecker
from clean_architecture_linter.config import ConfigurationLoader
from tests.linter_test_utils import run_checker


class TestDependencyChecker(unittest.TestCase):
    def setUp(self):
        ConfigurationLoader._instance = None
        from unittest.mock import MagicMock
        self.mock_python_gateway = MagicMock()
        # Default to Domain layer for consistency if not overridden
        self.mock_python_gateway.get_node_layer.return_value = "Domain"

    def test_dependency_checker_forbidden_import(self):
        """Test W9010: Forbidden cross-layer import."""
        code = """
import infrastructure.db
        """
        # Domain importing Infrastructure
        msgs = run_checker(DependencyChecker, code, "src/domain/entities.py", python_gateway=self.mock_python_gateway)
        self.assertIn("clean-arch-dependency", msgs)

    def test_dependency_checker_allowed_import(self):
        """Test allowed import (same layer or lower)."""
        code = """
import domain.models
        """
        # Domain importing Domain
        msgs = run_checker(DependencyChecker, code, "src/domain/entities.py", python_gateway=self.mock_python_gateway)
        self.assertEqual(msgs, [])


if __name__ == "__main__":
    unittest.main()
