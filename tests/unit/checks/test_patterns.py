import unittest
from unittest.mock import MagicMock

import astroid.nodes

from excelsior_architect.domain.config import ConfigurationLoader
from excelsior_architect.use_cases.checks.patterns import CouplingChecker, PatternChecker
from tests.unit.checker_test_utils import CheckerTestCase, create_mock_node


class TestCouplingChecker(unittest.TestCase, CheckerTestCase):
    def setUp(self) -> None:
        self.linter = MagicMock()
        self.ast_gateway = MagicMock()
        self.python_gateway = MagicMock()
        stub_resolver = MagicMock()
        stub_resolver.get_stub_path.return_value = None
        self.config_loader = ConfigurationLoader({}, {})
        self.checker = CouplingChecker(
            self.linter,
            self.ast_gateway,
            self.python_gateway,
            stub_resolver=stub_resolver,
            config_loader=self.config_loader,
            registry={},
        )

    def test_demeter_violation_chain(self) -> None:
        # a.b.c() -> chain length 3 (a, b, c) -> 2 dots. _MIN_CHAIN_LENGTH is 2.
        # Use real astroid parsing to get proper isinstance behavior
        import astroid
        code: str = "result = a.b.c()"
        module = astroid.parse(code)
        call_nodes = list(module.nodes_of_class(astroid.nodes.Call))
        node = call_nodes[0]

        # Avoid exclusions (rule holds logic; mock rule for thin checker)
        self.checker._demeter_rule._is_test_file = MagicMock(
            return_value=False)
        self.checker._demeter_rule._is_chain_excluded = MagicMock(
            return_value=False)

        self.checker.visit_call(node)

        # Expect W9006
        self.assertAddsMessage(self.checker, "W9006", args=("a.b.c",))


class TestPatternChecker(unittest.TestCase, CheckerTestCase):
    def setUp(self) -> None:
        self.linter = MagicMock()
        self.checker = PatternChecker(self.linter, registry={})

    def test_delegation_not_detected_simple(self) -> None:
        # if x: do()
        node = create_mock_node(astroid.nodes.If)
        node.test = create_mock_node(astroid.nodes.Name, name="x")
        node.body = [create_mock_node(astroid.nodes.Expr)]  # mocks call
        node.orelse = []

        # logic: _check_delegation_chain returns depth > 0
        # Here depth is 0. So no message.
        self.checker.visit_if(node)
        self.assertNoMessages(self.checker)

    # TODO: Complex delegation chain test requires mocking recursion logic carefully.
