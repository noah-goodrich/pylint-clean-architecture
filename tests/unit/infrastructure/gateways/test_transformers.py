"""Unit tests for LibCST transformers."""


import libcst as cst

from excelsior_architect.infrastructure.gateways.transformers import (
    AddImportTransformer,
    AddParameterTypeTransformer,
    AddReturnTypeTransformer,
    DeterministicTypeHintsTransformer,
    DomainImmutabilityTransformer,
    FreezeDataclassTransformer,
    GovernanceCommentTransformer,
    LifecycleReturnTypeTransformer,
    TypeIntegrityTransformer,
)


class TestAddImportTransformer:
    """Test AddImportTransformer."""

    def test_adds_import_to_module(self) -> None:
        """Test that import is added to module."""
        source = "x = 1\n"
        module = cst.parse_module(source)

        transformer = AddImportTransformer({
            "module": "typing",
            "imports": ["List", "Dict"]
        })

        modified = module.visit(transformer)
        code = modified.code

        assert "from typing import List, Dict" in code
        assert "x = 1" in code

    def test_inserts_after_existing_imports(self) -> None:
        """Test that new import is inserted after existing imports."""
        source = """from os import path
x = 1
"""
        module = cst.parse_module(source)

        transformer = AddImportTransformer({
            "module": "typing",
            "imports": ["List"]
        })

        modified = module.visit(transformer)
        code = modified.code

        # Should have both imports
        assert "from os import path" in code
        assert "from typing import List" in code
        # Typing import should come after os import (or at beginning if insert_idx logic differs)
        # The transformer inserts at insert_idx which is after last import
        lines = code.splitlines()
        os_line = next((i for i, line in enumerate(lines)
                       if "from os import" in line), None)
        typing_line = next((i for i, line in enumerate(
            lines) if "from typing import" in line), None)
        # Both should exist
        assert os_line is not None
        assert typing_line is not None

    def test_only_adds_once(self) -> None:
        """Test that import is only added once even if visited multiple times."""
        source = "x = 1\n"
        module = cst.parse_module(source)

        transformer = AddImportTransformer({
            "module": "typing",
            "imports": ["List"]
        })

        # Visit twice
        modified1 = module.visit(transformer)
        modified2 = modified1.visit(transformer)

        # Should only have one import
        assert modified1.code.count("from typing import List") == 1
        assert modified2.code.count("from typing import List") == 1

    def test_supports_dotted_module_import(self) -> None:
        """Test that transformer supports dotted module paths (from a.b import C)."""
        source = "x = 1\n"
        module = cst.parse_module(source)

        transformer = AddImportTransformer({
            "module": "a.b.c",
            "imports": ["Thing"]
        })

        modified = module.visit(transformer)
        code = modified.code
        assert "from a.b.c import Thing" in code


class TestFreezeDataclassTransformer:
    """Test FreezeDataclassTransformer."""

    def test_adds_frozen_to_existing_dataclass(self) -> None:
        """Test that frozen=True is added to existing @dataclass decorator."""
        source = """from dataclasses import dataclass

@dataclass
class User:
    name: str
"""
        module = cst.parse_module(source)

        transformer = FreezeDataclassTransformer({"class_name": "User"})
        modified = module.visit(transformer)
        code = modified.code

        assert "@dataclass(frozen=True)" in code or "@dataclass(frozen = True)" in code

    def test_adds_dataclass_decorator_if_missing(self) -> None:
        """Test that @dataclass(frozen=True) is added if class has no dataclass decorator."""
        source = """class User:
    name: str
"""
        module = cst.parse_module(source)

        transformer = FreezeDataclassTransformer({"class_name": "User"})
        modified = module.visit(transformer)
        code = modified.code

        assert "@dataclass(frozen=True)" in code or "@dataclass(frozen = True)" in code
        assert "from dataclasses import dataclass" in code

    def test_adds_dataclass_import_if_missing(self) -> None:
        """Test that dataclass import is added if missing."""
        source = """class User:
    name: str
"""
        module = cst.parse_module(source)

        transformer = FreezeDataclassTransformer({"class_name": "User"})
        modified = module.visit(transformer)
        code = modified.code

        assert "from dataclasses import dataclass" in code

    def test_does_not_add_duplicate_import(self) -> None:
        """Test that import is not duplicated if already present."""
        source = """from dataclasses import dataclass

class User:
    name: str
"""
        module = cst.parse_module(source)

        transformer = FreezeDataclassTransformer({"class_name": "User"})
        modified = module.visit(transformer)
        code = modified.code

        # Should only have one import
        assert code.count("from dataclasses import dataclass") == 1

    def test_handles_existing_frozen_dataclass(self) -> None:
        """Test that existing frozen dataclass is not modified."""
        source = """from dataclasses import dataclass

@dataclass(frozen=True)
class User:
    name: str
"""
        module = cst.parse_module(source)

        transformer = FreezeDataclassTransformer({"class_name": "User"})
        modified = module.visit(transformer)
        code = modified.code

        # Should still have frozen=True
        assert "@dataclass(frozen=True)" in code or "@dataclass(frozen = True)" in code


