"""Pattern checks (W9005, W9006)."""

from typing import TYPE_CHECKING, Dict, List, Optional

import astroid  # type: ignore[import-untyped]
from pylint.checkers import BaseChecker

if TYPE_CHECKING:
    from pylint.lint import PyLinter

from clean_architecture_linter.domain.config import ConfigurationLoader
from clean_architecture_linter.domain.protocols import AstroidProtocol, PythonProtocol

_MIN_CHAIN_LENGTH: int = 2
_MAX_SELF_CHAIN_LENGTH: int = 2


class PatternChecker(BaseChecker):
    """W9005: Delegation anti-pattern detection with prescriptive advice."""

    name: str = "clean-arch-delegation"

    def __init__(self, linter: "PyLinter") -> None:
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
        if self._is_main_block(node):
            return

        is_delegation, advice = self._check_delegation_chain(node)
        if is_delegation:
            self.add_message(
                "clean-arch-delegation",
                node=node,
                args=(advice or "Refactor to Strategy, Handler, or Adapter pattern.",),
            )

    def _is_main_block(self, node: astroid.nodes.If) -> bool:
        """Heuristic for 'if __name__ == "__main__"'."""
        return (
            isinstance(node.test, astroid.nodes.Compare)
            and isinstance(node.test.left, astroid.nodes.Name)
            and node.test.left.name == "__name__"
        )

    def _check_delegation_chain(self, node: astroid.nodes.If, depth: int = 0) -> tuple[bool, Optional[str]]:
        """Check if if/elif chain is purely delegating."""
        if len(node.body) != 1:
            return False, None

        stmt = node.body[0]
        if not self._is_delegation_call(stmt):
            return False, None

        advice: str = "Refactor to Strategy/Handler pattern."
        if isinstance(node.test, astroid.nodes.Compare) and isinstance(node.test.left, astroid.nodes.Name):
            advice: str = "Refactor to **Strategy Pattern** using a dictionary mapping."

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

    name: str = "clean-arch-demeter"

    def __init__(
        self,
        linter: "PyLinter",
        ast_gateway: Optional[AstroidProtocol] = None,
        python_gateway: Optional[PythonProtocol] = None,
    ) -> None:
        self.msgs = {
            "W9006": (
                "Law of Demeter: Chain access (%s) exceeds one level. Create delegated method. "
                "Clean Fix: Add a method to the immediate object that performs the operation.",
                "clean-arch-demeter",
                "OBJECTS SHOULD NOT EXPOSE INTERNALS. Violating Demeter (a.b.c) couples code to structure.",
            ),
        }
        super().__init__(linter)
        self._locals_map: Dict[str, bool] = {}
        self._ast_gateway = ast_gateway
        self._python_gateway = python_gateway

    def visit_functiondef(self, _node: astroid.nodes.FunctionDef) -> None:
        """Reset locals map for each function."""
        self._locals_map = {}

    def visit_assign(self, node: astroid.nodes.Assign) -> None:
        """Track if a local variable is created from a method call (likely a stranger)."""
        if not isinstance(node.value, astroid.nodes.Call):
            return

        # If it's a trusted call, it's NOT a stranger
        if self._ast_gateway.is_trusted_authority_call(node.value):
            return

        # If the return type is a primitive (dict, list, str, etc.), it's NOT a stranger
        # This uses dynamic type inference - no hardcoded lists
        return_qname = self._ast_gateway.get_return_type_qname_from_expr(
            node.value)
        if return_qname and self._ast_gateway.is_primitive(return_qname):
            return

        # Additional check: If calling method on primitive receiver (dict.setdefault, list.append, etc.)
        # the result is safe. Use dynamic type inference on the receiver.
        if isinstance(node.value.func, astroid.nodes.Attribute):
            receiver_qname = self._ast_gateway.get_return_type_qname_from_expr(
                node.value.func.expr)
            if receiver_qname and self._ast_gateway.is_primitive(receiver_qname):
                return

        for target in node.targets:
            if isinstance(target, astroid.nodes.AssignName):
                self._locals_map[target.name] = True

    def visit_call(self, node: astroid.nodes.Call) -> None:
        """Check for Law of Demeter violations."""
        if self._is_test_file(node):
            return

        if self._check_method_chain(node):
            return

        self._check_stranger_variable(node)

    def _is_test_file(self, node: astroid.nodes.NodeNG) -> bool:
        """Detect if current node resides in a test file, excluding benchmarks/samples."""
        root = node.root()
        file_path: str = getattr(root, "file", "")
        if not file_path:
            return False

        # Avoid skipping our own test benchmarks/samples
        if any(x in file_path.lower() for x in ("benchmark", "samples", "bait")):
            return False

        parts = file_path.split("/")
        filename = parts[-1] if parts else ""

        # Only skip if it's in a 'tests' directory or starts with 'test_'
        # And NOT if it's a functional test target (usually in /tmp or snowfort_test)
        if "tests" in parts or filename.startswith("test_"):
            # Extra guard: if it's in /tmp/ it might be a functional test
            if "/tmp/" in file_path or "snowfort" in file_path:
                return False
            return True

        return False

    def _check_method_chain(self, node: astroid.nodes.Call) -> bool:
        """Case 1: Direct method chains."""
        if not isinstance(node.func, astroid.nodes.Attribute):
            return False

        chain: List[str] = []
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
        self.add_message("clean-arch-demeter", node=node, args=(full_chain,))
        return True

    def _is_assigned_from_primitive_method(self, var_node: astroid.nodes.Name) -> bool:
        """Check if a variable was assigned from a method call on a primitive (dict, list, etc.)."""
        # Find the assignment statement for this variable in the current function
        func_node = var_node.frame()
        if not isinstance(func_node, astroid.nodes.FunctionDef):
            return False

        # Look for Assign nodes that target this variable
        for assign in func_node.nodes_of_class(astroid.nodes.Assign):
            for target in assign.targets:
                if isinstance(target, astroid.nodes.AssignName) and target.name == var_node.name:
                    # Found the assignment - check if RHS is a Call on a primitive
                    if not isinstance(assign.value, astroid.nodes.Call):
                        return False

                    # Check if it's calling a method on a primitive receiver
                    if isinstance(assign.value.func, astroid.nodes.Attribute):
                        # Try to infer the receiver type
                        receiver_qname = self._ast_gateway.get_return_type_qname_from_expr(
                            assign.value.func.expr)
                        if receiver_qname and self._ast_gateway.is_primitive(receiver_qname):
                            return True

                        # Check if the receiver has an isinstance() type guard before this assignment
                        # This handles cases like: `if isinstance(x, dict): y = x.setdefault(...)`
                        if isinstance(assign.value.func.expr, astroid.nodes.Name):
                            receiver_name = assign.value.func.expr.name
                            if self._has_isinstance_primitive_guard(func_node, receiver_name, assign.lineno):
                                return True
                    return False
        return False

    def _unwrap_not(self, test: astroid.nodes.NodeNG) -> astroid.nodes.NodeNG:
        """Unwrap 'not' in `if not isinstance(...)` -> isinstance node."""
        if isinstance(test, astroid.nodes.UnaryOp) and test.op == "not":
            return test.operand
        return test

    def _isinstance_guard_var_primitive(
        self, test: astroid.nodes.Call, var_name: str
    ) -> bool:
        """Return True if test is isinstance(var_name, primitive_type)."""
        try:
            for inf in test.func.infer():
                if getattr(inf, "name", None) != "isinstance":
                    continue
                if len(test.args) < 2:
                    return False
                if not (
                    isinstance(test.args[0], astroid.nodes.Name)
                    and test.args[0].name == var_name
                ):
                    return False
                type_arg = test.args[1]
                for type_inf in type_arg.infer():
                    q = getattr(type_inf, "qname", None)
                    if q is None:
                        continue
                    type_qname = q() if callable(q) else q
                    if isinstance(type_qname, str) and self._ast_gateway.is_primitive(type_qname):
                        return True
                return False
        except (astroid.InferenceError, AttributeError):
            pass
        return False

    def _has_isinstance_primitive_guard(
        self,
        func_node: astroid.nodes.FunctionDef,
        var_name: str,
        before_line: int,
    ) -> bool:
        """Check if a variable has an isinstance(var, primitive_type) guard before the given line."""
        for if_node in func_node.nodes_of_class(astroid.nodes.If):
            if if_node.lineno >= before_line:
                continue
            test = self._unwrap_not(if_node.test)
            if isinstance(test, astroid.nodes.Call) and self._isinstance_guard_var_primitive(
                test, var_name
            ):
                return True
        return False

    def _check_stranger_variable(self, node: astroid.nodes.Call) -> None:
        """Case 2: Method called on a 'stranger' variable."""
        if isinstance(node.func, astroid.nodes.Attribute):
            expr = node.func.expr
            if isinstance(expr, astroid.nodes.Name) and self._locals_map.get(expr.name, False):
                # Double-check: Is this variable actually a primitive? Type inference can improve after assignment
                var_qname = self._ast_gateway.get_return_type_qname_from_expr(
                    expr)
                if var_qname and self._ast_gateway.is_primitive(var_qname):
                    return  # It's a primitive, not a stranger

                # Additional check: Look up the assignment and check if it came from a primitive method
                if self._is_assigned_from_primitive_method(expr):
                    return  # Assigned from primitive.method(), safe

                if self._is_chain_excluded(node, [node.func.attrname], expr):
                    return

                self.add_message(
                    "clean-arch-demeter",
                    node=node,
                    args=(f"{expr.name}.{node.func.attrname} (Stranger)",),
                )

    def _excluded_by_environment_or_trust(
        self,
        node: astroid.nodes.Call,
        curr: astroid.nodes.NodeNG,
        config_loader: "ConfigurationLoader",
    ) -> bool:
        """Test/mock, overrides, trusted authority, protocol, fluent."""
        if self._is_test_file(node) or self._is_mock_involved(curr):
            return True
        if self._is_override_excluded(node, config_loader):
            return True
        if self._ast_gateway.is_trusted_authority_call(node):
            return True
        if isinstance(node.func, astroid.nodes.Attribute) and isinstance(
            node.func.expr, astroid.nodes.Call
        ):
            if self._ast_gateway.is_protocol_call(node.func.expr):
                return True
        return bool(self._ast_gateway.is_fluent_call(node))

    def _excluded_by_receiver_or_safe_source(
        self,
        node: astroid.nodes.Call,
        curr: astroid.nodes.NodeNG,
        chain: List[str],
        config_loader: "ConfigurationLoader",
    ) -> bool:
        """Primitive receiver, safe source, self/cls, local instantiation, hinted protocol."""
        if isinstance(node.func, astroid.nodes.Attribute):
            if self._is_primitive_receiver(node.func.expr):
                return True
        if self._is_safe_source(curr, config_loader):
            return True
        if self._is_self_or_cls(curr, chain):
            return True
        if self._is_locally_instantiated(curr):
            return True
        return bool(self._is_hinted_protocol(curr))

    def _is_chain_excluded(
        self,
        node: astroid.nodes.Call,
        chain: List[str],
        curr: astroid.nodes.NodeNG,
    ) -> bool:
        """Tiered logic for chain exclusion."""
        config_loader = ConfigurationLoader()
        if self._excluded_by_environment_or_trust(node, curr, config_loader):
            return True
        if self._excluded_by_receiver_or_safe_source(
            node, curr, chain, config_loader
        ):
            return True
        return self._is_allowed_by_inference(curr, config_loader)

    def _is_primitive_receiver(self, receiver: astroid.nodes.NodeNG) -> bool:
        """Check if the receiver of a call is a primitive type (LEGO brick)."""
        qname = self._ast_gateway.get_return_type_qname_from_expr(receiver)
        if qname:
            return self._ast_gateway.is_primitive(qname)
        return False

    def _is_self_or_cls(self, curr: astroid.nodes.NodeNG, chain: List[str]) -> bool:
        """Check if call is on self/cls within limits."""
        return (
            isinstance(curr, astroid.nodes.Name)
            and curr.name in ("self", "cls")
            and len(chain) <= _MAX_SELF_CHAIN_LENGTH
        )

    def _is_safe_source(self, receiver: astroid.nodes.NodeNG, config_loader: ConfigurationLoader) -> bool:
        """Check if receiver is a safe source."""
        # 1. Check Inference
        qname: Optional[str] = self._ast_gateway.get_return_type_qname_from_expr(
            receiver)
        if qname:
            if self._ast_gateway.is_primitive(qname):
                return True
            if self._python_gateway.is_stdlib_module(qname.split(".")[0]):
                return True

        # 2. Check Structural/Fallbacks
        if isinstance(receiver, astroid.nodes.Name):
            # Check if it's a known stdlib module name being used directly
            if self._python_gateway.is_stdlib_module(receiver.name):
                return True

        return self._is_inferred_safe(receiver, config_loader)

    def _is_inferred_safe(self, receiver: astroid.nodes.NodeNG, config_loader: ConfigurationLoader) -> bool:
        """Inference-based safety check."""
        try:
            for inferred in receiver.infer():
                if inferred is astroid.Uninferable:
                    continue

                inf_qname: str = getattr(inferred, "qname", lambda: "")()
                if self._check_mod_allowed(inf_qname, config_loader):
                    return True

                root_name: str = getattr(inferred.root(), "name", "")
                if self._check_mod_allowed(root_name, config_loader):
                    return True
        except (astroid.InferenceError, AttributeError):
            pass
        return False

    def _check_mod_allowed(self, mod_name: str, config_loader: ConfigurationLoader) -> bool:
        """Check if module is allowed."""
        if not mod_name:
            return False
        if self._python_gateway.is_stdlib_module(mod_name.split(".")[0]):
            return True

        if self._python_gateway.is_external_dependency(getattr(self.linter.current_file, "path", "")):
            # If we are IN infrastructure code, we might allow more things, but strictly speaking
            # we are checking if the *imported module* is allowed.
            pass

        allowed = config_loader.allowed_lod_roots
        return any(mod_name == m or mod_name.startswith(m + ".") for m in allowed)

    def _is_override_excluded(self, node: astroid.nodes.Call, config_loader: ConfigurationLoader) -> bool:
        """Explicit config override check."""
        try:
            if not isinstance(node.func, astroid.nodes.Attribute):
                return False

            for inferred in node.func.infer():
                if inferred is astroid.Uninferable:
                    continue
                qname = getattr(inferred, "qname", lambda: "")()
                # Deprecated: usage of allowed_lod_methods is discouraged in v3
                if qname in config_loader.allowed_lod_methods:
                    return True
        except (astroid.InferenceError, AttributeError):
            pass
        return False

    def _is_allowed_by_inference(self, node: astroid.nodes.NodeNG, config_loader: "ConfigurationLoader") -> bool:
        """Inferred layer allowance check."""
        qname: Optional[str] = self._ast_gateway.get_return_type_qname_from_expr(
            node)
        if qname:
            if self._is_layer_allowed(qname, config_loader):
                return True
            if any(qname.startswith(root) for root in config_loader.allowed_lod_roots):
                return True
        return False

    def _is_layer_allowed(self, module_name: str, config_loader: "ConfigurationLoader") -> bool:
        """Check if a module belongs to an allowed layer."""
        layer: Optional[str] = config_loader.get_layer_for_module(module_name)
        if layer and ("domain" in layer.lower() or "dto" in layer.lower()):
            # Category 5: Domain Entities (Frozen Dataclasses)
            return True
        return False

    def _is_locally_instantiated(self, node: astroid.nodes.NodeNG) -> bool:
        """Detect if an object was instantiated as a local friend (Constructor Call)."""
        if not isinstance(node, astroid.nodes.Name):
            return False

        scope = node.scope()
        try:
            for def_node in node.lookup(node.name)[1]:
                if def_node.scope() != scope:
                    continue

                parent = def_node.parent
                if isinstance(parent, astroid.nodes.Assign) and isinstance(parent.value, astroid.nodes.Call):
                    # Category 4: Factory Exemption (Must be a Class instantiation)
                    call_node: astroid.nodes.Call = parent.value
                    func_node = call_node.func
                    for inf in func_node.infer():
                        if isinstance(inf, astroid.nodes.ClassDef):
                            return True
        except (astroid.InferenceError, AttributeError):
            pass
        return False

    def _is_hinted_protocol(self, node: astroid.nodes.NodeNG) -> bool:
        """Check if the inferred type is a Protocol or resides in a protocols module."""
        return self._ast_gateway.is_protocol(node)

    def _is_mock_involved(self, node: astroid.nodes.NodeNG) -> bool:
        """Detect if mock objects are involved in the expression."""
        qname = self._ast_gateway.get_return_type_qname_from_expr(node)
        if qname and any(m in qname for m in ("unittest.mock", "pytest", "MagicMock")):
            return True
        return False
