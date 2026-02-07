"""Missing Type Hint Rule (W9015) - High-Integrity Auto-Fix."""

from typing import Literal

import astroid

from excelsior_architect.domain.entities import TransformationPlan
from excelsior_architect.domain.protocols import AstroidProtocol
from excelsior_architect.domain.rules import BaseRule, Violation
from excelsior_architect.domain.transformation_contexts import ImportContext


class MissingTypeHintRule(BaseRule):
    """
    High-Integrity Rule for Missing Type Hints (W9015).

    Only fixes when type inference is deterministic and non-Any.
    """

    code: str = "W9015"
    description: str = "Missing Type Hint: All function and method signatures must be fully type-hinted."
    fix_type: Literal["code"] = "code"

    def __init__(self, ast_gateway: AstroidProtocol) -> None:
        self.ast_gateway = ast_gateway

    def check(self, node: astroid.nodes.NodeNG) -> list[Violation]:
        """
        Check for missing type hints in function definitions.

        Returns violations with fixable=True only when type can be deterministically inferred.
        """
        violations: list[Violation] = []

        if not isinstance(node, astroid.nodes.Module):
            return violations

        # Find all function definitions in the module
        for func_def_node in node.nodes_of_class(astroid.nodes.FunctionDef):
            if not isinstance(func_def_node, astroid.nodes.FunctionDef):
                continue
            func_def = func_def_node
            # Check return type
            if not func_def.returns:
                return_type_qname = self._infer_return_type(func_def)
                fixable, failure_reason = self._can_fix_type(return_type_qname)

                violations.append(Violation.from_node(
                    code=self.code,
                    message=f"Missing Type Hint: return type in {func_def.name} signature.",
                    node=func_def,
                    fixable=fixable,
                    fix_failure_reason=failure_reason,
                ))

            # Check parameters
            for i, arg in enumerate(func_def.args.args):
                # Skip self/cls for methods
                is_method = func_def.is_method()
                if i == 0 and is_method and arg.name in ("self", "cls"):
                    continue

                # Check if parameter has annotation
                has_hint = False
                has_annotation = (
                    (i < len(func_def.args.annotations)
                     and func_def.args.annotations[i])
                    or (hasattr(arg, "annotation") and arg.annotation)
                )
                if has_annotation:
                    has_hint = True

                if not has_hint:
                    if not isinstance(arg, astroid.nodes.AssignName):
                        continue
                    param_type_qname = self._infer_parameter_type(
                        func_def, arg, i)
                    fixable, failure_reason = self._can_fix_type(
                        param_type_qname)

                    violations.append(Violation.from_node(
                        code=self.code,
                        message=f"Missing Type Hint: parameter '{arg.name}' in {func_def.name} signature.",
                        node=arg,
                        fixable=fixable,
                        fix_failure_reason=failure_reason,
                    ))

        return violations

    def _infer_return_type(self, func_def: astroid.nodes.FunctionDef) -> str | None:
        """Infer return type using AstroidGateway."""
        # Look for return statements
        for return_node in func_def.nodes_of_class(astroid.nodes.Return):
            if not isinstance(return_node, astroid.nodes.Return):
                continue
            # Type narrowing: return_node is already Return type
            return_value = getattr(return_node, "value", None)
            if return_value:
                return self.ast_gateway.get_return_type_qname_from_expr(return_value)
        return None

    def _infer_parameter_type(
        self,
        func_def: astroid.nodes.FunctionDef,
        arg: astroid.nodes.AssignName,
        index: int,
    ) -> str | None:
        """Infer parameter type from default value or usage."""
        # Check if there's a default value
        args = func_def.args
        args_defaults = args.defaults
        if args_defaults:
            # Defaults are aligned from the right
            args_args = args.args
            diff = len(args_args) - len(args_defaults)
            if index >= diff:
                default_idx = index - diff
                return self.ast_gateway.get_node_return_type_qname(args_defaults[default_idx])

        # Try to infer from usage in function body
        # This is more complex - for now, return None if no default
        return None

    def _can_fix_type(self, type_qname: str | None) -> tuple[bool, str | None]:
        """
        Determine if a type can be safely fixed.

        Returns:
            (fixable: bool, failure_reason: Optional[str])
        """
        if type_qname is None:
            return (False, "Inference failed: Type could not be determined from context or stubs.")

        # Check if type is Any
        if "Any" in type_qname or type_qname.endswith(".Any"):
            return (False, "Injection Aborted: 'Any' is a banned type (W9016).")

        # Check if type is Uninferable
        if "Uninferable" in type_qname:
            return (False, "Inference failed: Type could not be determined from context or stubs.")

        # Type is specific and non-Any - can fix. Import safety is handled in fix()
        # by injecting required imports when needed.
        return (True, None)

    def fix(self, violation: Violation) -> list[TransformationPlan] | None:
        """
        Return transformation plans to fix the missing type hint.

        Only called if violation.fixable is True.
        """
        if not violation.fixable:
            return None

        node = violation.node

        # Determine if this is a return type or parameter type violation
        if isinstance(node, astroid.nodes.FunctionDef):
            # Return type violation
            return_type_qname = self._infer_return_type(node)
            if return_type_qname:
                # Convert qname to simple type name (e.g., "builtins.str" -> "str")
                type_name = self._qname_to_type_name(return_type_qname)
                plans: list[TransformationPlan] = []

                import_ctx = self._import_context_for_qname(
                    return_type_qname, node)
                if import_ctx:
                    plans.append(TransformationPlan.add_import(
                        import_ctx["module"], import_ctx["imports"]
                    ))

                plans.append(TransformationPlan.add_return_type(
                    function_name=node.name,
                    return_type=type_name,
                ))

                return plans

        elif isinstance(node, astroid.nodes.AssignName):
            # Parameter type violation
            # Need to get the function and parameter name from context
            func_def = node.parent
            if isinstance(func_def, astroid.nodes.FunctionDef):
                # Find which parameter this is
                for i, arg in enumerate(func_def.args.args):
                    if arg is node and isinstance(arg, astroid.nodes.AssignName):
                        param_type_qname = self._infer_parameter_type(
                            func_def, arg, i)
                        if param_type_qname:
                            type_name = self._qname_to_type_name(
                                param_type_qname)
                            plans = []

                            import_ctx = self._import_context_for_qname(
                                param_type_qname, arg)
                            if import_ctx:
                                plans.append(TransformationPlan.add_import(
                                    import_ctx["module"], import_ctx["imports"]
                                ))

                            plans.append(TransformationPlan.add_parameter_type(
                                function_name=func_def.name,
                                param_name=arg.name,
                                param_type=type_name,
                            ))

                            return plans

        return None

    def _import_context_for_qname(
        self, type_qname: str, node: astroid.nodes.NodeNG
    ) -> ImportContext | None:
        """Build AddImportTransformer context for a qname, or None if no import needed."""
        # builtins.* never needs imports
        if type_qname.startswith("builtins."):
            return None

        # typing.* types: import the short name from typing
        if type_qname.startswith("typing."):
            return {"module": "typing", "imports": [type_qname.split(".")[-1]]}

        # For module-qualified types, import the leaf name from its module.
        if "." not in type_qname:
            return None

        import_module, import_name = type_qname.rsplit(".", 1)

        # Avoid importing from the same module the node is defined in.
        root = node.root()
        current_module = getattr(root, "name", None)
        if current_module and current_module == import_module:
            return None

        return {"module": import_module, "imports": [import_name]}

    def _qname_to_type_name(self, qname: str) -> str:
        """Convert fully qualified name to simple type name."""
        # Handle builtins
        if qname.startswith("builtins."):
            return qname.split(".")[-1]
        # Handle typing module
        if qname.startswith("typing."):
            return qname.split(".")[-1]
        # Return last part
        return qname.split(".")[-1]

    def get_fix_instructions(self, violation: Violation) -> str:
        """Provide manual fix instructions."""
        if violation.fix_failure_reason:
            return f"Manual fix required: {violation.fix_failure_reason}"
        return "Add explicit type hints to all parameters and the return value."
