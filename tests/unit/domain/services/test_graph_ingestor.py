"""Unit tests for GraphIngestor."""
from unittest.mock import ANY, MagicMock

from excelsior_architect.domain.services.graph_ingestor import GraphIngestor


def test_ingest_project_calls_add_artifact_for_each_python_file():
    """ingest_project uses filesystem.glob_python_files and adds artifacts."""
    graph = MagicMock()
    ast = MagicMock()
    ast.parse_file.return_value = None
    filesystem = MagicMock()
    filesystem.glob_python_files.return_value = ["src/foo/bar.py", "src/baz.py"]

    ingestor = GraphIngestor(graph=graph, ast=ast, filesystem=filesystem)
    ingestor.ingest_project("src", [])

    filesystem.glob_python_files.assert_called_once_with("src")
    assert graph.add_artifact.call_count == 2
    graph.add_artifact.assert_any_call("src/foo/bar.py", "bar.py", ANY)
    graph.add_artifact.assert_any_call("src/baz.py", "baz.py", ANY)


def test_ingest_project_adds_violations_from_handover_dicts():
    """ingest_project maps handover-style dicts to add_violation calls."""
    graph = MagicMock()
    ast = MagicMock()
    filesystem = MagicMock()
    filesystem.glob_python_files.return_value = []

    ingestor = GraphIngestor(graph=graph, ast=ast, filesystem=filesystem)
    violations = [
        {"code": "W9004", "message": "I/O in domain", "locations": ["domain/service.py:10"]},
    ]
    ingestor.ingest_project(".", violations)

    graph.add_violation.assert_called_once_with(
        "W9004",
        "domain/service.py:10",
        "I/O in domain",
    )


def test_ingest_project_uses_canonical_message_when_registry_and_rule_id_present():
    """When canonical_registry and rule_id are present, uses canonical message for graph."""
    graph = MagicMock()
    ast = MagicMock()
    filesystem = MagicMock()
    filesystem.glob_python_files.return_value = []
    registry = MagicMock()
    registry.get_canonical_or_fallback.return_value = "I/O detected in Domain/UseCase layer."

    ingestor = GraphIngestor(
        graph=graph, ast=ast, filesystem=filesystem, canonical_registry=registry
    )
    violations = [
        {
            "code": "W9004",
            "message": "Illegal I/O: open() called at service.py:10",
            "locations": ["domain/service.py:10"],
            "rule_id": "excelsior.W9004",
        },
    ]
    ingestor.ingest_project(".", violations)

    registry.get_canonical_or_fallback.assert_called_once_with(
        "excelsior.W9004", "Illegal I/O: open() called at service.py:10"
    )
    graph.add_violation.assert_called_once_with(
        "W9004",
        "domain/service.py:10",
        "I/O detected in Domain/UseCase layer.",
    )
