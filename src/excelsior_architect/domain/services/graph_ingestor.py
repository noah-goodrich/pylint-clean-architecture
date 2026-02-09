"""
The 'Sensor' that populates the Knowledge Graph with the current project state.
"""
from typing import List
from excelsior_architect.infrastructure.gateways.kuzu_gateway import KuzuGraphGateway
from excelsior_architect.infrastructure.gateways.astroid_gateway import AstroidGateway
from excelsior_architect.domain.entities import Violation


class GraphIngestor:
    def __init__(self, graph: KuzuGraphGateway, ast: AstroidGateway):
        self.graph = graph
        self.ast = ast

    def ingest_project(self, root_dir: str, violations: List[Violation]):
        """
        Walks the filesystem, parses structure, and maps violations to symbols.
        """
        # 1. Map files to layers (Simple heuristic for POC)
        for py_file in Path(root_dir).rglob("*.py"):
            layer = "domain" if "domain" in str(py_file) else "infrastructure"
            if "use_cases" in str(py_file):
                layer = "use_cases"

            self.graph.add_artifact(str(py_file), py_file.name, layer)

            # 2. Extract Symbols and External Dependencies
            tree = self.ast.parse_file(str(py_file))
            for node in tree.body:
                if hasattr(node, 'name'):
                    self.graph.add_symbol(
                        str(py_file), node.name, type(node).__name__)

                    # Detect external library dependencies
                    if hasattr(node, 'names'):  # Import nodes
                        for name_node in node.names:
                            self.graph.add_dependency(node.name, name_node[0])

        # 3. Map Violations to the Graph
        for v in violations:
            # We assume 'v.node_name' is populated by the checker
            self.graph.add_violation(v.code, v.node_name, v.message)
