"""Unit tests for CodeSnippetExtractor."""
from unittest.mock import MagicMock

from excelsior_architect.infrastructure.services.code_snippet_extractor import (
    CodeSnippetExtractor,
)


def test_extract_at_returns_none_when_file_missing() -> None:
    """Extractor returns None when file does not exist."""
    fs = MagicMock()
    fs.exists.return_value = False
    extractor = CodeSnippetExtractor(filesystem=fs, ast_protocol=MagicMock())
    result = extractor.extract_at("/nonexistent/path.py", 1, ".")
    assert result is None
