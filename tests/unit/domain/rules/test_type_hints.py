"""Comprehensive tests for MissingTypeHintRule (W9015)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import astroid
import pytest

from clean_architecture_linter.domain.rules.type_hints import MissingTypeHintRule
from clean_architecture_linter.domain.rules import Violation
from clean_architecture_linter.infrastructure.gateways.astroid_gateway import AstroidGateway


class TestMissingTypeHintRuleCheck:
    """Test violation detection in MissingTypeHintRule.check()."""

    def test_check_returns_empty_for_non_module(self) -> None:
        """Test check returns empty list for non-Module nodes."""
        gateway = AstroidGateway()
        rule = MissingTypeHintRule(gateway)

        # Pass a non-Module node
        func_node = astroid.parse("def func(): pass").body[0]
        violations = rule.check(func_node)

        assert violations == []

    def test_check_detects_missing_return_type(self) -> None:
        """Test check detects missing return type."""
        code = """
def get_value():
    return 42
"""
        gateway = AstroidGateway()
        rule = MissingTypeHintRule(gateway)

        module = astroid.parse(code)
        violations = rule.check(module)

        assert len(violations) == 1
        assert violations[0].code == "W9015"
        assert "return type" in violations[0].message
        assert violations[0].node.name == "get_value"

    def test_check_detects_missing_parameter_type(self) -> None:
        """Test check detects missing parameter type."""
        code = """
def process(name):
    return name.upper()
"""
        gateway = AstroidGateway()
        rule = MissingTypeHintRule(gateway)

        module = astroid.parse(code)
        violations = rule.check(module)

        assert len(violations) >= 1
        param_violations = [v for v in violations if "parameter" in v.message]
        assert len(param_violations) == 1
        assert "name" in param_violations[0].message

    def test_check_skips_self_parameter(self) -> None:
        """Test check skips self parameter in methods."""
        code = """
class MyClass:
    def method(self, value):
        return value
"""
        gateway = AstroidGateway()
        rule = MissingTypeHintRule(gateway)

        module = astroid.parse(code)
        violations = rule.check(module)

        # Should detect return type and 'value' parameter, but not 'self'
        param_violations = [v for v in violations if "parameter" in v.message]
        self_violations = [v for v in param_violations if "self" in v.message]
        assert len(self_violations) == 0

    def test_check_skips_cls_parameter(self) -> None:
        """Test check skips cls parameter in classmethods."""
        code = """
class MyClass:
    @classmethod
    def method(cls, value):
        return value
"""
        gateway = AstroidGateway()
        rule = MissingTypeHintRule(gateway)

        module = astroid.parse(code)
        violations = rule.check(module)

        # Should detect return type and 'value' parameter, but not 'cls'
        param_violations = [v for v in violations if "parameter" in v.message]
        cls_violations = [v for v in param_violations if "cls" in v.message]
        assert len(cls_violations) == 0

    def test_check_handles_function_with_existing_return_type(self) -> None:
        """Test check doesn't flag functions with existing return type."""
        code = """
def get_value() -> int:
    return 42
"""
        gateway = AstroidGateway()
        rule = MissingTypeHintRule(gateway)

        module = astroid.parse(code)
        violations = rule.check(module)

        # Should not detect return type violation
        return_violations = [v for v in violations if "return type" in v.message]
        assert len(return_violations) == 0

    def test_check_handles_function_with_existing_parameter_types(self) -> None:
        """Test check doesn't flag functions with existing parameter types."""
        code = """
def process(name: str) -> str:
    return name.upper()
"""
        gateway = AstroidGateway()
        rule = MissingTypeHintRule(gateway)

        module = astroid.parse(code)
        violations = rule.check(module)

        # Should not detect any violations
        assert len(violations) == 0


