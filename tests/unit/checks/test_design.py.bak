import unittest
from unittest.mock import MagicMock

import astroid.nodes

from clean_architecture_linter.checks.design import DesignChecker
from tests.unit.checker_test_utils import CheckerTestCase, create_mock_node


class TestDesignChecker(unittest.TestCase, CheckerTestCase):
    def setUp(self):
        self.linter = MagicMock()
        self.ast_gateway = MagicMock()
        self.checker = DesignChecker(self.linter, self.ast_gateway)

    def test_banned_any_in_signature(self):
        # def foo(x: Any) -> None: ...
        # Use real astroid parse to get proper isinstance behavior
        code = "def foo(x: Any) -> None: pass"
        import astroid
        module = astroid.parse(code)
        node = list(module.nodes_of_class(astroid.nodes.FunctionDef))[0]

        self.checker.visit_functiondef(node)

        # The annotation node for 'x' should trigger banned-any-usage
        self.assertAddsMessage(self.checker, "banned-any-usage", args=("parameter 'x'",))

    def test_naked_return_io(self):
        # return session.query() -> inferred as 'Cursor' (which is in default raw_types)

        node = create_mock_node(astroid.nodes.Return)
        val_node = create_mock_node(astroid.nodes.Call)
        node.value = val_node

        # Mock gateway response
        self.ast_gateway.get_node_return_type_qname.return_value = "sqlalchemy.Cursor"

        self.checker.visit_return(node)

        # 'Cursor' is in defaults
        self.assertAddsMessage(self.checker, "naked-return-violation", node, args=("Cursor",))

    def test_missing_type_hint_return(self):
        node = create_mock_node(astroid.nodes.FunctionDef, name="foo")
        node.returns = None
        # Valid args to skip param checks for this specific test
        node.args = create_mock_node(astroid.nodes.Arguments)
        node.args.args = []
        node.args.annotations = []
        node.args.vararg = None
        node.args.kwarg = None

        self.checker.visit_functiondef(node)

        self.assertAddsMessage(self.checker, "missing-type-hint", node, args=("return type", "foo"))
