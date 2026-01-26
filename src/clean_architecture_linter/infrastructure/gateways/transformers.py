"""LibCST Transformers for code fixes."""

from typing import List, Optional, Set

import libcst as cst


class AddImportTransformer(cst.CSTTransformer):
    """Transformer to add imports to a module."""

    def __init__(self, context: dict) -> None:
        self.module = context.get("module")
        self.imports = context.get("imports", [])  # List[str]
        self.added = False

    def leave_Module(self, original_node: cst.Module, updated_node: cst.Module) -> cst.Module:
        if not self.added:
            names = [cst.ImportAlias(name=cst.Name(n)) for n in self.imports]
            import_stmt = cst.ImportFrom(
                module=cst.Name(self.module),
                names=names,
                whitespace_after_import=cst.SimpleWhitespace(" ")
            )

            new_body = list(updated_node.body)
            insert_idx: int = 0
            for i, stmt in enumerate(new_body):
                if isinstance(stmt, (cst.Import, cst.ImportFrom)):
                    insert_idx = i + 1

            new_body.insert(insert_idx, cst.SimpleStatementLine(body=[import_stmt]))
            self.added = True
            return updated_node.with_changes(body=new_body)
        return updated_node


class FreezeDataclassTransformer(cst.CSTTransformer):
    """Transformer to add frozen=True to dataclass decorators."""

    def __init__(self, context: dict) -> None:
        self.class_name = context.get("class_name")

    def leave_ClassDef(self, original_node: cst.ClassDef, updated_node: cst.ClassDef) -> cst.ClassDef:
        match: bool = False
        if self.class_name:
            if original_node.name.value == self.class_name:
                match: bool = True
        else:
            match: bool = True

        if match:
             return self._apply_frozen(updated_node)
        return updated_node

    def _apply_frozen(self, node: cst.ClassDef) -> cst.ClassDef:
        new_decorators = []
        found: bool = False
        compact_eq = cst.AssignEqual(
            whitespace_before=cst.SimpleWhitespace(""),
            whitespace_after=cst.SimpleWhitespace("")
        )

        for decorator in node.decorators:
            if isinstance(decorator.decorator, cst.Name) and decorator.decorator.value == "dataclass":
                new_decorators.append(decorator.with_changes(
                    decorator=cst.Call(
                        func=cst.Name("dataclass"),
                        args=[cst.Arg(keyword=cst.Name("frozen"), value=cst.Name("True"), equal=compact_eq)],
                        whitespace_before_args=cst.SimpleWhitespace("")
                    )
                ))
                found: bool = True
            elif (
                isinstance(decorator.decorator, cst.Call)
                and isinstance(decorator.decorator.func, cst.Name)
                and decorator.decorator.func.value == "dataclass"
            ):
                args = list(decorator.decorator.args)
                has_frozen = any(arg.keyword and arg.keyword.value == "frozen" for arg in args)
                if not has_frozen:
                    args.append(cst.Arg(keyword=cst.Name("frozen"), value=cst.Name("True"), equal=compact_eq))
                    new_decorators.append(decorator.with_changes(
                        decorator=decorator.decorator.with_changes(args=args)
                    ))
                else:
                    new_decorators.append(decorator)
                found: bool = True
            else:
                new_decorators.append(decorator)

        if found:
            return node.with_changes(decorators=new_decorators)
        return node


class DomainImmutabilityTransformer(FreezeDataclassTransformer):
    """Transformer to enforce immutability in Domain layer classes."""

    def __init__(self, context: dict) -> None:
        super().__init__({"class_name": None})
        self.file_path = context.get("file_path", "")

    def leave_ClassDef(self, original_node: cst.ClassDef, updated_node: cst.ClassDef) -> cst.ClassDef:
         # Simplified: Assuming ApplyFixesUseCase filtered the file_path to be in Domain
         return super().leave_ClassDef(original_node, updated_node)


class AddReturnTypeTransformer(cst.CSTTransformer):
    """Transformer to add return type annotations to functions."""

    def __init__(self, context: dict) -> None:
        self.function_name = context.get("function_name")
        self.return_type = context.get("return_type")

    def leave_FunctionDef(self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef) -> cst.FunctionDef:
        if original_node.name.value == self.function_name:
            if not original_node.returns:
                return updated_node.with_changes(
                    returns=cst.Annotation(annotation=cst.Name(self.return_type))
                )
        return updated_node


