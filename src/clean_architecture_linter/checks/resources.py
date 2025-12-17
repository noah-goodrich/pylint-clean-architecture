import ast
from pylint.checkers import BaseChecker
from clean_architecture_linter.config import ConfigurationLoader

class ResourceChecker(BaseChecker):
    name = 'clean-architecture-resources'
    msgs = {
        'W9004': (
            'Resource access violation (%s) detected in layer %s.',
            'abstract-resource-access-violation',
            'Used when a function call matches a forbidden resource access pattern for the current layer.'
        ),
    }

    def __init__(self, linter=None):
        super().__init__(linter)
        self.config_loader = ConfigurationLoader()

    def visit_call(self, node):
        try:
            # 1. Start: Config check logic
            if not self.linter.current_name:
                return

            layer_config = self.config_loader.get_layer_config(self.linter.current_name)
            if not layer_config:
                return

            allowed_resources = set(layer_config.get("allowed_resources", []))

            # 2. Check the call name
            full_name = self._get_call_name(node)
            if not full_name:
                return

            resource_map = self.config_loader.get_resource_access_methods()

            for resource_type, patterns in resource_map.items():
                if resource_type in allowed_resources:
                    continue

                if full_name in patterns:
                    self.add_message(
                        'abstract-resource-access-violation',
                        node=node,
                        args=(resource_type, layer_config.get('name', 'Unknown'))
                    )
        except Exception:
            import traceback
            traceback.print_exc()

    def _get_call_name(self, node):
        """Helper to reconstruct 'module.func' from AST."""
        if hasattr(node.func, 'attrname'): # Attribute
             return self._stringify_node(node.func)
        elif hasattr(node.func, 'name'): # Name
             return node.func.name
        return None

    def _stringify_node(self, node):
        if hasattr(node, 'name'): # Name
            return node.name
        elif hasattr(node, 'attrname'): # Attribute
            base = self._stringify_node(node.expr)
            if base:
                return f"{base}.{node.attrname}"
            return node.attrname
        return None