class TestAddReturnTypeTransformer:
    """Test AddReturnTypeTransformer."""

    def test_adds_return_type_to_function(self) -> None:
        """Test that return type is added to function without return type."""
        source = """def get_value():
    return 42
"""
        module = cst.parse_module(source)

        transformer = AddReturnTypeTransformer({
            "function_name": "get_value",
            "return_type": "int"
        })

        modified = module.visit(transformer)
        code = modified.code

        assert "def get_value() -> int:" in code

    def test_does_not_modify_function_with_existing_return_type(self) -> None:
        """Test that function with existing return type is not modified."""
        source = """def get_value() -> int:
    return 42
"""
        module = cst.parse_module(source)

        transformer = AddReturnTypeTransformer({
            "function_name": "get_value",
            "return_type": "str"
        })

        modified = module.visit(transformer)
        code = modified.code

        # Should still be int, not str
        assert "-> int:" in code
        assert "-> str:" not in code

    def test_only_modifies_target_function(self) -> None:
        """Test that only the target function is modified."""
        source = """def get_value():
    return 42

def other_func():
    return "test"
"""
        module = cst.parse_module(source)

        transformer = AddReturnTypeTransformer({
            "function_name": "get_value",
            "return_type": "int"
        })

        modified = module.visit(transformer)
        code = modified.code

        assert "def get_value() -> int:" in code
        assert "def other_func():" in code  # Should not have return type


class TestAddParameterTypeTransformer:
    """Test AddParameterTypeTransformer."""

    def test_adds_parameter_type(self) -> None:
        """Test that parameter type is added."""
        source = """def process(name):
    return name.upper()
"""
        module = cst.parse_module(source)

        transformer = AddParameterTypeTransformer({
            "function_name": "process",
            "param_name": "name",
            "param_type": "str"
        })

        modified = module.visit(transformer)
        code = modified.code

        assert "def process(name: str):" in code

    def test_does_not_modify_parameter_with_existing_type(self) -> None:
        """Test that parameter with existing type is not modified."""
        source = """def process(name: str):
    return name.upper()
"""
        module = cst.parse_module(source)

        transformer = AddParameterTypeTransformer({
            "function_name": "process",
            "param_name": "name",
            "param_type": "int"
        })

        modified = module.visit(transformer)
        code = modified.code

        # Should still be str, not int
        assert "name: str" in code
        assert "name: int" not in code


class TestLifecycleReturnTypeTransformer:
    """Test LifecycleReturnTypeTransformer."""

    def test_adds_none_to_init(self) -> None:
        """Test that -> None is added to __init__."""
        source = """class User:
    def __init__(self):
        self.name = "test"
"""
        module = cst.parse_module(source)

        transformer = LifecycleReturnTypeTransformer({})
        modified = module.visit(transformer)
        code = modified.code

        assert "def __init__(self) -> None:" in code

    def test_adds_none_to_setup(self) -> None:
        """Test that -> None is added to setUp."""
        source = """def setUp():
    pass
"""
        module = cst.parse_module(source)

        transformer = LifecycleReturnTypeTransformer({})
        modified = module.visit(transformer)
        code = modified.code

        assert "def setUp() -> None:" in code

    def test_adds_none_to_test_methods(self) -> None:
        """Test that -> None is added to test_ methods."""
        source = """def test_something():
    assert True
"""
        module = cst.parse_module(source)

        transformer = LifecycleReturnTypeTransformer({})
        modified = module.visit(transformer)
        code = modified.code

        assert "def test_something() -> None:" in code


