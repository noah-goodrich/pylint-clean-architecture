"""
The 'Sensor' that populates the Knowledge Graph with the current project state.

Uses GraphGatewayProtocol, AstroidProtocol, and FileSystemProtocol so it can run
with any supported adapter. Accepts either domain Violation objects or handover-style
dicts (code, message, locations).
"""
from typing import TYPE_CHECKING, List, Union

if TYPE_CHECKING:
    from excelsior_architect.domain.protocols import (
        AstroidProtocol,
        CanonicalMessageRegistryProtocol,
        FileSystemProtocol,
        GraphGatewayProtocol,
    )
    from excelsior_architect.domain.rules import Violation

# Handover-style violation: dict with code, message, locations (from ai_handover.json)
HandoverViolation = Union[
    "Violation",
    dict,  # {"code": str, "message": str, "locations": list[str]}
]


def _symbol_from_violation(v: "Violation") -> str:
    """Derive graph symbol name from a domain Violation (has astroid node)."""
    if hasattr(v.node, "name") and v.node.name:
        return str(v.node.name)
    return v.location or "unknown"


def _symbol_from_handover(v: dict) -> str:
    """Derive graph symbol name from handover dict (e.g. first location or placeholder)."""
    locations = v.get("locations") or []
    if locations:
        return locations[0]  # "path:line" as identifier
    return "unknown"


def _basename(path_str: str) -> str:
    """Extract file name from path string (protocol-agnostic)."""
    return path_str.replace("\\", "/").split("/")[-1]


class GraphIngestor:
    """Populates the graph with artifacts, symbols, dependencies, and violations."""

    def __init__(
        self,
        graph: "GraphGatewayProtocol",
        ast: "AstroidProtocol",
        filesystem: "FileSystemProtocol",
        canonical_registry: "CanonicalMessageRegistryProtocol | None" = None,
    ) -> None:
        self.graph = graph
        self.ast = ast
        self.filesystem = filesystem
        self._canonical_registry = canonical_registry

    def ingest_project(self, root_dir: str, violations: List[HandoverViolation]) -> None:
        """
        Walks the project under root_dir, parses AST, and maps violations to the graph.
        violations: either list[Violation] (from checker) or list of dicts with
        code, message, locations (from handover).
        """
        for path_str in self.filesystem.glob_python_files(root_dir):
            layer = self._layer_for_path(path_str)
            self.graph.add_artifact(path_str, _basename(path_str), layer)

            tree = self.ast.parse_file(path_str)
            if tree is None:
                continue
            for node in tree.body:
                if hasattr(node, "name"):
                    self.graph.add_symbol(path_str, node.name, type(node).__name__)
                    if hasattr(node, "names"):  # Import nodes
                        for name_node in node.names:
                            self.graph.add_dependency(node.name, name_node[0])

        for v in violations:
            if isinstance(v, dict):
                code = v.get("code", "")
                instance_msg = v.get("message", "")
                symbol_name = _symbol_from_handover(v)
                rule_id = v.get("rule_id")
                if self._canonical_registry and rule_id:
                    message = self._canonical_registry.get_canonical_or_fallback(
                        rule_id, instance_msg
                    )
                else:
                    message = instance_msg
            else:
                # Domain Violation (has .node, .code, .message)
                code = v.code
                message = v.message
                symbol_name = _symbol_from_violation(v)
            self.graph.add_violation(code, symbol_name, message)

    def _layer_for_path(self, file_path: str) -> str:
        """Resolve layer from file path (directory-based heuristic)."""
        from excelsior_architect.domain.layer_registry import LayerRegistry
        registry = LayerRegistry()
        layer = registry.resolve_layer("", file_path, None)
        return layer or "infrastructure"
