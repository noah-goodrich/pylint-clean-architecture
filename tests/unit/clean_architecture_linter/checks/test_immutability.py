import unittest

from clean_architecture_linter.checks.immutability import ImmutabilityChecker
from clean_architecture_linter.config import ConfigurationLoader
from tests.linter_test_utils import run_checker


class TestImmutabilityChecker(unittest.TestCase):
    def setUp(self):
        ConfigurationLoader._instance = None
        from unittest.mock import MagicMock
        self.mock_py_gateway = MagicMock()
        # Mock get_node_layer to return None or specific layer if needed by tests
        # For immutable entity tests, it likely relies on registry or config, but the checker calls gateway.
        self.mock_py_gateway.get_node_layer.return_value = "Domain"

    def test_domain_entity_mutable(self):
        code = """
from dataclasses import dataclass
@dataclass
class UserEntity:
    pass
        """
        msgs = run_checker(ImmutabilityChecker, code, "src/domain/entities.py", python_gateway=self.mock_py_gateway)
        self.assertIn("domain-immutability-violation", msgs)

    def test_domain_entity_frozen_ok(self):
        code = """
from dataclasses import dataclass
@dataclass(frozen=True)
class UserEntity:
    pass
        """
        msgs = run_checker(ImmutabilityChecker, code, "src/domain/entities.py", python_gateway=self.mock_py_gateway)
        self.assertEqual(msgs, [])

    def test_ignore_outside_domain(self):
        code = """
from dataclasses import dataclass
@dataclass
class UserHelper:
    pass
        """
        # Infrastructure layer
        self.mock_py_gateway.get_node_layer.return_value = "Infrastructure"
        msgs = run_checker(ImmutabilityChecker, code, "src/infrastructure/utils.py", python_gateway=self.mock_py_gateway)
        self.assertEqual(msgs, [])


if __name__ == "__main__":
    unittest.main()
