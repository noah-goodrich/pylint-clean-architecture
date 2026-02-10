"""FileSystemProtocol implementation that reads from package resources via importlib.resources."""

from importlib.resources import files

from excelsior_architect.domain.protocols import FileSystemProtocol


class PackageResourceFileSystem(FileSystemProtocol):
    """Reads package data via importlib.resources. Supports read_text only; write ops raise."""

    def __init__(self, package: str = "excelsior_architect") -> None:
        self._package = package

    def _resource_path(self, path: str) -> str:
        """Normalize path for package resources (forward slashes, no leading slash)."""
        return path.replace("\\", "/").lstrip("/")

    def read_text(self, path: str, encoding: str = "utf-8") -> str:
        """Read text from a package resource."""
        resource_path = self._resource_path(path)
        traversable = files(self._package).joinpath(*resource_path.split("/"))
        return traversable.read_text(encoding=encoding)

    def resolve_path(self, path: str) -> str:
        """Return path as-is (package resources have no filesystem path)."""
        return self._resource_path(path)

    def is_directory(self, path: str) -> bool:
        """Check if path is a directory in package resources."""
        resource_path = self._resource_path(path)
        traversable = files(self._package).joinpath(*resource_path.split("/"))
        return traversable.is_dir()

    def glob_python_files(self, path: str) -> list[str]:
        """Not supported for package resources."""
        raise NotImplementedError("glob_python_files not supported for package resources")

    def get_path_string(self, path: str) -> str:
        """Return path as string."""
        return self._resource_path(path)

    def make_dirs(self, path: str, exist_ok: bool = True) -> None:
        """Package resources are read-only."""
        raise NotImplementedError("make_dirs not supported for package resources")

    def exists(self, path: str) -> bool:
        """Check if resource exists in package."""
        resource_path = self._resource_path(path)
        traversable = files(self._package).joinpath(*resource_path.split("/"))
        return traversable.is_file()

    def write_text(self, path: str, content: str, encoding: str = "utf-8") -> None:
        """Package resources are read-only."""
        raise NotImplementedError("write_text not supported for package resources")

    def append_text(self, path: str, content: str, encoding: str = "utf-8") -> None:
        """Package resources are read-only."""
        raise NotImplementedError("append_text not supported for package resources")

    def join_path(self, *paths: str) -> str:
        """Join path components with forward slashes."""
        return "/".join(p.lstrip("/") for p in paths if p)

    def get_mtime(self, path: str) -> float:
        """Package resources may not have mtime; return 0."""
        return 0.0
