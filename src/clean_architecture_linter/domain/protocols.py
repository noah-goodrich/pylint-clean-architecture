from typing import TYPE_CHECKING, List, Optional, Protocol

if TYPE_CHECKING:
    import astroid  # type: ignore[import-untyped]  # pylint: disable=clean-arch-resources

    from clean_architecture_linter.domain.config import ConfigurationLoader  # pylint: disable=clean-arch-resources
    from clean_architecture_linter.domain.entities import LinterResult



class TypeshedProtocol(Protocol):
    """Protocol for Typeshed integration."""
    def is_stdlib_module(self, module_name: str) -> bool: ...
    def is_stdlib_qname(self, qname: str) -> bool: ...

class AstroidProtocol(Protocol):
    def get_node_return_type_qname(self, node: "astroid.nodes.NodeNG") -> Optional[str]:
        ...

    def get_return_type_qname_from_expr(self, expr: "astroid.nodes.NodeNG") -> Optional[str]:
        ...

    def is_protocol(self, node: "astroid.nodes.NodeNG") -> bool:
        ...

    def is_protocol_call(self, node: "astroid.nodes.Call") -> bool:
        ...

    def is_primitive(self, qname: str) -> bool:
        ...

    def is_trusted_authority_call(self, node: "astroid.nodes.Call") -> bool:
        ...

    def is_fluent_call(self, node: "astroid.nodes.Call") -> bool:
        ...

    def get_call_name(self, node: "astroid.nodes.Call") -> Optional[str]:
        ...

    def clear_inference_cache(self) -> None:
        """Clear the astroid inference cache to force fresh inference after code changes."""
        ...

    def parse_file(self, file_path: str) -> Optional["astroid.nodes.Module"]:
        """Parse a file and return the astroid Module node."""
        ...


class PythonProtocol(Protocol):
    def is_stdlib_module(self, module_name: str) -> bool:
        ...

    def is_external_dependency(self, file_path: Optional[str]) -> bool:
        ...

    def is_exception_node(self, node: "astroid.nodes.ClassDef") -> bool:
        ...

    def is_protocol_node(self, node: "astroid.nodes.ClassDef") -> bool:
        ...

    def get_node_layer(self, node: "astroid.nodes.NodeNG", config_loader: "ConfigurationLoader") -> Optional[str]:
        ...

class LinterAdapterProtocol(Protocol):
    """Protocol for linter adapters."""
    def gather_results(self, target_path: str) -> list["LinterResult"]: ...

class FixerGatewayProtocol(Protocol):
    """Protocol for applying code fixes via LibCST."""
    def apply_fixes(self, file_path: str, fixes: list[any]) -> bool:
        """Apply a list of fix suggestions to a file. Returns True if modified."""
        ...

class TelemetryPort(Protocol):
    """Protocol for telemetry/UI updates."""
    def step(self, message: str) -> None: ...
    def error(self, message: str) -> None: ...
    def handshake(self) -> None: ...


class FileSystemProtocol(Protocol):
    """Protocol for filesystem operations - abstracts Path usage."""
    def resolve_path(self, path: str) -> str:
        """Resolve and normalize a path string."""
        ...

    def is_directory(self, path: str) -> bool:
        """Check if path is a directory."""
        ...

    def glob_python_files(self, path: str) -> List[str]:
        """Get all Python files in path (recursive if directory)."""
        ...

    def get_path_string(self, path: str) -> str:
        """Convert path to string representation."""
        ...

    def make_dirs(self, path: str, exist_ok: bool = True) -> None:
        """Create directory and parent directories if needed."""
        ...

    def write_text(self, path: str, content: str, encoding: str = "utf-8") -> None:
        """Write text content to a file."""
        ...

    def join_path(self, *paths: str) -> str:
        """Join path components into a single path string."""
        ...

    def get_mtime(self, path: str) -> float:
        """Get file modification time as timestamp."""
        ...
