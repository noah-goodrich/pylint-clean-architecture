"""Unit tests for GenerateBlueprintUseCase."""
import json
from pathlib import Path
from unittest.mock import MagicMock

from excelsior_architect.infrastructure.services.code_snippet_extractor import CodeSnippet
from excelsior_architect.use_cases.generate_blueprint import GenerateBlueprintUseCase


def test_execute_writes_blueprint_with_current_state_snippets_when_extractor_provides_them():
    """When snippet_extractor is provided and returns snippets, blueprint includes Current State section."""
    storage = MagicMock()
    handover = {
        "violations_by_rule": {
            "W9006": [
                {
                    "locations": [
                        str(Path("src/excelsior_architect/domain/analysis.py").resolve()) + ":35"
                    ]
                }
            ]
        }
    }
    storage.read_artifact.return_value = json.dumps(handover)
    graph_gateway = MagicMock()
    graph_gateway.query_recommended_strategies.return_value = [
        {
            "pattern": "Facade",
            "rationale": "Hide chain access",
            "affected_files": [
                str(Path("src/excelsior_architect/domain/analysis.py").resolve())
            ],
            "violations": ["W9006"],
            "score": 5,
        }
    ]
    ingestor = MagicMock()
    telemetry = MagicMock()
    snippet_extractor = MagicMock()
    snippet_extractor.extract_at.return_value = CodeSnippet(
        file_path="analysis.py",
        symbol_or_line="cluster",
        source="def cluster(self): ...",
    )

    use_case = GenerateBlueprintUseCase(
        storage=storage,
        graph_gateway=graph_gateway,
        ingestor=ingestor,
        telemetry=telemetry,
        snippet_extractor=snippet_extractor,
    )
    result = use_case.execute(source="check", root_dir=".")

    assert result == "BLUEPRINT.md"
    content = storage.write_artifact.call_args[0][1]
    assert "Current State (code to refactor)" in content
    assert "```python" in content
    assert "def cluster(self): ..." in content


def test_execute_writes_blueprint_and_returns_path():
    """execute ingests project, queries strategies, writes BLUEPRINT.md and returns path."""
    storage = MagicMock()
    handover = {"violations_by_rule": {"W9004": [{"message": "I/O in domain", "locations": ["domain/x.py:1"]}]}}
    storage.read_artifact.return_value = json.dumps(handover)
    graph_gateway = MagicMock()
    graph_gateway.query_recommended_strategies.return_value = []
    ingestor = MagicMock()
    telemetry = MagicMock()

    use_case = GenerateBlueprintUseCase(
        storage=storage,
        graph_gateway=graph_gateway,
        ingestor=ingestor,
        telemetry=telemetry,
    )
    result = use_case.execute(source="check", root_dir=".")

    assert result == "BLUEPRINT.md"
    storage.write_artifact.assert_called_once()
    call = storage.write_artifact.call_args
    assert call[0][0] == "BLUEPRINT.md"
    assert "Strategic Refactoring Playbook" in call[0][1]
    ingestor.ingest_project.assert_called_once()