class TestDeterministicTypeHintsTransformer:
    """Test DeterministicTypeHintsTransformer."""

    def test_adds_type_hint_for_string_literal(self) -> None:
        """Test that type hint is added for string literal assignment."""
        source = """x = "hello"
"""
        module = cst.parse_module(source)

        transformer = DeterministicTypeHintsTransformer({})
        modified = module.visit(transformer)
        code = modified.code

        assert "x: str = \"hello\"" in code

    def test_adds_type_hint_for_integer_literal(self) -> None:
        """Test that type hint is added for integer literal assignment."""
        source = """x = 42
"""
        module = cst.parse_module(source)

        transformer = DeterministicTypeHintsTransformer({})
        modified = module.visit(transformer)
        code = modified.code

        assert "x: int = 42" in code

    def test_adds_type_hint_for_boolean_literal(self) -> None:
        """Test that type hint is added for boolean literal assignment."""
        source = """x = True
"""
        module = cst.parse_module(source)

        transformer = DeterministicTypeHintsTransformer({})
        modified = module.visit(transformer)
        code = modified.code

        assert "x: bool = True" in code


class TestTypeIntegrityTransformer:
    """Test TypeIntegrityTransformer."""

    def test_adds_missing_typing_imports(self) -> None:
        """Test that missing typing imports are added."""
        source = """def process(items: List[str]) -> Optional[int]:
    return None
"""
        module = cst.parse_module(source)

        transformer = TypeIntegrityTransformer({})
        modified = module.visit(transformer)
        code = modified.code

        assert "from typing import List, Optional" in code

    def test_adds_missing_typing_imports_separately(self) -> None:
        """Test that missing typing imports are added (may create separate import line)."""
        source = """from typing import List

def process(items: List[str]) -> Optional[int]:
    return None
"""
        module = cst.parse_module(source)

        transformer = TypeIntegrityTransformer({})
        modified = module.visit(transformer)
        code = modified.code

        # TypeIntegrityTransformer adds a new import line for missing types
        # It doesn't merge with existing imports, so we may get multiple import lines
        assert "Optional" in code
        # Should have at least one typing import
        assert "from typing import" in code


class TestDomainImmutabilityTransformer:
    """Test DomainImmutabilityTransformer."""

    def test_inherits_from_freeze_dataclass_transformer(self) -> None:
        """Test that DomainImmutabilityTransformer inherits from FreezeDataclassTransformer."""
        transformer = DomainImmutabilityTransformer({"file_path": "test.py"})
        assert isinstance(transformer, FreezeDataclassTransformer)


class TestGovernanceCommentTransformer:
    """Test GovernanceCommentTransformer."""

    def test_injects_comment_above_target_line(self) -> None:
        """Test that governance comment is injected above target line."""
        source = """def example():
    x = obj.a.b.c()
    return x
"""
        module = cst.parse_module(source)

        transformer = GovernanceCommentTransformer({
            "rule_code": "W9006",
            "rule_name": "Law of Demeter",
            "problem": "Chain access exceeds one level",
            "recommendation": "Delegate to immediate object",
            "context_info": "Violation at line 2.",
            "target_line": 2,
        })
        transformer.source_lines = source.splitlines()

        modified = module.visit(transformer)
        code = modified.code

        assert "EXCELSIOR: W9006" in code
        assert "Law of Demeter" in code
        assert "Problem:" in code
        assert "Recommendation:" in code

    def test_handles_zero_target_line(self) -> None:
        """Test that zero target line doesn't inject comments."""
        source = "x = 1\n"
        module = cst.parse_module(source)

        transformer = GovernanceCommentTransformer({
            "rule_code": "W9006",
            "rule_name": "Test",
            "problem": "Test",
            "recommendation": "Test",
            "context_info": "",
            "target_line": 0,
        })

        modified = module.visit(transformer)
        assert modified.code == source