class AddParameterTypeTransformer(cst.CSTTransformer):
    """Transformer to add parameter type annotations."""

    def __init__(self, context: dict) -> None:
        self.function_name = context.get("function_name")
        self.param_name = context.get("param_name")
        self.param_type = context.get("param_type")

    def leave_FunctionDef(self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef) -> cst.FunctionDef:
        if original_node.name.value == self.function_name:
            new_params_list = []
            modified: bool = False

            # Handle default parameters (params.params)
            for param in updated_node.params.params:
                if param.name.value == self.param_name and not param.annotation:
                    new_param = param.with_changes(
                        annotation=cst.Annotation(
                            annotation=cst.Name(self.param_type),
                            whitespace_before_indicator=cst.SimpleWhitespace("")
                        )
                    )
                    new_params_list.append(new_param)
                    modified: bool = True
                else:
                    new_params_list.append(param)

            if modified:
                 new_params = updated_node.params.with_changes(params=new_params_list)
                 return updated_node.with_changes(params=new_params)

        return updated_node


class LifecycleReturnTypeTransformer(cst.CSTTransformer):
    """Transformer to add None return type to lifecycle methods."""

    def __init__(self, context: dict) -> None:
        pass

    def leave_FunctionDef(self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef) -> cst.FunctionDef:
        name = original_node.name.value
        if name in ("__init__", "setUp", "tearDown") or name.startswith("test_"):
             if not original_node.returns:
                 return updated_node.with_changes(
                     returns=cst.Annotation(
                         annotation=cst.Name("None"),
                         whitespace_before_indicator=cst.SimpleWhitespace(" ")
                     )
                 )
        return updated_node


class DeterministicTypeHintsTransformer(cst.CSTTransformer):
    """Enforce type hints on literals (e.g. x = "foo" -> x: str = "foo")."""

    def __init__(self, context: dict) -> None:
        pass

    def leave_Assign(self, original_node: cst.Assign, updated_node: cst.Assign) -> cst.Assign:
        if len(updated_node.targets) == 1 and isinstance(updated_node.targets[0], cst.AssignTarget):
            # Check if annotation exists? cst.Assign doesn't have annotation directly?
            # AssignTarget(target=Name(..)) -> AnnAssign is different node type.
            # If it's Assign, it lacks annotation. AnnAssign is separate.
            # So if we visit Assign, it's definitely unannotated.

            target = updated_node.targets[0]
            val = updated_node.value

            annot: Optional[str] = None
            if isinstance(val, cst.SimpleString):
                annot: str = "str"
            elif isinstance(val, cst.Integer):
                annot: str = "int"
            elif isinstance(val, cst.Name) and val.value in ("True", "False"):
                annot: str = "bool"

            if annot and isinstance(target.target, cst.Name):
                # Convert Assign to AnnAssign
                return cst.AnnAssign(
                    target=target.target,
                    annotation=cst.Annotation(
                        annotation=cst.Name(annot),
                        whitespace_before_indicator=cst.SimpleWhitespace("")
                    ),
                    value=val,
                    equal=cst.AssignEqual(
                        whitespace_before=cst.SimpleWhitespace(" "),
                        whitespace_after=cst.SimpleWhitespace(" ")
                    )
                )  # type: ignore
        return updated_node


class TypeIntegrityTransformer(cst.CSTTransformer):
    """Auto-import common typing missing imports."""

    def __init__(self, context: dict) -> None:
        self.used_types: Set[str] = set()
        self.existing_typing_imports: Set[str] = set()
        self.typing_aliases = {"List", "Dict", "Optional", "Any", "Union", "Iterable", "Callable"}

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        if isinstance(node.module, cst.Name) and node.module.value == "typing":
            if isinstance(node.names, cst.ImportStar):
                return  # Can't know
            for alias in node.names:
                if isinstance(alias.name, cst.Name):
                    self.existing_typing_imports.add(alias.name.value)

    def visit_Annotation(self, node: cst.Annotation) -> None:
        # Check annotation name
        if isinstance(node.annotation, cst.Name):
            if node.annotation.value in self.typing_aliases:
                self.used_types.add(node.annotation.value)
        # Check Subscript (List[str])
        if isinstance(node.annotation, cst.Subscript):
             if isinstance(node.annotation.value, cst.Name):
                 if node.annotation.value.value in self.typing_aliases:
                     self.used_types.add(node.annotation.value.value)

    def leave_Module(self, original_node: cst.Module, updated_node: cst.Module) -> cst.Module:
        missing = self.used_types - self.existing_typing_imports
        if missing:
            _ = [cst.ImportAlias(name=cst.Name(n)) for n in sorted(missing)]  # Prepared for import merging
            # Check if we should merge with existing 'from typing import ...'
            # For simplicity, add new import statement (libcst ensures valid python, but might duplicate lines)
            # A smart implementation would find existing import and append.
            # I will prepend a new import line for simplicity as 'clean enough' for Turn 2.

            import_stmt = cst.ImportFrom(
                module=cst.Name("typing"),
                names=[cst.ImportAlias(name=cst.Name(n)) for n in sorted(missing)],
                whitespace_after_import=cst.SimpleWhitespace(" ")
            )

            new_body = list(updated_node.body)
            insert_idx: int = 0
            for i, stmt in enumerate(new_body):
                if isinstance(stmt, (cst.Import, cst.ImportFrom)):
                    insert_idx = i + 1
            new_body.insert(insert_idx, cst.SimpleStatementLine(body=[import_stmt]))
            return updated_node.with_changes(body=new_body)

        return updated_node


