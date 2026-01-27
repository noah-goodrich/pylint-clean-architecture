"""Unit tests for ImmutabilityChecker (W9601)."""

import unittest
from unittest.mock import MagicMock

import astroid

from clean_architecture_linter.domain.layer_registry import LayerRegistry
from clean_architecture_linter.use_cases.checks.immutability import ImmutabilityChecker
from tests.unit.checker_test_utils import CheckerTestCase, create_mock_node


class TestImmutabilityChecker(unittest.TestCase, CheckerTestCase):
    """Test ImmutabilityChecker visit methods."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.linter = MagicMock()
        self.python_gateway = MagicMock()
        self.checker = ImmutabilityChecker(self.linter, self.python_gateway)
        self.config_loader = self.checker.config_loader

    def test_visit_assignattr_skips_non_domain_layer(self) -> None:
        """Test visit_assignattr skips non-Domain layer."""
        node = create_mock_node(astroid.nodes.AssignAttr)
        self.python_gateway.get_node_layer.return_value = LayerRegistry.LAYER_USE_CASE

        self.checker.visit_assignattr(node)
        self.assertNoMessages(self.checker)

    def test_visit_assignattr_flags_domain_layer_assignment(self) -> None:
        """Test visit_assignattr flags assignment in Domain layer."""
        node = create_mock_node(astroid.nodes.AssignAttr)
        self.python_gateway.get_node_layer.return_value = LayerRegistry.LAYER_DOMAIN
        
        # Mock frame to not be __init__
        frame = create_mock_node(astroid.nodes.FunctionDef, name="some_method")
        node.frame = MagicMock(return_value=frame)

        self.checker.visit_assignattr(node)
        self.assertAddsMessage(
            self.checker, "domain-immutability-violation", node, args=(LayerRegistry.LAYER_DOMAIN,)
        )

    def test_visit_assignattr_skips_init_assignments(self) -> None:
        """Test visit_assignattr skips __init__ assignments."""
        # Create actual code with __init__
        code = """
class MyClass:
    def __init__(self):
        self.value = 1
"""
        module = astroid.parse(code)
        class_def = module.body[0]
        init_func = class_def.body[0]
        assign_attr = init_func.body[0].targets[0]
        
        self.python_gateway.get_node_layer.return_value = LayerRegistry.LAYER_DOMAIN

        self.checker.visit_assignattr(assign_attr)
        self.assertNoMessages(self.checker)

    def test_is_dataclass_name_with_name_node(self) -> None:
        """Test _is_dataclass_name with Name node."""
        # Create actual Name node
        code = "dataclass"
        node = astroid.parse(code).body[0].value
        assert self.checker._is_dataclass_name(node) is True

        code = "not_dataclass"
        node = astroid.parse(code).body[0].value
        assert self.checker._is_dataclass_name(node) is False

    def test_is_dataclass_name_with_attribute_node(self) -> None:
        """Test _is_dataclass_name with Attribute node."""
        # Create actual Attribute node
        code = "typing.dataclass"
        node = astroid.parse(code).body[0].value
        assert self.checker._is_dataclass_name(node) is True

        code = "typing.not_dataclass"
        node = astroid.parse(code).body[0].value
        assert self.checker._is_dataclass_name(node) is False

    def test_is_dataclass_name_with_other_node(self) -> None:
        """Test _is_dataclass_name with other node types."""
        node = create_mock_node(astroid.nodes.Call)
        assert self.checker._is_dataclass_name(node) is False

    def test_dataclass_frozen_from_decorators_finds_dataclass(self) -> None:
        """Test _dataclass_frozen_from_decorators finds @dataclass."""
        code = """
@dataclass
class X:
    pass
"""
        module = astroid.parse(code)
        decorator = module.body[0].decorators.nodes[0]
        is_dataclass, is_frozen = self.checker._dataclass_frozen_from_decorators([decorator])
        assert is_dataclass is True
        assert is_frozen is False

    def test_dataclass_frozen_from_decorators_finds_frozen_true(self) -> None:
        """Test _dataclass_frozen_from_decorators finds frozen=True."""
        code = """
@dataclass(frozen=True)
class X:
    pass
"""
        module = astroid.parse(code)
        decorator = module.body[0].decorators.nodes[0]
        is_dataclass, is_frozen = self.checker._dataclass_frozen_from_decorators([decorator])
        assert is_dataclass is True
        assert is_frozen is True

    def test_dataclass_frozen_from_decorators_finds_frozen_false(self) -> None:
        """Test _dataclass_frozen_from_decorators finds frozen=False."""
        code = """
