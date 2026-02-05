from typing import TYPE_CHECKING, Optional, Protocol

from clean_architecture_linter.domain.registry_types import RuleRegistryEntry

if TYPE_CHECKING:
    from clean_architecture_linter.domain.config import ConfigurationLoader
    from clean_architecture_linter.domain.entities import (
        AuditResult,
        LinterResult,
        TransformationPlan,
    )
    from clean_architecture_linter.domain.rules import Violation


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


class StubAuthorityProtocol(Protocol):
    """Protocol for resolving .pyi stub paths and attribute types. Implemented by StubAuthority in infrastructure."""

    def get_stub_path(
        self, module_name: str, project_root: Optional[str] = None
    ) -> Optional[str]:
        """Resolve a .pyi path for a module. Returns path or None."""
        ...

    def get_attribute_type(
        self,
        module_name: str,
        class_name: str,
        attr_name: str,
        project_root: Optional[str] = None,
    ) -> Optional[str]:
        """Resolve an attribute's type from a .pyi. Returns qname (e.g. builtins.str) or None."""
        ...


class LinterAdapterProtocol(Protocol):
    """Protocol for linter adapters."""

    def gather_results(self, target_path: str,
                       select_only: Optional[list[str]] = None) -> list["LinterResult"]: ...

    def apply_fixes(
        self, target_path: str, select_only: Optional[list[str]] = None
    ) -> bool:
        """Apply automatic fixes. Returns True if any file was modified."""
        ...

    def supports_autofix(self) -> bool: ...
    def get_fixable_rules(self) -> list[str]: ...
    def get_manual_fix_instructions(self, rule_code: str) -> str: ...


class FixerGatewayProtocol(Protocol):
    """Protocol for applying code fixes. Implementers accept only TransformationPlan at boundary."""

    def apply_fixes(self, file_path: str, fixes: list["TransformationPlan"]) -> bool:
        """Apply a list of transformation plans to a file. Returns True if modified."""
        ...


class TelemetryPort(Protocol):
    """Protocol for telemetry/UI updates."""

    def step(self, message: str) -> None: ...
    def error(self, message: str) -> None: ...
    def warning(self, message: str) -> None: ...
    def handshake(self) -> None: ...


class FileSystemProtocol(Protocol):
    """Protocol for filesystem operations - abstracts Path usage."""

    def resolve_path(self, path: str) -> str:
        """Resolve and normalize a path string."""
        ...

    def is_directory(self, path: str) -> bool:
        """Check if path is a directory."""
        ...

    def glob_python_files(self, path: str) -> list[str]:
        """Get all Python files in path (recursive if directory)."""
        ...

    def get_path_string(self, path: str) -> str:
        """Convert path to string representation."""
        ...

    def make_dirs(self, path: str, exist_ok: bool = True) -> None:
        """Create directory and parent directories if needed."""
        ...

    def exists(self, path: str) -> bool:
        """Return True if path exists (file or directory)."""
        ...

    def read_text(self, path: str, encoding: str = "utf-8") -> str:
        """Read text content from a file."""
        ...

    def write_text(self, path: str, content: str, encoding: str = "utf-8") -> None:
        """Write text content to a file."""
        ...

    def append_text(self, path: str, content: str, encoding: str = "utf-8") -> None:
        """Append text to a file (creates if missing)."""
        ...

    def join_path(self, *paths: str) -> str:
        """Join path components into a single path string."""
        ...

    def get_mtime(self, path: str) -> float:
        """Get file modification time as timestamp."""
        ...


class ArtifactStorageProtocol(Protocol):
    """Protocol for storing and reading Excelsior artifacts (handover, fix plans, history).
    Keys are logical (e.g. last_audit_check.json, ai_handover_check.json, fix_plans/...).
    Implementation decides physical location (.excelsior/, stage, table)."""

    def write_artifact(self, key: str, content: str, encoding: str = "utf-8") -> None:
        """Write content to artifact at key. Overwrites if present."""
        ...

    def read_artifact(self, key: str, encoding: str = "utf-8") -> str:
        """Read artifact content at key. Raises if missing."""
        ...

    def exists(self, key: str) -> bool:
        """Return True if artifact at key exists."""
        ...

    def append_artifact(self, key: str, content: str, encoding: str = "utf-8") -> None:
        """Append content to artifact at key (e.g. NDJSON history). Creates if missing."""
        ...

    def get_artifact_timestamp(self, key: str) -> float:
        """Get modification time of artifact as timestamp. Optional for non-file backends."""
        ...


