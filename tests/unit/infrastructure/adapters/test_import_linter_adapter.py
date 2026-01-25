from unittest.mock import MagicMock, patch

from clean_architecture_linter.infrastructure.adapters.import_linter_adapter import ImportLinterAdapter


def test_gather_results_success() -> None:
    adapter = ImportLinterAdapter()

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
            returncode = 1 # failure in linting, but success in execution
        )

        results = adapter.gather_results("src")

        assert len(results) > 0, "Should find violations"
        assert results[0].code == "IL001"
        assert "domain_isolation" in results[0].message
        assert "is not allowed to import" in results[0].message

def test_gather_results_fallback() -> None:
    adapter = ImportLinterAdapter()

    with patch("subprocess.run") as mock_run:
        # First call raises FileNotFoundError
        mock_run.side_effect = [FileNotFoundError, MagicMock(stdout = "", returncode = 0)]

        results = adapter.gather_results("src")

        # Should have called subprocess twice
        assert mock_run.call_count == 2
        # Should return empty list (success)
        assert results == []

def test_gather_results_exception() -> None:
    adapter = ImportLinterAdapter()
    with patch("subprocess.run", side_effect=Exception("Boom")):
        results = adapter.gather_results("src")
        assert len(results) == 1
        assert results[0].code == "IMPORT_LINTER_ERROR"
        assert "Boom" in results[0].message
