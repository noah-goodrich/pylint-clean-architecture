"""Smoke test: 3-level chain into snowflake with stubs -> no W9019; LoD may apply."""

import snowflake.connector


def run_query() -> None:
    """With stubs/snowflake/connector.pyi present, W9019 does not fire."""
    conn = snowflake.connector.connect(account="x", user="y", password="z")
    conn.cursor().execute("SELECT 1")
