"""Registry mapping rule codes to canonical (summary) messages from violation CSVs."""

import csv
import io
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from excelsior_architect.domain.protocols import FileSystemProtocol


# Paths relative to package (loaded via FileSystemProtocol)
_DEFAULT_VIOLATION_PATHS = [
    ("ruff", "resources/data/ruff_violations.csv"),
    ("mypy", "resources/data/mypy_violations.csv"),
    ("excelsior", "resources/data/excelsior_violations.csv"),
]


class CanonicalMessageRegistry:
    """
    Maps rule_id (linter.code) to canonical summary message from violation registries.

    Canonical messages are used for summaries, graph storage, and UI tables.
    Instance-specific messages (with location/context) remain in logs and fix plans.
    """

    def __init__(
        self,
        filesystem: "FileSystemProtocol",
        paths: list[tuple[str, str]] | None = None,
    ) -> None:
        self._fs = filesystem
        self._paths = paths or _DEFAULT_VIOLATION_PATHS
        self._registry: dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        """Load canonical messages from violation CSVs. Key = linter.code, Value = Description."""
        for linter, path in self._paths:
            try:
                content = self._fs.read_text(path)
                for row in csv.DictReader(io.StringIO(content)):
                    code = row.get("Code", "").strip()
                    desc = row.get("Description", "").strip()
                    if code and desc:
                        key = f"{linter}.{code}"
                        self._registry[key] = desc
            except Exception:
                continue

    def get_canonical_message(self, rule_id: str) -> str:
        """
        Return canonical message for rule_id (e.g. ruff.C901, mypy.no-untyped-def).
        Falls back to empty string if not found.
        """
        return self._registry.get(rule_id, "")

    def get_canonical_or_fallback(self, rule_id: str, fallback: str) -> str:
        """Return canonical message, or fallback if not in registry."""
        return self._registry.get(rule_id) or fallback
