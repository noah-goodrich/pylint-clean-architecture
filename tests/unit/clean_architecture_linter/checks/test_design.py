import unittest
from clean_architecture_linter.config import ConfigurationLoader
from clean_architecture_linter.checks.design import DesignChecker
from tests.linter_test_utils import run_checker


class TestDesignChecker(unittest.TestCase):

    def setUp(self):
        ConfigurationLoader._instance = None

    def test_naked_return_violation(self):
        """W9007: Repository returning raw Cursor."""
        code = """
class UserRepository:
    def get_user(self):
        return Cursor()
        """
        msgs = run_checker(DesignChecker, code, "src/infrastructure/repo.py")
        self.assertIn("naked-return-violation", msgs)

    def test_missing_abstraction_violation(self):
        """W9009: UseCase assigning raw Client."""
        code = """
class S3Client: pass
class CreateUserUseCase:
    def execute(self):
        client = S3Client()
        """
        msgs = run_checker(DesignChecker, code, "src/use_cases/user.py")
        self.assertIn("missing-abstraction-violation", msgs)


if __name__ == "__main__":
    unittest.main()
