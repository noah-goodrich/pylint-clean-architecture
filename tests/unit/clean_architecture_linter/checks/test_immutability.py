import unittest
from clean_architecture_linter.config import ConfigurationLoader
from clean_architecture_linter.checks.immutability import ImmutabilityChecker
from tests.linter_test_utils import run_checker


class TestImmutabilityChecker(unittest.TestCase):

    def setUp(self):
        ConfigurationLoader._instance = None

    def test_domain_entity_mutable(self):
        code = """
from dataclasses import dataclass
@dataclass
class UserEntity:
    pass
        """
        msgs = run_checker(ImmutabilityChecker, code, "src/domain/entities.py")
        self.assertIn("domain-mutability-violation", msgs)

    def test_domain_entity_frozen_ok(self):
        code = """
from dataclasses import dataclass
@dataclass(frozen=True)
class UserEntity:
    pass
        """
        msgs = run_checker(ImmutabilityChecker, code, "src/domain/entities.py")
        self.assertEqual(msgs, [])

    def test_ignore_outside_domain(self):
        code = """
from dataclasses import dataclass
@dataclass
class UserHelper:
    pass
        """
        # Infrastructure layer
        msgs = run_checker(ImmutabilityChecker, code, "src/infrastructure/utils.py")
        self.assertEqual(msgs, [])


if __name__ == "__main__":
    unittest.main()
