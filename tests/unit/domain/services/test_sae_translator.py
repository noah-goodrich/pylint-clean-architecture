"""Unit tests for SAETranslator."""
from excelsior_architect.domain.services.sae_translator import SAETranslator


def test_translate_blueprint_to_contexts_maps_strategies_to_contexts():
    """translate_blueprint_to_contexts returns one context per RecommendedStrategy."""
    diagnosis = [
        {
            "pattern": "Repository",
            "rationale": "Centralize data access.",
            "affected_files": ["domain/repo.py", "use_cases/foo.py"],
            "violations": ["W9004", "W9001"],
            "score": 0.9,
        },
    ]
    translator = SAETranslator()
    result = translator.translate_blueprint_to_contexts(diagnosis)
    assert len(result) == 1
    assert result[0]["pattern"] == "Repository"
    assert result[0]["rationale"] == "Centralize data access."
    assert result[0]["affected_files"] == ["domain/repo.py", "use_cases/foo.py"]
    assert result[0]["violations"] == ["W9004", "W9001"]
    assert result[0]["steps"] == []


def test_translate_blueprint_to_contexts_empty_returns_empty():
    """translate_blueprint_to_contexts with empty diagnosis returns empty list."""
    translator = SAETranslator()
    assert translator.translate_blueprint_to_contexts([]) == []
