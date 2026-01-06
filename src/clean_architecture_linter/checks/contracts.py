"""Contract Integrity checks (W9201)."""

from pylint.checkers import BaseChecker
from clean_architecture_linter.config import ConfigurationLoader
from clean_architecture_linter.layer_registry import LayerRegistry
from clean_architecture_linter.helpers import get_node_layer


class ContractChecker(BaseChecker):
    """W9201: Expert-Grade Contract Integrity enforcement."""

    name = "clean-arch-contracts"
    msgs = {
        "W9201": (
            "Contract Integrity Violation: Infrastructure class %s "
            "must inherit from a Domain Protocol.",
            "contract-integrity-violation",
            "Infrastructure classes must inherit from a Domain Protocol "
            "(module path contains '.domain.' and name ends with 'Protocol').",
        ),
    }

    def __init__(self, linter=None):
        super().__init__(linter)
        self.config_loader = ConfigurationLoader()

    def visit_classdef(self, node):
        """
        Check if infrastructure classes implement domain protocols.
        Uses node.ancestors() for semantic enforcement.
        """
        layer = get_node_layer(node, self.config_loader)

        # Only enforce on Infrastructure layer
        if layer != LayerRegistry.LAYER_INFRASTRUCTURE:
            return

        # Skip base classes/interfaces if they are in infrastructure but are generic
        if node.name.endswith("Base") or node.name.startswith("Base"):
            return

        # Skip private helper classes
        if node.name.startswith("_") or node.name.startswith("Test"):
            return

        # Skip Exceptions
        if any(ancestor.name == 'Exception' for ancestor in node.ancestors()):
            return

        # 1. Must have a Domain Protocol ancestor
        if not self._has_domain_protocol_ancestor(node):
            self.add_message("contract-integrity-violation", node=node, args=(node.name,))
            return

        # 2. Expert-Grade: Public methods must be defined in the Protocol
        protocol_methods = self._get_protocol_methods(node)
        for member in node.methods():
            if member.name.startswith("_"):
                continue

            # Common exclusions for constructors
            if member.name in ("__init__", "__post_init__"):
                continue

            if member.name not in protocol_methods:
                self.add_message("contract-integrity-violation", node=member, args=(f"{node.name}.{member.name} (not in Protocol)",))

    def _get_protocol_methods(self, node):
        """Collect public method names from all Domain Protocol ancestors."""
        methods = set()
        for ancestor in node.ancestors():
            if self._is_domain_protocol(ancestor):
                for method in ancestor.methods():
                    if not method.name.startswith("_"):
                        methods.add(method.name)
        return methods

    def _has_domain_protocol_ancestor(self, node):
        """Check if any ancestor is a domain protocol."""
        return any(self._is_domain_protocol(ancestor) for ancestor in node.ancestors())

    def _is_domain_protocol(self, ancestor):
        """Identify if an ancestor class is a Domain Protocol."""
        try:
            # Check for Protocol inheritance directly if possible
            is_protocol = any(getattr(b, "name", "") == "Protocol" for b in ancestor.bases)

            ancestor_module = ancestor.root().name
            # Rule: module path contains '.domain.' and name ends with 'Protocol'
            # OR it inherits from Protocol and is in a domain module
            in_domain = ".domain." in f".{ancestor_module}."

            if in_domain and (ancestor.name.endswith("Protocol") or is_protocol):
                return True
        except (AttributeError, ValueError):
            pass
        return False