@dataclass(frozen=False)
class X:
    pass
"""
        module = astroid.parse(code)
        decorator = module.body[0].decorators.nodes[0]
        is_dataclass, is_frozen = self.checker._dataclass_frozen_from_decorators([decorator])
        assert is_dataclass is True
        assert is_frozen is False

    def test_dataclass_frozen_from_decorators_handles_multiple_keywords(self) -> None:
        """Test _dataclass_frozen_from_decorators handles multiple keywords."""
        code = """
@dataclass(order=True, frozen=True)
class X:
    pass
"""
        module = astroid.parse(code)
        decorator = module.body[0].decorators.nodes[0]
        is_dataclass, is_frozen = self.checker._dataclass_frozen_from_decorators([decorator])
        assert is_dataclass is True
        assert is_frozen is True

    def test_visit_classdef_skips_non_domain_layer(self) -> None:
        """Test visit_classdef skips non-Domain layer."""
        node = create_mock_node(astroid.nodes.ClassDef, decorators=None)
        self.python_gateway.get_node_layer.return_value = LayerRegistry.LAYER_USE_CASE

        self.checker.visit_classdef(node)
        self.assertNoMessages(self.checker)

    def test_visit_classdef_skips_no_decorators(self) -> None:
        """Test visit_classdef skips classes without decorators."""
        node = create_mock_node(astroid.nodes.ClassDef, decorators=None)
        self.python_gateway.get_node_layer.return_value = LayerRegistry.LAYER_DOMAIN

        self.checker.visit_classdef(node)
        self.assertNoMessages(self.checker)

    def test_visit_classdef_flags_unfrozen_dataclass(self) -> None:
        """Test visit_classdef flags unfrozen dataclass in Domain layer."""
        # Create actual code with @dataclass
        code = """
@dataclass
class MyClass:
    value: int
"""
        module = astroid.parse(code)
        node = module.body[0]  # ClassDef
        
        self.python_gateway.get_node_layer.return_value = LayerRegistry.LAYER_DOMAIN

        self.checker.visit_classdef(node)
        self.assertAddsMessage(
            self.checker, "domain-immutability-violation", node, args=(LayerRegistry.LAYER_DOMAIN,)
        )

    def test_visit_classdef_skips_frozen_dataclass(self) -> None:
        """Test visit_classdef skips frozen dataclass."""
        # Create actual code with @dataclass(frozen=True)
        code = """
@dataclass(frozen=True)
class MyClass:
    value: int
"""
        module = astroid.parse(code)
        node = module.body[0]  # ClassDef
        
        self.python_gateway.get_node_layer.return_value = LayerRegistry.LAYER_DOMAIN

        self.checker.visit_classdef(node)
        self.assertNoMessages(self.checker)

    def test_dataclass_frozen_from_decorators_handles_attribute_decorator(self) -> None:
        """Test _dataclass_frozen_from_decorators handles Attribute decorator."""
        code = """
@typing.dataclass
class X:
    pass
"""
        module = astroid.parse(code)
        decorator = module.body[0].decorators.nodes[0]
        is_dataclass, is_frozen = self.checker._dataclass_frozen_from_decorators([decorator])
        assert is_dataclass is True
        assert is_frozen is False

    def test_dataclass_frozen_from_decorators_handles_non_const_frozen(self) -> None:
        """Test _dataclass_frozen_from_decorators handles non-Const frozen value."""
        # Create @dataclass(frozen=some_var) - not a Const
        code = """
some_var = True
@dataclass(frozen=some_var)
class X:
    pass
"""
        module = astroid.parse(code)
        decorator = module.body[1].decorators.nodes[0]
        is_dataclass, is_frozen = self.checker._dataclass_frozen_from_decorators([decorator])
        assert is_dataclass is True
        assert is_frozen is False  # Not a Const, so can't determine

    def test_dataclass_frozen_from_decorators_handles_wrong_keyword_name(self) -> None:
        """Test _dataclass_frozen_from_decorators handles wrong keyword name."""
        code = """
@dataclass(order=True)
class X:
    pass
"""
        module = astroid.parse(code)
        decorator = module.body[0].decorators.nodes[0]
        is_dataclass, is_frozen = self.checker._dataclass_frozen_from_decorators([decorator])
        assert is_dataclass is True
        assert is_frozen is False  # Wrong keyword name


if __name__ == "__main__":
    unittest.main()
