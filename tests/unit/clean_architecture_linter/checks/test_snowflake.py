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


if __name__ == "__main__":
    unittest.main()
