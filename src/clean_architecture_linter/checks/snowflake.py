"""Snowflake-specific governance checks (W9401, W9402, W9403)."""

from astroid import nodes
from pylint.checkers import BaseChecker
from clean_architecture_linter.helpers import get_call_name


class SnowflakeGovernanceChecker(BaseChecker):
    """Pipeline governance enforcement for Snowflake."""

    name = "snowflake-governance"
    msgs = {
        "W9601": (
            "Select Star Violation: 'SELECT *' detected. Specify columns explicitly. Clean Fix: List all required "
            "columns explicitly.",
            "select-star-violation",
            "Always specify explicit columns in SQL to prevent downstream breakages.",
        ),
        "W9602": (
            "Gold Layer View Warning: View detected in Gold layer. Prefer Tables or Dynamic Tables. Clean Fix: "
            "Materialize the view or use a Dynamic Table.",
            "gold-layer-view-violation",
            "Gold layer models should be materialized for performance and stability.",
        ),
        "W9603": (
            "Gold Layer Schema Evolution: Automatic schema evolution detected for Gold table. Clean Fix: Disable "
            "auto-evolution and manage schema migrations explicitly.",
            "gold-schema-evolution-violation",
            "Gold tables must have strict schemas. Disable automatic evolution.",
        ),
    }

    SQL_EXEC_METHODS = {"sql", "execute"}
    DATA_WRITE_METHODS = {"write_pandas", "create_view"}

    def __init__(self, linter=None):
        super().__init__(linter)
        self._is_snowflake_module = False

    def visit_module(self, node):
        """Analyze module imports to determine if Snowflake checks should be active."""
        self._is_snowflake_module = False

        # Determine internal tracking modules from config
        # Default empty list if not provided
        internal_modules = self.linter.config_loader.config.get(
            "governance_module_prefixes", []
        )

        # Check for Snowflake-related imports
        for import_node in node.nodes_of_class((nodes.Import, nodes.ImportFrom)):
            if isinstance(import_node, nodes.Import):
                for name, _ in import_node.names:
                    if self._is_snowflake_import(name, internal_modules):
                        self._is_snowflake_module = True
                        return
            elif isinstance(import_node, nodes.ImportFrom):
                if import_node.modname and self._is_snowflake_import(
                    import_node.modname, internal_modules
                ):
                    self._is_snowflake_module = True
                    return

    def _is_snowflake_import(self, module_name: str, internal_modules: list) -> bool:
        """Check if a module name is a Snowflake driver or configured internal wrapper."""
        if module_name.startswith("snowflake.connector") or module_name.startswith(
            "snowflake.snowpark"
        ):
            return True

        # Check configured internal wrappers
        for mod in internal_modules:
            if module_name.startswith(mod):
                return True
        return False

    def visit_call(self, node):
        """Check for governance violations if Snowflake is active for this module."""
        if not self._is_snowflake_module:
            return

        func_name = get_call_name(node)
        if not func_name:
            return

        # W9401: Select Star
        if func_name in self.SQL_EXEC_METHODS:
            self._check_select_star(node)

        # W9402: Gold Layer View
        if func_name == "create_view" or (
            func_name == "sql" and self._is_creating_view(node)
        ):
            self._check_gold_view(node)

        # W9403: Gold Schema Evolution
        if func_name == "write_pandas":
            self._check_gold_evolution(node)

    def _check_select_star(self, node):
        """W9401: Flag 'SELECT *' in SQL strings."""
        if not node.args:
            return

        first_arg = node.args[0]
        if isinstance(first_arg, nodes.Const) and isinstance(first_arg.value, str):
            val = first_arg.value
            sql = val.upper()
            if "SELECT *" in sql:
                self.add_message("select-star-violation", node=node)

    def _is_creating_view(self, node):
        """Check if a .sql() call contains CREATE VIEW."""
        if not node.args:
            return False
        first_arg = node.args[0]
        if isinstance(first_arg, nodes.Const) and isinstance(first_arg.value, str):
            val = first_arg.value
            return "CREATE VIEW" in val.upper()
        return False

    def _check_gold_view(self, node):
        """W9402: Flag views in Gold layer."""
        # Find any mention of _GOLD in the arguments
        for arg in node.args:
            if isinstance(arg, nodes.Const) and isinstance(arg.value, str):
                val = arg.value
                if "_GOLD" in val.upper():
                    self.add_message("gold-layer-view-violation", node=node)
                    return

    def _check_gold_evolution(self, node):
        """W9403: Flag auto_create_table=True in Gold layer."""
        # Check if any argument contains _GOLD
        is_gold = False
        for arg in node.args:
            if isinstance(arg, nodes.Const) and isinstance(arg.value, str):
                val = arg.value
                if "_GOLD" in val.upper():
                    is_gold = True
                    break

        if not is_gold and node.keywords:
            for kw in node.keywords:
                if isinstance(kw.value, nodes.Const) and isinstance(
                    kw.value.value, str
                ):
                    val = kw.value.value
                    if "_GOLD" in val.upper():
                        is_gold = True
                        break

        if not is_gold:
            return

        # Check for auto_create_table keyword
        if node.keywords:
            for kw in node.keywords:
                if kw.arg == "auto_create_table":
                    if isinstance(kw.value, nodes.Const) and kw.value.value is True:
                        self.add_message("gold-schema-evolution-violation", node=node)
                        return
