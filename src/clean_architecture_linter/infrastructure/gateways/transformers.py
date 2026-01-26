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


class GovernanceCommentTransformer(cst.CSTTransformer):
    """
    Transformer to inject governance directive comments above violation lines.

    These comments provide contextual anchors for both humans and AI (Cursor)
    to understand the architectural issue and recommended fix.

    The comment format is standardized and machine-parseable:
    # EXCELSIOR: [Rule Code] - [Rule Name]
    # Problem: [Specific issue description]
    # Recommendation: [Actionable fix guidance]
    # Context: [Relevant details] (optional)
    """

    def __init__(self, context: dict) -> None:
        self.rule_code = context.get("rule_code", "")
        self.rule_name = context.get("rule_name", "")
        self.problem = context.get("problem", "")
        self.recommendation = context.get("recommendation", "")
        self.context_info = context.get("context_info", "")
        self.target_line = context.get("target_line", 0)
        self.source_lines = context.get("source_lines", [])
        self.applied = False

    def _build_comment_lines(self) -> List[str]:
        """Build the standardized governance comment block."""
        lines = [
            f"# EXCELSIOR: {self.rule_code} - {self.rule_name}",
            f"# Problem: {self.problem}",
            f"# Recommendation: {self.recommendation}",
        ]
        if self.context_info:
            lines.append(f"# Context: {self.context_info}")
        return lines

    def _get_node_line(self, node: cst.CSTNode) -> int:
        """Get the line number for a node by parsing source."""
        if not self.source_lines:
            return 0

        # Use LibCST's position metadata if available
        # Otherwise, estimate based on source code
        try:
            # Try to get position from metadata
            if hasattr(node, "metadata") and node.metadata:
                position = node.metadata.get(cst.metadata.PositionProvider, None)
                if position:
                    return position.start.line
        except Exception:
            pass

        # Fallback: search source lines for node content
        # This is approximate but works for most cases
        node_str = cst.Module(body=[node]).code if isinstance(node, cst.BaseStatement) else ""
        if node_str:
            for i, line in enumerate(self.source_lines, 1):
                if node_str.strip() in line or any(part in line for part in node_str.split()[:3]):
                    return i
        return 0

    def leave_Module(
        self, original_node: cst.Module, updated_node: cst.Module
    ) -> cst.Module:
        """
        Add governance comment before target line in module body.

        We use source line matching to find the correct insertion point.
        """
        if self.applied or self.target_line <= 0:
            return updated_node

        new_body: List[cst.BaseStatement] = []
        comment_lines = self._build_comment_lines()

        # Create comment nodes as EmptyLine nodes with comments
        # LibCST Comment value must include the "#" character (full comment line)
        comment_empty_lines = []
        for line in comment_lines:
            # Ensure line starts with "#" for LibCST
            if not line.startswith("#"):
                line = "# " + line

            comment_empty_lines.append(
                cst.EmptyLine(
                    comment=cst.Comment(value=line),  # Include "#" in value
                    indent=cst.SimpleWhitespace(""),
                )
            )

        # Find the statement at or closest to target_line
        insert_index = -1
        for i, stmt in enumerate(updated_node.body):
            # Get approximate line for this statement
            stmt_line = self._get_node_line(stmt)

            # If we've reached or passed the target line, insert before this statement
            if stmt_line >= self.target_line and insert_index == -1:
                insert_index = i
                break

        # If we didn't find a match, insert at the beginning
        if insert_index == -1:
            insert_index = 0

        # Build new body with comments inserted
        for i, stmt in enumerate(updated_node.body):
            if i == insert_index:
                # Insert comments before this statement
                new_body.extend(comment_empty_lines)
                self.applied = True
            new_body.append(stmt)

        # If we never inserted (empty file or target_line beyond end), append at end
        if not self.applied and updated_node.body:
            new_body = list(updated_node.body) + comment_empty_lines
            self.applied = True
        elif not self.applied:
            # Empty file - just add comments
            new_body = comment_empty_lines
            self.applied = True

        return updated_node.with_changes(body=new_body)
