"""Local artifact storage - Infrastructure implementation of ArtifactStorageProtocol."""

from clean_architecture_linter.domain.protocols import (
    ArtifactStorageProtocol,
    FileSystemProtocol,
)


class LocalArtifactStorage(ArtifactStorageProtocol):
    """Stores Excelsior artifacts under a base path using FileSystemProtocol.
    Keys like last_audit_check.json, ai_handover_check.json, fix_plans/rule_id.md."""

    def __init__(self, base_path: str, filesystem: FileSystemProtocol) -> None:
        self._base = base_path
        self._fs = filesystem

    def _path(self, key: str) -> str:
        return self._fs.join_path(self._base, key)

    def _ensure_parent(self, key: str) -> None:
        if "/" in key or "\\" in key:
            parts = key.replace("\\", "/").rsplit("/", 1)
            if len(parts) == 2:
                parent_dir = self._fs.join_path(self._base, parts[0])
                self._fs.make_dirs(parent_dir, exist_ok=True)

    def write_artifact(self, key: str, content: str, encoding: str = "utf-8") -> None:
        """Write content to artifact at key. Overwrites if present."""
        self._ensure_parent(key)
        path = self._path(key)
        self._fs.make_dirs(self._base, exist_ok=True)
        self._fs.write_text(path, content, encoding=encoding)

    def read_artifact(self, key: str, encoding: str = "utf-8") -> str:
        """Read artifact content at key. Raises if missing."""
        path = self._path(key)
        return self._fs.read_text(path, encoding=encoding)

    def exists(self, key: str) -> bool:
        """Return True if artifact at key exists."""
        path = self._path(key)
        return self._fs.exists(path)

    def append_artifact(self, key: str, content: str, encoding: str = "utf-8") -> None:
        """Append content to artifact at key (e.g. NDJSON history). Creates if missing."""
        self._ensure_parent(key)
        path = self._path(key)
        self._fs.make_dirs(self._base, exist_ok=True)
        self._fs.append_text(path, content, encoding=encoding)

    def get_artifact_timestamp(self, key: str) -> float:
        """Get modification time of artifact as timestamp. Use empty key for base directory."""
        path = self._base if key == "" else self._path(key)
        return self._fs.get_mtime(path)