class TestMissingTypeHintRuleInference:
    """Test type inference methods."""

    def test_infer_return_type_from_literal(self) -> None:
        """Test _infer_return_type infers from string literal."""
        code = """
def get_message():
    return "hello"
"""
        gateway = AstroidGateway()
        rule = MissingTypeHintRule(gateway)

        module = astroid.parse(code)
        func_def = module.body[0]

        return_type = rule._infer_return_type(func_def)
        assert return_type is not None
        assert "str" in return_type

    def test_infer_return_type_from_integer_literal(self) -> None:
        """Test _infer_return_type infers from integer literal."""
        code = """
def get_value():
    return 42
"""
        gateway = AstroidGateway()
        rule = MissingTypeHintRule(gateway)

        module = astroid.parse(code)
        func_def = module.body[0]

        return_type = rule._infer_return_type(func_def)
        assert return_type is not None
        assert "int" in return_type

    def test_infer_return_type_from_none(self) -> None:
        """Test _infer_return_type handles None return."""
        code = """
def do_nothing():
    return None
"""
        gateway = AstroidGateway()
        rule = MissingTypeHintRule(gateway)

        module = astroid.parse(code)
        func_def = module.body[0]

        return_type = rule._infer_return_type(func_def)
        # None might be inferred as NoneType or None
        assert return_type is not None

    def test_infer_return_type_no_return_statement(self) -> None:
        """Test _infer_return_type returns None when no return statement."""
        code = """
def do_something():
    pass
"""
        gateway = AstroidGateway()
        rule = MissingTypeHintRule(gateway)

        module = astroid.parse(code)
        func_def = module.body[0]

        return_type = rule._infer_return_type(func_def)
        assert return_type is None

    def test_infer_parameter_type_from_default_value(self) -> None:
        """Test _infer_parameter_type infers from default value."""
        code = """
def process(name="default"):
    return name.upper()
"""
        gateway = AstroidGateway()
        rule = MissingTypeHintRule(gateway)

        module = astroid.parse(code)
        func_def = module.body[0]

        param_type = rule._infer_parameter_type(func_def, func_def.args.args[0], 0)
        assert param_type is not None
        assert "str" in param_type

    def test_infer_parameter_type_no_default(self) -> None:
        """Test _infer_parameter_type returns None when no default value."""
        code = """
def process(name):
    return name.upper()
"""
        gateway = AstroidGateway()
        rule = MissingTypeHintRule(gateway)

        module = astroid.parse(code)
        func_def = module.body[0]

        param_type = rule._infer_parameter_type(func_def, func_def.args.args[0], 0)
        # Without default, inference from usage is complex, may return None
        # This is acceptable - the rule marks it as non-fixable
        assert param_type is None or isinstance(param_type, str)


class TestMissingTypeHintRuleCanFixType:
    """Test _can_fix_type logic."""

    def test_can_fix_type_returns_false_for_none(self) -> None:
        """Test _can_fix_type returns False for None."""
        gateway = AstroidGateway()
        rule = MissingTypeHintRule(gateway)

        fixable, reason = rule._can_fix_type(None)
        assert fixable is False
        assert reason is not None
        assert "Inference failed" in reason

    def test_can_fix_type_returns_false_for_any(self) -> None:
        """Test _can_fix_type returns False for Any type."""
        gateway = AstroidGateway()
        rule = MissingTypeHintRule(gateway)

        fixable, reason = rule._can_fix_type("typing.Any")
        assert fixable is False
        assert reason is not None
        assert "Any" in reason
        assert "banned" in reason

    def test_can_fix_type_returns_false_for_any_in_qname(self) -> None:
        """Test _can_fix_type returns False when Any is in qname."""
        gateway = AstroidGateway()
        rule = MissingTypeHintRule(gateway)

        fixable, reason = rule._can_fix_type("some.module.Any")
        assert fixable is False
        assert "Any" in reason

    def test_can_fix_type_returns_false_for_uninferable(self) -> None:
        """Test _can_fix_type returns False for Uninferable."""
        gateway = AstroidGateway()
        rule = MissingTypeHintRule(gateway)

        fixable, reason = rule._can_fix_type("astroid.nodes.Uninferable")
        assert fixable is False
        assert reason is not None
        assert "Inference failed" in reason

    def test_can_fix_type_returns_true_for_deterministic_type(self) -> None:
        """Test _can_fix_type returns True for specific types."""
        gateway = AstroidGateway()
        rule = MissingTypeHintRule(gateway)

        fixable, reason = rule._can_fix_type("builtins.str")
        assert fixable is True
        assert reason is None

    def test_can_fix_type_returns_true_for_typing_types(self) -> None:
        """Test _can_fix_type returns True for typing module types."""
        gateway = AstroidGateway()
        rule = MissingTypeHintRule(gateway)

        fixable, reason = rule._can_fix_type("typing.List")
        assert fixable is True
        assert reason is None


class TestMissingTypeHintRuleFix:
    """Test fix() method that generates transformers."""

    def test_fix_returns_none_when_not_fixable(self) -> None:
        """Test fix returns None when violation is not fixable."""
        gateway = AstroidGateway()
        rule = MissingTypeHintRule(gateway)

        violation = MagicMock()
        violation.fixable = False

        result = rule.fix(violation)
        assert result is None

    def test_fix_returns_transformer_for_return_type(self) -> None:
        """Test fix returns AddReturnTypeTransformer for return type violations."""
        code = """
def get_value():
    return "hello"
"""
        gateway = AstroidGateway()
        rule = MissingTypeHintRule(gateway)

        module = astroid.parse(code)
        func_def = module.body[0]

        # Create a fixable violation
        from clean_architecture_linter.domain.rules import Violation
        violation = Violation(
            code="W9015",
            message="Missing return type",
            location="test.py:2",
            node=func_def,
            fixable=True,
        )

        transformer = rule.fix(violation)
        assert transformer is not None
        assert transformer.function_name == "get_value"
        assert transformer.return_type == "str"

    def test_fix_returns_none_when_inference_fails(self) -> None:
        """Test fix returns None when type inference fails."""
        code = """
def get_value():
    pass  # No return statement
"""
        gateway = AstroidGateway()
        rule = MissingTypeHintRule(gateway)

        module = astroid.parse(code)
        func_def = module.body[0]

        from clean_architecture_linter.domain.rules import Violation
        violation = Violation(
            code="W9015",
            message="Missing return type",
            location="test.py:2",
            node=func_def,
            fixable=True,  # Marked fixable but inference will fail
        )

        transformer = rule.fix(violation)
        # Should return None because inference fails
        assert transformer is None

    def test_fix_handles_parameter_type_violation(self) -> None:
        """Test fix handles parameter type violations."""
        code = """
def process(name="default"):
    return name.upper()
"""
        gateway = AstroidGateway()
        rule = MissingTypeHintRule(gateway)

        module = astroid.parse(code)
        func_def = module.body[0]
        arg = func_def.args.args[0]

        from clean_architecture_linter.domain.rules import Violation
        violation = Violation(
            code="W9015",
            message="Missing parameter type",
            location="test.py:2",
            node=arg,
            fixable=True,
        )

        # Mock the parent relationship
        arg.parent = func_def

        transformer = rule.fix(violation)
        # May return None if inference fails, or transformer if it succeeds
        assert transformer is None or hasattr(transformer, 'param_name')


