"""Unit tests for KuzuGraphGateway."""
import tempfile
from pathlib import Path

from excelsior_architect.infrastructure.gateways.kuzu_gateway import KuzuGraphGateway


def test_kuzu_gateway_init_and_schema():
    """KuzuGraphGateway creates DB and initializes schema."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = str(Path(tmp) / "graph")
        gw = KuzuGraphGateway(db_path=db_path)
        gw.add_artifact("src/foo.py", "foo.py", "domain")
        gw.add_symbol("src/foo.py", "MyClass", "ClassDef")
        gw.add_strategy("R1", "Repository", "Centralize data", ["step1"], ["W9004"])
        gw.add_violation("W9004", "MyClass", "Template")
        strategies = gw.query_recommended_strategies()
        assert isinstance(strategies, list)
        for s in strategies:
            assert "pattern" in s
            assert "rationale" in s
            assert "affected_files" in s
            assert "violations" in s