class AuditTrailServiceProtocol(Protocol):
    """Protocol for persisting audit results and handover bundles."""

    def save_audit_trail(
        self, audit_result: "AuditResult", source: Optional[str] = None
    ) -> None:
        """Save audit results to .excelsior directory."""
        ...

    def save_ai_handover(
        self, audit_result: "AuditResult", source: Optional[str] = None
    ) -> str:
        """Generate and save AI handover bundle. Returns path to JSON file."""
        ...

    def append_audit_history(
        self,
        audit_result: "AuditResult",
        source: str,
        json_path: str,
        txt_path: str,
    ) -> None:
        """Append one record to the audit history file (NDJSON)."""
        ...


class GuidanceServiceProtocol(Protocol):
    """Protocol for rule registry and manual/proactive guidance. Implemented by GuidanceService in infrastructure."""

    def get_manual_instructions(self, linter: str, rule_code: str) -> str:
        """Return manual fix instructions for the given linter and rule code."""
        ...

    def get_proactive_guidance(self, linter: str, rule_code: str) -> str:
        """Return proactive guidance for the rule."""
        ...

    def get_entry(self, linter: str, rule_code: str) -> Optional[RuleRegistryEntry]:
        """Return the full registry entry for the rule, or None."""
        ...

    def iter_proactive_guidance(self) -> list[tuple[str, str, str]]:
        """Yield (rule_id, short_description, proactive_guidance) for entries that have proactive_guidance."""
        ...

    def get_excelsior_entry(self, rule_code: str) -> Optional[RuleRegistryEntry]:
        """Return the full registry entry for an Excelsior rule by code or symbol."""
        ...

    def get_fixable_codes(self) -> list[str]:
        """Return list of Excelsior rule codes and symbols that are fixable (from registry)."""
        ...

    def get_comment_only_codes(self) -> list[str]:
        """Return list of Excelsior rule codes and symbols that are comment-only (from registry)."""
        ...

    def get_message_tuple(self, rule_code: str) -> Optional[tuple[str, str, str]]:
        """Return (message_template, symbol, description) for Pylint msgs, or None."""
        ...

    def get_display_name(self, rule_code: str) -> str:
        """Return display name for an Excelsior rule."""
        ...


class ViolationBridgeProtocol(Protocol):
    """Protocol for converting linter results to Violation objects. Implemented by ViolationBridgeService in infrastructure."""

    def convert_linter_results_to_violations(
        self, linter_results: list["LinterResult"], file_path: str
    ) -> list["Violation"]:
        """Convert LinterResult objects to Violation objects with astroid nodes."""
        ...


class StubCreatorProtocol(Protocol):
    """Protocol for creating .pyi stubs and extracting W9019 modules. Implemented in infrastructure."""

    def extract_w9019_modules(self, linter_results: list) -> set[str]:
        """Extract unique module names from W9019 (clean-arch-unstable-dep) results."""
        ...

    def create_stub(
        self,
        module: str,
        project_root: str,
        *,
        use_stubgen: bool = True,
        overwrite: bool = False,
    ) -> tuple[bool, str]:
        """Create a .pyi stub for the given module. Returns (success, message)."""
        ...


class ScaffolderProtocol(Protocol):
    """Protocol for project scaffolding and configuration."""

    def init_project(
        self, template: Optional[str] = None, check_layers: bool = False
    ) -> None:
        """Initialize project configuration and artifacts."""
        ...


class RawLogPort(Protocol):
    """Protocol for capturing raw subprocess stdout/stderr to log files."""

    def log_raw(self, tool: str, stdout: str, stderr: str) -> None:
        """Append raw tool output to .excelsior/logs/raw_{tool}.log."""
        ...
