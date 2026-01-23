from typing import Protocol, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    # JUSTIFICATION: Type checking imports for Domain Protocol definitions
    import astroid # type: ignore[import-untyped] # pylint: disable=clean-arch-resources
    # JUSTIFICATION: Type checking imports for Domain Protocol definitions
    from clean_architecture_linter.config import ConfigurationLoader # pylint: disable=clean-arch-resources
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


class PythonProtocol(Protocol):
    def is_std_lib_module(self, module_name: str) -> bool:
        ...

    def get_node_layer(self, node: "astroid.nodes.NodeNG", config_loader: "ConfigurationLoader") -> Optional[str]:
        ...

class LinterAdapterProtocol(Protocol):
    """Protocol for linter adapters."""
    def gather_results(self, target_path: str) -> list["LinterResult"]: ...
