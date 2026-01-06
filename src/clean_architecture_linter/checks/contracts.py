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

        if not self._has_domain_protocol_ancestor(node):
            self.add_message("contract-integrity-violation", node=node, args=(node.name,))

    def _has_domain_protocol_ancestor(self, node):
        """Check if any ancestor is a domain protocol."""
        for ancestor in node.ancestors():
            try:
                ancestor_module = ancestor.root().name
                # Check if ancestor is from a domain module and ends with Protocol
                # Robust matching for .domain. or domain. at start
                if (".domain." in f".{ancestor_module}.") and ancestor.name.endswith("Protocol"):
                    return True
            except (AttributeError, ValueError):
                continue
        return False
