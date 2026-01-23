import unittest

from clean_architecture_linter.checks.design import DesignChecker
from clean_architecture_linter.config import ConfigurationLoader
from tests.linter_test_utils import run_checker
import astroid


class TestDesignChecker(unittest.TestCase):
    def setUp(self):
        ConfigurationLoader._instance = None
        from unittest.mock import MagicMock
        self.mock_ast_gateway = MagicMock()
        # Default fallback
        def get_qname(node):
            if isinstance(node, astroid.nodes.Call):
                if isinstance(node.func, astroid.nodes.Name):
                    return node.func.name
                if isinstance(node.func, astroid.nodes.Attribute):
                    return node.func.attrname
                # Test specific for naked_return failure: 'Cursor()' call
                # Check directly if node looks like Cursor call
                if node.func.name == "Cursor":
                     return "Cursor"
            return getattr(node, "name", "Unknown")
        self.mock_ast_gateway.get_node_return_type_qname.side_effect = get_qname

    def test_naked_return_violation(self):
        """W9007: Repository returning raw Cursor."""
        code = """
class UserRepository:
    def get_user(self):
        return Cursor()
        """
        msgs = run_checker(DesignChecker, code, "src/infrastructure/repo.py", ast_gateway=self.mock_ast_gateway)
        self.assertIn("naked-return-violation", msgs)

    def test_missing_abstraction_violation(self):
        """W9009: UseCase assigning raw Client."""
        code = """
class S3Client: pass
class CreateUserUseCase:
    def execute(self):
        client = S3Client()
        """
        msgs = run_checker(DesignChecker, code, "src/use_cases/user.py", ast_gateway=self.mock_ast_gateway)
        self.assertIn("missing-abstraction-violation", msgs)

    def test_defensive_none_check_violation(self):
        """W9012: Defensive None check in UseCase."""
        code = """
class CreateUserUseCase:
    def execute(self, user_id):
        if user_id is None:
            raise ValueError("user_id is required")
        return user_id
        """
        msgs = run_checker(DesignChecker, code, "src/use_cases/user.py", ast_gateway=self.mock_ast_gateway)
        self.assertIn("defensive-none-check", msgs)

    def test_none_check_in_infrastructure_allowed(self):
        """W9012: Defensive None check is allowed in Infrastructure/CLI."""
        code = """
def cli_command(user_id):
    if user_id is None:
        raise ValueError("Missing ID")
        """
        msgs = run_checker(DesignChecker, code, "src/interface/cli.py", ast_gateway=self.mock_ast_gateway)
        self.assertNotIn("defensive-none-check", msgs)


if __name__ == "__main__":
    unittest.main()
