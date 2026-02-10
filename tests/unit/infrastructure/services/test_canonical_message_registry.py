"""Unit tests for CanonicalMessageRegistry."""
from unittest.mock import MagicMock

from excelsior_architect.infrastructure.services.canonical_message_registry import (
    CanonicalMessageRegistry,
)


def test_get_canonical_message_returns_description_from_csv():
    """Registry loads CSV and returns Description for rule_id."""
    fs = MagicMock()
    fs.read_text.return_value = (
        "Tool,Code,Name,Description,Common Solution\n"
        "Excelsior,W9004,Forbidden I/O,I/O detected in Domain/UseCase layer.,Adapter\n"
    )
    registry = CanonicalMessageRegistry(filesystem=fs, paths=[("excelsior", "excelsior.csv")])
    assert registry.get_canonical_message("excelsior.W9004") == "I/O detected in Domain/UseCase layer."
    assert registry.get_canonical_or_fallback("excelsior.W9004", "fallback") == "I/O detected in Domain/UseCase layer."


def test_get_canonical_or_fallback_returns_fallback_when_not_found():
    """When rule_id not in registry, get_canonical_or_fallback returns fallback."""
    fs = MagicMock()
    fs.read_text.return_value = "Tool,Code,Name,Description\nExcelsior,W9004,name,desc\n"
    registry = CanonicalMessageRegistry(filesystem=fs, paths=[("excelsior", "e.csv")])
    assert registry.get_canonical_or_fallback("excelsior.UNKNOWN", "instance msg") == "instance msg"
    assert registry.get_canonical_message("excelsior.UNKNOWN") == ""
