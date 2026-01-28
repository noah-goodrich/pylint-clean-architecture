"""Smoke test: 3-level chain into snowflake with no stubs -> W9019."""

import snowflake.connector


def run_query() -> None:
    """connect().cursor().execute() without stubs/snowflake/connector.pyi -> W9019."""
    conn = snowflake.connector.connect(account="x", user="y", password="z")
    conn.cursor().execute("SELECT 1")
