import unittest
from unittest.mock import MagicMock

from clean_architecture_linter.checks.boundaries import (
    ResourceChecker,
    VisibilityChecker,
)
from clean_architecture_linter.config import ConfigurationLoader
from tests.linter_test_utils import run_checker


class TestResourceChecker(unittest.TestCase):
    def setUp(self):
        ConfigurationLoader._instance = None
        self.loader = ConfigurationLoader()
        from unittest.mock import MagicMock
        self.mock_python_gateway = MagicMock()
        self.mock_python_gateway.get_node_layer.return_value = "Domain"
        self.mock_python_gateway.is_stdlib_module.return_value = False
        self.mock_python_gateway.is_external_dependency.return_value = False

    def test_resource_checker_forbidden_io(self):
        """Test W9004: Forbidden I/O import in Domain."""
        # Assuming snowflake.connector is not in defaults allowed list for ResourceChecker
        code = """
import snowflake.connector
        """
        msgs = run_checker(ResourceChecker, code, "src/domain/logic.py", python_gateway=self.mock_python_gateway)
        self.assertIn("clean-arch-resources", msgs)

    def test_resource_checker_allowed_internal(self):
        """Test allowed internal import in Domain."""
        code = """
import domain.entities
        """
        msgs = run_checker(ResourceChecker, code, "src/domain/logic.py", python_gateway=self.mock_python_gateway)
        self.assertEqual(msgs, [])

    def test_resource_checker_allowed_stdlib(self):
        """Test allowed stdlib import in Domain."""
        code = """
import typing
import datetime
        """
        msgs = run_checker(ResourceChecker, code, "src/domain/logic.py", python_gateway=self.mock_python_gateway)
        self.assertEqual(msgs, [])

    def test_test_file_exemption(self):
        """Verify that files with /tests/ in path don't trigger W9004."""
        code = "import pytest"
        filename = "/abs/path/to/project/packages/my_pkg/tests/unit/use_cases/test_something.py"

        # Mock get_layer_for_module to pretend this test file is in UseCase layer
        original_get_layer = self.loader.get_layer_for_module
        self.loader.get_layer_for_module = MagicMock(return_value="UseCase")

        try:
            msgs = run_checker(ResourceChecker, code, filename, python_gateway=self.mock_python_gateway)
            self.assertEqual(len(msgs), 0, f"Should not have messages for test file. Got: {msgs}")
        finally:
            self.loader.get_layer_for_module = original_get_layer

    def test_path_variants_exemption(self):
        """Verify various path formats trigger exemption."""
        paths = [
            "/abs/path/tests/foo.py",
            "tests/foo.py",
            "package/tests/foo.py",
            "C:\\project\\tests\\foo.py",
        ]
        code = "import os"

        # Force layer to UseCase so it WOULD fail if not exempted
        original_get_layer = self.loader.get_layer_for_module
        self.loader.get_layer_for_module = MagicMock(return_value="UseCase")

        try:
            for p in paths:
                with self.subTest(path=p):
                    msgs = run_checker(ResourceChecker, code, p, python_gateway=self.mock_python_gateway)
                    self.assertEqual(len(msgs), 0, f"Failed exemption for path: {p}")
        finally:
            self.loader.get_layer_for_module = original_get_layer


class TestVisibilityChecker(unittest.TestCase):
    def setUp(self):
        ConfigurationLoader._instance = None

    def test_visibility_checker_public(self):
        code = "class A: \n def call(self, other): return other.public"
        msgs = run_checker(VisibilityChecker, code)
        self.assertEqual(msgs, [])

    def test_visibility_checker_protected(self):
        code = "class A: \n def call(self, other): return other._secret"
        with unittest.mock.patch(
            "clean_architecture_linter.config.ConfigurationLoader.visibility_enforcement",
            new_callable=unittest.mock.PropertyMock,
        ) as mock_vis:
            mock_vis.return_value = True
            msgs = run_checker(VisibilityChecker, code)
            self.assertIn("clean-arch-visibility", msgs)

    def test_visibility_checker_self_access_ok(self):
        code = "class A: \n def call(self): return self._secret"
        with unittest.mock.patch(
            "clean_architecture_linter.config.ConfigurationLoader.visibility_enforcement",
            new_callable=unittest.mock.PropertyMock,
        ) as mock_vis:
            mock_vis.return_value = True
            msgs = run_checker(VisibilityChecker, code)
            self.assertEqual(msgs, [])


if __name__ == "__main__":
    unittest.main()