class LawOfDemeterTransformer(cst.CSTTransformer):
    """
    Transformer to fix Law of Demeter violations by breaking chains.
    
    For a violation like obj.a.b.c(), the transformer:
    1. Identifies the "Stranger" access (obj.a)
    2. Extracts the intermediate call into a local variable (e.g., _tmp = obj.a)
    3. Replaces the original chain with the local variable (e.g., _tmp.b.c())
    """

    def __init__(self, context: dict) -> None:
        # context contains: violation_line, chain_parts, existing_names
        self.target_line = context.get("line", -1)
        self.chain_parts = context.get("chain_parts", [])  # e.g., ["obj", "a", "b", "c"]
        self.existing_names = set(context.get("existing_names", []))
        self._local_var_counter = 0
        self._inserted_assignments: List[tuple[int, cst.SimpleStatementLine]] = []
        self._call_replacements: dict[int, cst.Call] = {}

    def _generate_unique_var_name(self) -> str:
        """Generate a unique temporary variable name."""
        while True:
            var_name = f"_tmp_{self._local_var_counter}"
            self._local_var_counter += 1
            if var_name not in self.existing_names:
                self.existing_names.add(var_name)
                return var_name

    def leave_SimpleStatementLine(
        self, original_node: cst.SimpleStatementLine, updated_node: cst.SimpleStatementLine
    ) -> cst.SimpleStatementLine:
        """Fix Law of Demeter violations in simple statement lines."""
        if self.target_line < 0 or len(self.chain_parts) < 2:
            return updated_node

        # Check if this statement contains our target call
        new_body = []
        inserted_before = False

        for item in updated_node.body:
            if isinstance(item, cst.Expr) and isinstance(item.value, cst.Call):
                call = item.value
                if self._is_target_call(call):
                    # Extract intermediate: obj.a from obj.a.b.c()
                    intermediate_expr = self._extract_intermediate(call.func)
                    if intermediate_expr:
                        var_name = self._generate_unique_var_name()
                        # Create assignment statement
                        assign = cst.Assign(
                            targets=[cst.AssignTarget(target=cst.Name(var_name))],
                            value=intermediate_expr
                        )
                        # Insert assignment before the expression
                        if not inserted_before:
                            new_body.append(assign)
                            inserted_before = True
                        # Replace call with simplified version
                        replacement = self._build_replacement_call(var_name, call)
                        new_body.append(cst.Expr(value=replacement))
                        continue
            new_body.append(item)

        if inserted_before:
            return updated_node.with_changes(body=new_body)
        return updated_node

    def _is_target_call(self, call: cst.Call) -> bool:
        """Check if this call matches our target violation."""
        # For now, check if it's an attribute chain with enough parts
        if not isinstance(call.func, cst.Attribute):
            return False
        # Count attribute depth
        depth = 0
        current = call.func
        while isinstance(current, cst.Attribute):
            depth += 1
            current = current.value
        # Need at least 2 levels (obj.a.b)
        return depth >= 2

    def _extract_intermediate(self, attr: cst.Attribute) -> Optional[cst.BaseExpression]:
        """Extract the first two levels of attribute access (obj.a)."""
        if not isinstance(attr, cst.Attribute):
            return None
        # Get the value (obj) and the first attribute (a)
        if isinstance(attr.value, (cst.Name, cst.Attribute)):
            # Return obj.a
            return attr
        return None

    def _build_replacement_call(self, var_name: str, original_call: cst.Call) -> cst.Call:
        """Build replacement call using temporary variable."""
        if not isinstance(original_call.func, cst.Attribute):
            return original_call

        # Count how many attribute levels we need to skip (first 2: obj.a)
        # Then build the rest: _tmp.b.c()
        attr_chain = original_call.func
        remaining_attrs = []
        current = attr_chain
        skip = 2  # Skip obj.a

        while isinstance(current, cst.Attribute) and skip > 0:
            if skip == 1:
                # This is the last one to skip, collect the rest
                remaining_attrs.append(current.attr)
            current = current.value
            skip -= 1

        # Build new call starting from var_name
        func_expr: cst.BaseExpression = cst.Name(var_name)
        for attr in reversed(remaining_attrs):
            func_expr = cst.Attribute(value=func_expr, attr=attr)

        return original_call.with_changes(func=func_expr)
