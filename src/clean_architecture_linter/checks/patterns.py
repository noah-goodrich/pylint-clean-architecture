"""Pattern checks (W9005, W9006)."""

from typing import TYPE_CHECKING, Optional

import astroid  # type: ignore[import-untyped]
from pylint.checkers import BaseChecker

if TYPE_CHECKING:
    from pylint.lint import PyLinter

from clean_architecture_linter.config import ConfigurationLoader

_MIN_CHAIN_LENGTH = 2
_MAX_SELF_CHAIN_LENGTH = 2


class PatternChecker(BaseChecker):
    """W9005: Delegation anti-pattern detection with prescriptive advice."""

    name = "clean-arch-delegation"

    def __init__(self, linter: Optional["PyLinter"] = None) -> None:
        self.msgs = {
            "W9005": (
                "Delegation Anti-Pattern: %s "
                "Clean Fix: Implement logic in the delegate or use a Map/Dictionary lookup.",
                "clean-arch-delegation",
                "If/elif chains that only delegate should use Strategy or Handler patterns.",
            ),
        }
        super().__init__(linter)

    def visit_if(self, node: astroid.nodes.If) -> None:
        """Check for delegation chains."""
        # Skip 'if __name__ == "__main__"' blocks
        if (
            isinstance(node.test, astroid.nodes.Compare)
            and isinstance(node.test.left, astroid.nodes.Name)
            and node.test.left.name == "__name__"
        ):
            return

        is_delegation, advice = self._check_delegation_chain(node)
        if is_delegation:
            self.add_message(
                "clean-arch-delegation",
                node=node,
                args=(advice or "Refactor to Strategy, Handler, or Adapter pattern.",),
            )

    def _check_delegation_chain(self, node: astroid.nodes.If, depth: int = 0) -> tuple[bool, Optional[str]]:
        """Check if if/elif chain is purely delegating."""
        if len(node.body) != 1:
            return False, None

        stmt = node.body[0]
        if not self._is_delegation_call(stmt):
            return False, None

        # Generate prescriptive advice based on condition type
        advice = "Refactor to Strategy/Handler pattern."
        if isinstance(node.test, astroid.nodes.Compare) and isinstance(node.test.left, astroid.nodes.Name):
            advice = "Refactor to **Strategy Pattern** using a dictionary mapping."

        # If strict guard clause (no else), it is NOT a delegation CHAIN unless deep recursion
        if not node.orelse:
            # Only flag if we are already deep in a chain (depth > 0)
            # This ignores simple 'if x: do_y()' guard clauses
            return depth > 0, advice

        if len(node.orelse) == 1:
            orelse = node.orelse[0]
            if isinstance(orelse, astroid.nodes.If):
                return self._check_delegation_chain(orelse, depth + 1)
            if self._is_delegation_call(orelse):
                # 3 branches: if/elif/else or if/elif/elif
                # Let's require depth >= 1 (so if/elif)
                return depth > 0, advice

        return False, None

    def _is_delegation_call(self, node: astroid.nodes.NodeNG) -> bool:
        """Check if node is 'return func(...)' or 'func(...)'."""
        if isinstance(node, astroid.nodes.Return):
            return isinstance(node.value, astroid.nodes.Call)
        if isinstance(node, astroid.nodes.Expr):
            return isinstance(node.value, astroid.nodes.Call)
        return False


