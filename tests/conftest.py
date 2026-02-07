"""Pytest configuration and insulation from sibling repositories.

Run pytest from this project's root with PYTHONPATH=src. pythonpath and
rootdir in pyproject.toml keep collection and imports scoped to
excelsior-architect so sibling projects (e.g. pytest-coverage-impact)
never pollute runs.
"""

from unittest.mock import MagicMock


def apply_fixes_required_deps(**overrides: object) -> dict[str, object]:
    """Return required dependency mocks for ApplyFixesUseCase. Pass overrides to customize."""
    base = {
        "linter_adapter": MagicMock(),
        "telemetry": MagicMock(),
        "astroid_gateway": MagicMock(),
        "ruff_adapter": MagicMock(),
        "check_audit_use_case": MagicMock(),
        "config_loader": MagicMock(),
        "excelsior_adapter": MagicMock(),
        "violation_bridge": MagicMock(),
    }
    base.update(overrides)
    return base
