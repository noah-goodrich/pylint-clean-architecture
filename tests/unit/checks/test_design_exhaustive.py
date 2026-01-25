import unittest
from unittest.mock import MagicMock

import astroid.nodes

from clean_architecture_linter.checks.design import DesignChecker
from clean_architecture_linter.layer_registry import LayerRegistry
from tests.unit.checker_test_utils import CheckerTestCase


class TestDesignCheckerExhaustive(unittest.TestCase, CheckerTestCase):
    def setUp(self) -> None:
        self.linter = MagicMock()
        self.gateway = MagicMock()
        self.checker = DesignChecker(self.linter, ast_gateway=self.gateway)
        self.checker.open() # Load config

    def test_visit_return_naked_return_raw_type(self) -> None:
        """W9007: Return of raw type triggers violation."""
        # Setup Return node
        node = create_strict_mock(astroid.nodes.Return)
        val_node = create_strict_mock(astroid.nodes.Name)
        node.value = val_node

        # Mock infer/gateway
        # _get_inferred_type_name uses gateway
        self.gateway.get_node_return_type_qname.return_value = "sqlalchemy.orm.Session"

        # Session is in raw_types (default)
        self.checker.visit_return(node)

        self.assertAddsMessage(self.checker, "naked-return-violation", node=node)

    def test_visit_assign_missing_abstraction(self) -> None:
        """W9009: Assigning infrastructure object in UseCase."""
        # Setup Assign node
        node = create_strict_mock(astroid.nodes.Assign)
        target = create_strict_mock(astroid.nodes.Name)
        target.as_string.return_value = "repo"
        node.targets = [target]
        node.value = create_strict_mock(astroid.nodes.Call)

        # Mock layer context (UseCase)
        self.checker.config_loader.get_layer_for_module = MagicMock(return_value=LayerRegistry.LAYER_USE_CASE)
        mock_root = MagicMock()
        mock_root.file = "src/use_cases/create_user.py"
        mock_root.name = "use_cases.create_user"
        node.root.return_value = mock_root

        # Mock inference -> "boto3.client" (infra)
        mock_inf = MagicMock()
        mock_inf.name = "Client"
        mock_inf.root.return_value.name = "boto3"
        node.value.infer.return_value = iter([mock_inf])

        # Ensure boto3 is in infrastructure_modules
        self.checker.visit_assign(node)

        self.assertAddsMessage(self.checker, "missing-abstraction-violation", node=node)

    def test_defensive_none_check_in_domain(self) -> None:
        """W9012: Defensive None check in Domain layer."""
        # if x is None: raise ValueError
        node = create_strict_mock(astroid.nodes.If)

        # Context -> Domain
        self.checker.config_loader.get_layer_for_module = MagicMock(return_value=LayerRegistry.LAYER_DOMAIN)
        mock_root = MagicMock()
        mock_root.name = "domain.logic"
        node.root.return_value = mock_root

        # Test condition: x is None
        compare = create_strict_mock(astroid.nodes.Compare)
        compare.ops = [("is", create_strict_mock(astroid.nodes.Const, value=None))]
        compare.left = create_strict_mock(astroid.nodes.Name, name="x")
        node.test = compare

        # Body: raise
        node.body = [create_strict_mock(astroid.nodes.Raise)]

        self.checker.visit_if(node)
        self.assertAddsMessage(self.checker, "defensive-none-check", node=node)

    def test_any_in_signature_recursive(self) -> None:
        """W9016: Explicit 'Any' in generic aliases."""
        # def foo(x: List[Any]) -> None: ...
        node = create_strict_mock(astroid.nodes.FunctionDef)
        node.name = "foo"
        node.returns = None

        # Args with annotations
        args = MagicMock()
        args.args = [create_strict_mock(astroid.nodes.Name, name="x")]

        # List[Any] -> Subscript(value=List, slice=Any)
        # We simulate the AST structure
        subscript = create_strict_mock(astroid.nodes.Subscript)
        subscript.slice = create_strict_mock(astroid.nodes.Name, name="Any")
        subscript.value = MagicMock() # Required attribute
        # Subscript.value can be anything normally, we recurse on slice

        args.annotations = [subscript]
        node.args = args

        self.checker.visit_functiondef(node)
        # Warning is on the slice (the 'Any' part), not the subscript itself
        self.assertAddsMessage(self.checker, "banned-any-usage", node=subscript.slice)

def create_strict_mock(spec_cls, **attrs):
    """Helper duplicate."""
    m = MagicMock(spec=spec_cls)
    for k, v in attrs.items():
        setattr(m, k, v)
    return m
