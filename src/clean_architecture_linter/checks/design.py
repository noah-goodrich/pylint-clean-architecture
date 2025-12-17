import ast
import astroid
from pylint.checkers import BaseChecker
from clean_architecture_linter.config import ConfigurationLoader

class DesignChecker(BaseChecker):
    name = 'clean-architecture-design'
    msgs = {
        'W9007': (
            'Naked Return from External Access: Repository/Client method returns raw I/O object (%s). Must return a decoupled Domain Entity.',
            'naked-return-violation',
            'Used when an external access layer returns a raw connection/cursor object.'
        ),
        'W9008': (
            'Unused Parameter in Abstract/Domain Layer: "%s". Interfaces must be clean.',
            'unused-parameter-violation',
            'Used when an argument is unused in a Domain or Interface layer function.'
        ),
    }

    def __init__(self, linter=None):
        super().__init__(linter)
        self.config_loader = ConfigurationLoader()
        # Define some common raw types we want to ban strictly in returns
        # This could be configurable.
        self.raw_types = {'Cursor', 'Session', 'Response', 'Engine', 'Connection'}

    def visit_return(self, node):
        try:
            # W9007: Naked Return
            if not node.value:
                return

            current_module = self.linter.current_name
            if not current_module:
                return

            layer_config = self.config_loader.get_layer_config(current_module)
            # We only really care about "External Access" layers for this rule.
            # But since we don't have "layer type" in config yet, maybe we check if
            # the layer allows 'database_io' or 'network_io'?
            # Or we assume user configures specific layers for this check eventually.
            # For now, let's just run it locally and check if we are returning a banned type.

            # We need to know if the current function is in a layer that *should* be returning entities.
            # That's usually the "Repository" or "Gateway" layer.

            # Check return value type name
            type_name = self._get_type_name(node.value)
            if type_name in self.raw_types:
                 self.add_message('naked-return-violation', node=node, args=(type_name,))
        except Exception:
            import traceback
            traceback.print_exc()

    def visit_functiondef(self, node):
        try:
            # W9008: Unused params
            # Only check domain/interface layers
            current_module = self.linter.current_name
            if not current_module: return

            layer_config = self.config_loader.get_layer_config(current_module)
            if not layer_config: return # Only check governed layers

            # We can loosely identify "domain" by name or config.
            # For now, apply to all governed layers to enforce cleanliness?
            # Or maybe strict mode? Let's apply to all implementation layers.

            # Skip abstract methods
            if not node.body: return # stub
            if any(isinstance(d, ast.Name) and d.id == 'abstractmethod' for d in node.decorator_list):
                return

            # Get args
            args = [a.arg for a in node.args.args]
            if 'self' in args: args.remove('self')
            if 'cls' in args: args.remove('cls')

            # Check usage in body
            used_names = set()
            for subnode in node.nodes_of_class(astroid.nodes.Name): # astroid method to walk
                 if subnode.lookup(subnode.name)[0] == subnode:
                     # This is getting complex. Let's stick to simple name match.
                     pass

            # Simpler walk:
            for subnode in node.nodes_of_class(astroid.nodes.Name):
                 used_names.add(subnode.name)

            for arg in args:
                if arg not in used_names:
                    # Flag it
                    self.add_message('unused-parameter-violation', node=node, args=(arg,))
        except Exception:
            import traceback
            traceback.print_exc()

    def _get_type_name(self, node):
        if isinstance(node, astroid.nodes.Call):
            # Returning a call? Foo()
            if hasattr(node.func, 'name'):
                return node.func.name
            if hasattr(node.func, 'attrname'):
                return node.func.attrname
        if hasattr(node, 'name'):
            return node.name
        return None
