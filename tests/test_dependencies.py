# pylint: disable=missing-docstring
import astroid
import pytest
from pylint.testutils import CheckerTestCase, MessageTest

from clean_architecture_linter.checks.dependencies import DependencyChecker
from clean_architecture_linter.layer_registry import LayerRegistry


class TestDependencyChecker(CheckerTestCase):
    CHECKER_CLASS = DependencyChecker

    def test_domain_importing_infrastructure_violation(self):
        """Domain layer should not import Infrastructure layer."""
        # Setup: Current file is a Domain Entity
        node = astroid.extract_node(
            """
        import infrastructure.database as db #@
        """
        )
        node.root().file = "/src/domain/user_entity.py"

        # Configure registry to recognize paths
        # We need to mock the configuration loader or registry behavior
        # But for unit test, the Checker usually uses self.linter.current_name or file path logic
        # We might need to mock config_loader.get_layer_for_module in the checker

        # Mocking the discovery logic:
        # 1. /src/domain/user_entity.py -> Domain
        # 2. infrastructure.database -> Infrastructure

        with self.assertAddsMessages(
            MessageTest(
                msg_id="clean-arch-dependency",
                node=node,
                line=2,
                col_offset=0,
                end_line=2,
                end_col_offset=36,
                args=("Infrastructure", "Domain"),  # imported_layer, current_layer
            )
        ):
            self.checker.visit_import(node)

    def test_usecase_importing_domain_allowed(self):
        """UseCase importing Domain is allowed."""
        node = astroid.extract_node(
            """
        import domain.user_entity as user #@
        """
        )
        node.root().file = "/src/use_cases/register_user.py"

        # No message expected
        with self.assertNoMessages():
            self.checker.visit_import(node)

    def test_infrastructure_importing_domain_allowed(self):
        """Infrastructure importing Domain is allowed."""
        node = astroid.extract_node(
            """
        import domain.user_entity as user #@
        """
        )
        node.root().file = "/src/infrastructure/repositories/user_repo.py"

        with self.assertNoMessages():
            self.checker.visit_import(node)

    def test_domain_importing_standard_lib_allowed(self):
        """Domain importing stdlib is allowed."""
        node = astroid.extract_node(
            """
        import uuid #@
        """
        )
        node.root().file = "/src/domain/user_entity.py"

        with self.assertNoMessages():
            self.checker.visit_import(node)