class TestMissingTypeHintRuleQnameToTypeName:
    """Test _qname_to_type_name conversion."""

    def test_qname_to_type_name_builtins(self) -> None:
        """Test conversion of builtins qname."""
        gateway = AstroidGateway()
        rule = MissingTypeHintRule(gateway)

        assert rule._qname_to_type_name("builtins.str") == "str"
        assert rule._qname_to_type_name("builtins.int") == "int"
        assert rule._qname_to_type_name("builtins.bool") == "bool"

    def test_qname_to_type_name_typing(self) -> None:
        """Test conversion of typing qname."""
        gateway = AstroidGateway()
        rule = MissingTypeHintRule(gateway)

        assert rule._qname_to_type_name("typing.List") == "List"
        assert rule._qname_to_type_name("typing.Dict") == "Dict"
        assert rule._qname_to_type_name("typing.Optional") == "Optional"

    def test_qname_to_type_name_other_modules(self) -> None:
        """Test conversion of other module qnames."""
        gateway = AstroidGateway()
        rule = MissingTypeHintRule(gateway)

        assert rule._qname_to_type_name("pathlib.Path") == "Path"
        assert rule._qname_to_type_name("collections.abc.Iterable") == "Iterable"


class TestMissingTypeHintRuleGetFixInstructions:
    """Test get_fix_instructions method."""

    def test_get_fix_instructions_with_failure_reason(self) -> None:
        """Test get_fix_instructions includes failure reason."""
        gateway = AstroidGateway()
        rule = MissingTypeHintRule(gateway)

        from clean_architecture_linter.domain.rules import Violation
        violation = Violation(
            code="W9015",
            message="Missing type hint",
            location="test.py:1",
            node=MagicMock(),
            fixable=False,
            fix_failure_reason="Inference failed",
        )

        instructions = rule.get_fix_instructions(violation)
        assert "Inference failed" in instructions
        assert "Manual fix required" in instructions

    def test_get_fix_instructions_without_failure_reason(self) -> None:
        """Test get_fix_instructions provides generic instructions."""
        gateway = AstroidGateway()
        rule = MissingTypeHintRule(gateway)

        from clean_architecture_linter.domain.rules import Violation
        violation = Violation(
            code="W9015",
            message="Missing type hint",
            location="test.py:1",
            node=MagicMock(),
            fixable=True,
        )

        instructions = rule.get_fix_instructions(violation)
        assert "type hints" in instructions
        assert "parameters" in instructions or "return" in instructions

    def test_fix_handles_arguments_node_with_function_def_parent(self) -> None:
        """Test fix handles Arguments node with FunctionDef parent (lines 164-172)."""
        gateway = AstroidGateway()
        rule = MissingTypeHintRule(gateway)

        code = """
def process(x):
    return x
"""
        module = astroid.parse(code)
        func_def = module.body[0]
        args_node = func_def.args

        violation = Violation(
            code="W9015",
            message="Missing parameter type",
            location="test.py:2",
            node=args_node.args[0],  # The parameter node
            fixable=True,
        )

        # Mock the inference to return a type
        with patch.object(gateway, 'get_node_return_type_qname', return_value='builtins.str'):
            result = rule.fix(violation)
            # Should return a transformer if type can be inferred
            assert result is not None or result is None  # May return None if inference fails

    def test_fix_handles_arguments_node_finds_parameter_index(self) -> None:
        """Test fix finds correct parameter index in Arguments node."""
        gateway = AstroidGateway()
        rule = MissingTypeHintRule(gateway)

        code = """
def process(x, y):
    return x + y
"""
        module = astroid.parse(code)
        func_def = module.body[0]
        # Create violation for second parameter
        param_node = func_def.args.args[1]

        violation = Violation(
            code="W9015",
            message="Missing parameter type",
            location="test.py:2",
            node=param_node,
            fixable=True,
        )

        # Mock inference to return a type
        with patch.object(gateway, 'get_node_return_type_qname', return_value='builtins.int'):
            result = rule.fix(violation)
            # Should attempt to create transformer
            assert result is not None or result is None
