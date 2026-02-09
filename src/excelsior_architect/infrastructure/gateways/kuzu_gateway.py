"""
Infrastructure Adapter for the Kùzu Graph Database.
Enhanced to support Dependency nodes for catching library leaks.
"""
import kuzu
import json
from pathlib import Path
from typing import List, Dict, Any, Optional


class KuzuGraphGateway:
    def __init__(self, db_path: str = ".excelsior/graph"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db = kuzu.Database(db_path)
        self.conn = kuzu.Connection(self.db)
        self._init_schema()

    def _init_schema(self):
        # Nodes
        self._create_table(
            "CREATE NODE TABLE Artifact(path STRING, name STRING, PRIMARY KEY (path))")
        self._create_table(
            "CREATE NODE TABLE Symbol(name STRING, type STRING, PRIMARY KEY (name))")
        self._create_table(
            "CREATE NODE TABLE Layer(name STRING, PRIMARY KEY (name))")
        self._create_table(
            "CREATE NODE TABLE Violation(code STRING, message STRING, PRIMARY KEY (code))")
        self._create_table(
            "CREATE NODE TABLE Strategy(id STRING, pattern STRING, rationale STRING, steps STRING, PRIMARY KEY (id))")
        self._create_table(
            "CREATE NODE TABLE Dependency(name STRING, type STRING, PRIMARY KEY (name))")

        # Relationships
        self._create_table(
            "CREATE REL TABLE IMPORTS(FROM Artifact TO Artifact)")
        self._create_table("CREATE REL TABLE OWNS(FROM Artifact TO Symbol)")
        self._create_table("CREATE REL TABLE LIVES_IN(FROM Artifact TO Layer)")
        self._create_table(
            "CREATE REL TABLE AFFECTS(FROM Violation TO Symbol)")
        self._create_table(
            "CREATE REL TABLE MAPS_TO(FROM Violation TO Strategy)")
        self._create_table(
            "CREATE REL TABLE REQUIRES(FROM Symbol TO Dependency)")

    def _create_table(self, query: str):
        try:
            self.conn.execute(query)
        except Exception:
            pass

    def add_dependency(self, symbol_name: str, dep_name: str, dep_type: str = "external"):
        """Link a code symbol to an external library or internal dependency."""
        self.conn.execute(
            f"MERGE (d:Dependency {{name: '{dep_name}', type: '{dep_type}'}})")
        self.conn.execute(
            f"MATCH (s:Symbol {{name: '{symbol_name}'}}), (d:Dependency {{name: '{dep_name}'}}) "
            "MERGE (s)-[:REQUIRES]->(d)"
        )

    def add_artifact(self, path: str, name: str, layer: str):
        self.conn.execute(f"MERGE (l:Layer {{name: '{layer}'}})")
        self.conn.execute(
            f"MERGE (a:Artifact {{path: '{path}', name: '{name}'}})")
        self.conn.execute(
            f"MATCH (a:Artifact {{path: '{path}'}}), (l:Layer {{name: '{layer}'}}) MERGE (a)-[:LIVES_IN]->(l)")

    def add_symbol(self, artifact_path: str, name: str, symbol_type: str):
        self.conn.execute(
            f"MERGE (s:Symbol {{name: '{name}', type: '{symbol_type}'}})")
        self.conn.execute(
            f"MATCH (a:Artifact {{path: '{artifact_path}'}}), (s:Symbol {{name: '{name}'}}) MERGE (a)-[:OWNS]->(s)")

    def add_violation(self, code: str, symbol_name: str, message: str):
        self.conn.execute(
            f"MERGE (v:Violation {{code: '{code}', message: '{message}'}})")
        self.conn.execute(
            f"MATCH (v:Violation {{code: '{code}'}}), (s:Symbol {{name: '{symbol_name}'}}) MERGE (v)-[:AFFECTS]->(s)")

    def add_strategy(self, strat_id: str, pattern: str, rationale: str, steps: List[str], codes: List[str]):
        steps_json = json.dumps(steps)
        self.conn.execute(
            f"MERGE (st:Strategy {{id: '{strat_id}', pattern: '{pattern}', rationale: '{rationale}', steps: '{steps_json}'}})")
        for code in codes:
            self.conn.execute(
                f"MERGE (v:Violation {{code: '{code}', message: 'Template' }})")
            self.conn.execute(
                f"MATCH (v:Violation {{code: '{code}'}}), (st:Strategy {{id: '{strat_id}'}}) MERGE (v)-[:MAPS_TO]->(st)")

    def query_recommended_strategies(self) -> List[Dict[str, Any]]:
        """Identifies pattern-based refactors across the whole project."""
        query = """
        MATCH (st:Strategy)<-[:MAPS_TO]-(v:Violation)-[:AFFECTS]->(s:Symbol)<-[:OWNS]-(a:Artifact)
        RETURN
            st.pattern as pattern,
            st.rationale as rationale,
            collect(DISTINCT a.path) as affected_files,
            collect(DISTINCT v.code) as violations,
            count(DISTINCT v) as score
        ORDER BY score DESC
        """
        result = self.conn.execute(query)
        return [dict(zip(result.get_column_names(), row)) for row in result.fetchall()]

    def query_dependency_leaks(self, forbidden_dep: str, target_layer: str = "domain"):
        """Finds instances where a forbidden library leaked into a specific layer."""
        query = f"""
        MATCH (d:Dependency {{name: '{forbidden_dep}'}})<-[:REQUIRES]-(s:Symbol)<-[:OWNS]-(a:Artifact)-[:LIVES_IN]->(l:Layer {{name: '{target_layer}'}})
        RETURN a.path as file, s.name as symbol, d.name as leaked_lib
        """
        result = self.conn.execute(query)
        return [dict(zip(result.get_column_names(), row)) for row in result.fetchall()]
