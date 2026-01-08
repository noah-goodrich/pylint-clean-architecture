import unittest
from clean_architecture_linter.checks.snowflake import SnowflakeGovernanceChecker
from tests.linter_test_utils import run_checker


class TestSnowflakeGovernanceChecker(unittest.TestCase):

    def test_select_star_violation(self):
        code = """
import snowflake.snowpark
def query(session):
    session.sql("SELECT * FROM table")
        """
        msgs = run_checker(SnowflakeGovernanceChecker, code, "infrastructure/db.py")
        self.assertIn("select-star-violation", msgs)

    def test_gold_view_violation(self):
        code = """
import snowflake.snowpark
def create_model(session):
    session.create_view("CREATE VIEW RAW_GOLD.MY_VIEW AS SELECT 1") # Logic checks if _GOLD is in args
        """
        msgs = run_checker(
            SnowflakeGovernanceChecker, code, "infrastructure/pipelines.py"
        )
        self.assertIn("gold-layer-view-violation", msgs)

    def test_gold_evolution_violation(self):
        code = """
import snowflake.connector
from snowflake.connector.pandas_tools import write_pandas
def save(df):
    write_pandas(df, "MY_GOLD_TABLE", auto_create_table=True)
        """
        msgs = run_checker(
            SnowflakeGovernanceChecker, code, "infrastructure/pipelines.py"
        )
        self.assertIn("gold-schema-evolution-violation", msgs)

    def test_no_violations(self):
        code = """
import snowflake.snowpark
def query(session):
    session.sql("SELECT id, name FROM table")
    write_pandas(df, "MY_SILVER_TABLE", auto_create_table=True)
        """
        msgs = run_checker(SnowflakeGovernanceChecker, code, "infrastructure/db.py")
        self.assertEqual(msgs, [])

    def test_custom_governance_prefix_violation(self):
        """Test violation in a custom configured module prefix."""
        code = """
import my_project.infra.snowflake
def query(session):
    session.sql("SELECT * FROM table")
        """
        # We need to manually set up the checker to inject config
        from tests.linter_test_utils import MockLinter
        import astroid

        linter = MockLinter()
        # Inject custom config
        linter.config_loader.config = {
            "governance_module_prefixes": ["my_project.infra.snowflake"]
        }

        checker = SnowflakeGovernanceChecker(linter)
        tree = astroid.parse(code)

        # Manually invoke visit_module to set state
        checker.visit_module(tree)
        # Mock visit_call logic manually or rely on walker if I implemented it there?
        # SnowflakeGovernanceChecker needs state set by visit_module.

        # Let's inspect call nodes
        for node in tree.nodes_of_class(astroid.nodes.Call):
            checker.visit_call(node)

        self.assertIn("select-star-violation", linter.messages)


if __name__ == "__main__":
    unittest.main()
