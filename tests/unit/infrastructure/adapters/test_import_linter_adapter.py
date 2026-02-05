from unittest.mock import MagicMock, patch

from clean_architecture_linter.infrastructure.adapters.import_linter_adapter import ImportLinterAdapter


def test_gather_results_success_broken_contract() -> None:
    """Parse 'Broken contract' + 'is not allowed to import' format."""
    adapter = ImportLinterAdapter(guidance_service=MagicMock())

    mock_output: str = """
Some header
Broken contracts
----------------

Broken contract: domain_isolation
Allowed layers:
- domain
- use_cases
...

domain.entities is not allowed to import infrastructure.db
    """

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            stdout=mock_output,
            returncode=1,
        )

        results = adapter.gather_results("src")

        assert len(results) > 0, "Should find violations"
        assert results[0].code == "IL001"
        assert "domain_isolation" in results[0].message
        assert "is not allowed to import" in results[0].message


def test_parse_output_no_matches_for_ignored_import() -> None:
    """Parse 'No matches for ignored import X -> Y' format (actual import-linter output)."""
    adapter = ImportLinterAdapter(guidance_service=MagicMock())

    mock_output = """
No matches for ignored import clean_architecture_linter.interface.cli ->
clean_architecture_linter.infrastructure.adapters.linter_adapters.
"""
    results = adapter._parse_output(mock_output)

    assert len(results) == 1
    assert results[0].code == "IL001"
    assert "interface.cli" in results[0].message
    assert "linter_adapters" in results[0].message

def test_gather_results_fallback() -> None:
    adapter = ImportLinterAdapter(guidance_service=MagicMock())

    with patch("subprocess.run") as mock_run:
        # First call raises FileNotFoundError
        mock_run.side_effect = [FileNotFoundError, MagicMock(stdout = "", returncode = 0)]

        results = adapter.gather_results("src")

        # Should have called subprocess twice
        assert mock_run.call_count == 2
        # Should return empty list (success)
        assert results == []

def test_gather_results_exception() -> None:
    adapter = ImportLinterAdapter(guidance_service=MagicMock())
    with patch("subprocess.run", side_effect=Exception("Boom")):
        results = adapter.gather_results("src")
        assert len(results) == 1
        assert results[0].code == "IMPORT_LINTER_ERROR"
        assert "Boom" in results[0].message
