"""Filesystem Gateway - Infrastructure implementation of FileSystemProtocol."""

from pathlib import Path
from typing import List

from clean_architecture_linter.domain.protocols import FileSystemProtocol


class FileSystemGateway(FileSystemProtocol):
    """Infrastructure implementation of FileSystemProtocol using pathlib."""

    def resolve_path(self, path: str) -> str:
        """Resolve and normalize a path string."""
        return str(Path(path).resolve())

    def is_directory(self, path: str) -> bool:
        """Check if path is a directory."""
        return Path(path).is_dir()

    def glob_python_files(self, path: str) -> List[str]:
        """Get all Python files in path (recursive if directory)."""
        path_obj = Path(path).resolve()
        if path_obj.is_dir():
            return [str(p) for p in path_obj.glob("**/*.py")]
        return [str(path_obj)] if path_obj.suffix == ".py" else []

    def get_path_string(self, path: str) -> str:
        """Convert path to string representation."""
        return str(Path(path))

    def make_dirs(self, path: str, exist_ok: bool = True) -> None:
        """Create directory and parent directories if needed."""
        Path(path).mkdir(parents=True, exist_ok=exist_ok)

    def write_text(self, path: str, content: str, encoding: str = "utf-8") -> None:
        """Write text content to a file."""
        Path(path).write_text(content, encoding=encoding)

    def join_path(self, *paths: str) -> str:
        """Join path components into a single path string."""
        return str(Path(*paths))

    def get_mtime(self, path: str) -> float:
        """Get file modification time as timestamp."""
        return Path(path).stat().st_mtime
