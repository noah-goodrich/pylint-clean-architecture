"""
Infrastructure Adapter for the Kùzu Graph Database.
Enhanced to support Dependency nodes for catching library leaks.
"""
import json
import re
from pathlib import Path
from typing import List

import kuzu

# Strip ANSI escape sequences (e.g. from Pylint/Excelsior messages)
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

from excelsior_architect.domain.sae_entities import RecommendedStrategy


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
        """Add violation and AFFECTS edge. MERGE on code (PK) only to avoid duplicate key when same code appears with different messages.
        Uses parameterized queries to avoid injection and special-character issues (ANSI, quotes)."""
        msg_clean = _ANSI_RE.sub("", (message or ""))
        self.conn.execute(
            "MERGE (v:Violation {code: $code}) "
            "ON CREATE SET v.message = $msg ON MATCH SET v.message = $msg",
            parameters={"code": code, "msg": msg_clean},
        )
        self.conn.execute(
            "MATCH (v:Violation {code: $code}), (s:Symbol {name: $sym}) MERGE (v)-[:AFFECTS]->(s)",
            parameters={"code": code, "sym": symbol_name or ""},
        )

    def ensure_violation(self, code: str, message: str) -> None:
        """Ensure a violation node exists (e.g. from master registry).
        MERGE on primary key (code) only; ON CREATE/MATCH SET message to avoid duplicate PK.
        """
        msg_esc = (message or "").replace("'", "''")
        self.conn.execute(
            f"MERGE (v:Violation {{code: '{code}'}}) "
            f"ON CREATE SET v.message = '{msg_esc}' ON MATCH SET v.message = '{msg_esc}'")

    def add_strategy(self, strat_id: str, pattern: str, rationale: str, steps: List[str], codes: List[str]):
        """Link strategies to violations. Violations must exist (from ensure_violation); MERGE on code only."""
        steps_json = json.dumps(steps).replace("'", "''")
        pattern_esc = pattern.replace("'", "''")
        rationale_esc = rationale.replace("'", "''")
        self.conn.execute(
            f"MERGE (st:Strategy {{id: '{strat_id}', pattern: '{pattern_esc}', rationale: '{rationale_esc}', steps: '{steps_json}'}})")
        for code in codes:
            # MERGE on code (PK) only; ON CREATE for codes in patterns but not in violation registries
            self.conn.execute(
                f"MERGE (v:Violation {{code: '{code}'}}) ON CREATE SET v.message = 'Template'")
            self.conn.execute(
                f"MATCH (v:Violation {{code: '{code}'}}), (st:Strategy {{id: '{strat_id}'}}) MERGE (v)-[:MAPS_TO]->(st)")

    def query_recommended_strategies(self) -> List[RecommendedStrategy]:
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
        column_names = result.get_column_names()
        strategies: List[RecommendedStrategy] = []
        for row in result.get_all():
            row_dict = dict(zip(column_names, row))
            af = row_dict.get("affected_files")
            violations = row_dict.get("violations")
            strategies.append(
                {
                    "pattern": str(row_dict.get("pattern", "")),
                    "rationale": str(row_dict.get("rationale", "")),
                    "affected_files": list(af) if af is not None else [],
                    "violations": list(violations) if violations is not None else [],
                    "score": int(row_dict.get("score", 0)),
                }
            )
        return strategies

    def query_dependency_leaks(self, forbidden_dep: str, target_layer: str = "domain"):
        """Finds instances where a forbidden library leaked into a specific layer."""
        query = f"""
        MATCH (d:Dependency {{name: '{forbidden_dep}'}})<-[:REQUIRES]-(s:Symbol)<-[:OWNS]-(a:Artifact)-[:LIVES_IN]->(l:Layer {{name: '{target_layer}'}})
        RETURN a.path as file, s.name as symbol, d.name as leaked_lib
        """
        result = self.conn.execute(query)
        return [dict(zip(result.get_column_names(), row)) for row in result.get_all()]