class CouplingChecker(BaseChecker):
    """W9006: Law of Demeter violation detection."""

    name = "law-of-demeter"

    def __init__(self, linter: Optional["PyLinter"] = None) -> None:
        self.msgs = {
            "W9006": (
                "Law of Demeter: Chain access (%s) exceeds one level. Create delegated method. "
                "Clean Fix: Add a method to the immediate object that performs the operation.",
                "law-of-demeter",
                "OBJECTS SHOULD NOT EXPOSE INTERNALS. Violating Demeter (a.b.c) couples code to structure.",
            ),
        }
        super().__init__(linter)
        self._locals_map: dict[str, bool] = {}  # Map[variable_name] -> is_stranger (bool)

    # Common Repository/API patterns

    def visit_functiondef(self, _node: astroid.nodes.FunctionDef) -> None:
        """Reset locals map for each function."""
        self._locals_map = {}

    def visit_assign(self, node: astroid.nodes.Assign) -> None:
        """Track if a local variable is created from a method call (likely a stranger)."""
        if not isinstance(node.value, astroid.nodes.Call):
            return

        for target in node.targets:
            if isinstance(target, astroid.nodes.AssignName):
                self._locals_map[target.name] = True

    def visit_call(self, node: astroid.nodes.Call) -> None:
        """Check for Law of Demeter violations."""
        # Skip checks for test files
        root = node.root()
        file_path: str = getattr(root, "file", "")
        if "tests" in file_path.split("/") or "test_" in file_path.split("/")[-1]:
            return

        if self._is_method_chain_violation(node):
            return

        # Case 2: Method called on a 'stranger' variable
        if isinstance(node.func, astroid.nodes.Attribute):
            expr = node.func.expr
            if isinstance(expr, astroid.nodes.Name) and self._locals_map.get(expr.name, False):
                # It's a method call on a variable derived from another call.
                if self._is_chain_excluded(node, [node.func.attrname], expr):
                    return

                self.add_message(
                    "law-of-demeter",
                    node=node,
                    args=(f"{expr.name}.{node.func.attrname} (Stranger)",),
                )

    def _is_method_chain_violation(self, node: astroid.nodes.Call) -> bool:
        """Check direct method chains like a.b.c() or a().b()"""
        if not isinstance(node.func, astroid.nodes.Attribute):
            return False

        chain: list[str] = []
        curr: astroid.nodes.NodeNG = node.func
        while isinstance(curr, (astroid.nodes.Attribute, astroid.nodes.Call)):
            if isinstance(curr, astroid.nodes.Attribute):
                chain.append(curr.attrname)
                curr = curr.expr
            else:
                # Only count Call as a level if it's not the outermost call we are visiting
                if curr != node:
                    chain.append("()")
                curr = curr.func

        if len(chain) < _MIN_CHAIN_LENGTH:
            return False

        if self._is_chain_excluded(node, chain, curr):
            return False

        # Clean up display: replace .(). with ()
        full_chain = ".".join(reversed(chain)).replace(".()", "()")
        self.add_message("law-of-demeter", node=node, args=(full_chain,))
        return True

    def _is_chain_excluded(self, node: astroid.nodes.Call, chain: list[str], curr: astroid.nodes.NodeNG) -> bool:
        """Check if chain is excluded from Demeter checks using tiered logic."""
        config_loader = ConfigurationLoader()
        from clean_architecture_linter.helpers import get_return_type_qname

        # Tier 1 (Signature): Call get_return_type_qname (Full Chain Return Type)
        qname = get_return_type_qname(node)

        # Zero-Config Architecture: If return type is None (unresolved), it triggers a violation.
        # This forces the developer to provide a Type Hint.
        if qname is None:
            return False

        if qname == "builtins.NoneType":
            return True

        if self._is_safe_source(node.func.expr, config_loader):
            return True

        if self._is_override_excluded(node, config_loader):
            return True

        # Legacy/Essential exemptions
        if (
            isinstance(curr, astroid.nodes.Name)
            and curr.name in ("self", "cls")
            and len(chain) <= _MAX_SELF_CHAIN_LENGTH
        ):
            return True

        return bool(self._is_allowed_by_inference(curr, config_loader))

    def _is_safe_source(self, receiver: astroid.nodes.NodeNG, config_loader: ConfigurationLoader) -> bool:
        """Tier 2 logic: Check if receiver is a safe source (primitive or stdlib)."""
        from clean_architecture_linter.helpers import get_return_type_qname_from_expr, is_std_lib_module

        receiver_qname = get_return_type_qname_from_expr(receiver)
        if receiver_qname:
            # Legacy safe type check (manual list removed, relying on stdlib detection)
            if is_std_lib_module(receiver_qname.split(".")[0]):
                return True

        # Tier 2.5: Module Origin Fallback
        try:
            for inferred in list(receiver.infer()):
                if inferred is astroid.Uninferable:
                    continue

                inf_qname: str = getattr(inferred, "qname", lambda: "")()
                if inf_qname:
                    if any(inf_qname == m or inf_qname.startswith(m + ".") for m in config_loader.allowed_lod_modules):
                        return True
                    if is_std_lib_module(inf_qname.split(".")[0]):
                        return True

                root_name: str = getattr(inferred.root(), "name", "")
                if root_name:
                    if any(root_name == m or root_name.startswith(m + ".") for m in config_loader.allowed_lod_modules):
                        return True
                    if is_std_lib_module(root_name.split(".")[0]):
                        return True
        except (astroid.InferenceError, AttributeError):
            pass
        return False

    def _is_override_excluded(self, node: astroid.nodes.Call, config_loader: ConfigurationLoader) -> bool:
        """Tier 3 logic: Check for explicit configuration overrides."""
        try:
            func = node.func
            if not isinstance(func, astroid.nodes.Attribute):
                return False

            for inferred_method in func.infer():
                if inferred_method is astroid.Uninferable:
                    continue

                method_qname = getattr(inferred_method, "qname", lambda: "")()
                if method_qname and method_qname in config_loader.allowed_lod_methods:
                    return True
        except (astroid.InferenceError, AttributeError):
            pass
        return False

    def _is_allowed_by_inference(self, node: astroid.nodes.NodeNG, config_loader: ConfigurationLoader) -> bool:
        """Check if inferred type is allowed (e.g. Domain Entity)."""
        from clean_architecture_linter.helpers import get_return_type_qname_from_expr

        qname = get_return_type_qname_from_expr(node)
        if qname:
            if self._is_layer_allowed(qname, config_loader):
                return True
            if any(qname.startswith(root) for root in config_loader.allowed_lod_roots):
                return True

        try:
            for inferred in node.infer():
                if inferred is astroid.Uninferable:
                    continue
                module_name = getattr(inferred.root(), "name", "")
                if module_name:
                    if module_name in config_loader.allowed_lod_roots:
                        return True
                    if self._is_layer_allowed(module_name, config_loader):
                        return True
        except astroid.InferenceError:
            pass
        return False

    def _is_layer_allowed(self, module_name: str, config_loader: ConfigurationLoader) -> bool:
        """Check if a module belongs to an allowed layer (Domain/DTO)."""
        layer = config_loader.get_layer_for_module(module_name)
        return bool(layer and ("domain" in layer.lower() or "dto" in layer.lower()))
