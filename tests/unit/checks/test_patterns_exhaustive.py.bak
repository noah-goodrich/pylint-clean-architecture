import unittest
from unittest.mock import MagicMock

import astroid.nodes

from clean_architecture_linter.checks.patterns import CouplingChecker, PatternChecker
from tests.unit.checker_test_utils import CheckerTestCase


class TestPatternCheckerExhaustive(unittest.TestCase, CheckerTestCase):
    def setUp(self):
        self.linter = MagicMock()
        self.checker = PatternChecker(self.linter)

    def test_delegation_detected_deep_if(self):
        """W9005: Deep delegation chain (if/elif/elif) detected."""
        # if x: return delegate() elif y: return delegate()
        node = create_strict_mock(astroid.nodes.If)
        node.test = MagicMock() # Required for _is_main_block check

        # Branch 1
        node.body = [self._create_return_call()]

        # orelse needs to be an If (representing elif)
        elif_node = create_strict_mock(astroid.nodes.If)
        elif_node.test = MagicMock()
        elif_node.body = [self._create_return_call()]
        elif_node.orelse = [self._create_return_call()] # Final else -> return call

        node.orelse = [elif_node]

        self.checker.visit_if(node)
        self.assertAddsMessage(self.checker, "clean-arch-delegation", node=node)

    def _create_return_call(self):
        ret = create_strict_mock(astroid.nodes.Return)
        ret.value = create_strict_mock(astroid.nodes.Call)
        return ret

class TestCouplingCheckerExhaustive(unittest.TestCase, CheckerTestCase):
    def setUp(self):
        self.linter = MagicMock()
        self.ast_gateway = MagicMock()
        self.python_gateway = MagicMock()
        self.checker = CouplingChecker(self.linter, ast_gateway=self.ast_gateway, python_gateway=self.python_gateway)
        # Fix mock to avoid "str object has no attribute 'split'" or similar in _check_method_chain/is_test_file
        # Default responses
        self.ast_gateway.is_trusted_authority_call.return_value = False
        self.ast_gateway.is_fluent_call.return_value = False
        self.ast_gateway.is_primitive.return_value = False
        self.python_gateway.is_stdlib_module.return_value = False
        self.python_gateway.is_external_dependency.return_value = False

    def _add_root_mock(self, node):
        root = MagicMock()
        root.file = "src/logic.py"
        root.name = "src.logic"
        node.root.return_value = root
        return node

    def test_visit_call_long_chain_violation(self):
        """W9006: a.b.c() violation."""
        # a.b.c() -> Call(func=Attribute(expr=Attribute(expr=Name(a), attr='b'), attr='c'))
        node = create_strict_mock(astroid.nodes.Call)
        self._add_root_mock(node)

        attr_c = create_strict_mock(astroid.nodes.Attribute)
        attr_c.attrname = "c"

        attr_b = create_strict_mock(astroid.nodes.Attribute)
        attr_b.attrname = "b"

        name_a = create_strict_mock(astroid.nodes.Name)
        name_a.name = "a"

        attr_b.expr = name_a
        attr_c.expr = attr_b
        node.func = attr_c

        # Mock to ensure the chain is not excluded by dynamic logic
        self.checker._is_chain_excluded = MagicMock(return_value=False)

        self.checker.visit_call(node)
        self.assertAddsMessage(self.checker, "clean-arch-demeter", node=node, args=("a.b.c",))

    def test_visit_call_trusted_authority_exclusion(self):
        """W9006: Excluded if Trusted Authority."""
        node = create_strict_mock(astroid.nodes.Call)
        self._add_root_mock(node)

        # Structure: node.func.attrname="c", node.func.expr.attrname="b"
        # Correctly build the chain (attribute -> attribute -> name)
        attr_c = create_strict_mock(astroid.nodes.Attribute)
        attr_c.attrname = "c"

        attr_b = create_strict_mock(astroid.nodes.Attribute)
        attr_b.attrname = "b"

        # Add a Name node at the end of the chain to avoid "Mock object has no attribute 'expr'"
        name_a = create_strict_mock(astroid.nodes.Name)
        name_a.name = "a"

        attr_b.expr = name_a
        attr_c.expr = attr_b
        node.func = attr_c

        self.ast_gateway.is_trusted_authority_call.return_value = True

        self.checker.visit_call(node)
        self.assertNoMessages(self.checker)

    def test_visit_call_fluent_exclusion(self):
        """W9006: Excluded if Fluent API."""
        node = create_strict_mock(astroid.nodes.Call)
        self._add_root_mock(node)

        # Structure: node.func -> Attribute(filter) -> expr -> Attribute(b) -> expr -> Name(x)
        attr_filter = create_strict_mock(astroid.nodes.Attribute)
        attr_filter.attrname = "filter"

        attr_b = create_strict_mock(astroid.nodes.Attribute)
        attr_b.attrname = "b"

        name_x = create_strict_mock(astroid.nodes.Name, name="x")

        attr_b.expr = name_x
        attr_filter.expr = attr_b
        node.func = attr_filter

        self.ast_gateway.is_fluent_call.return_value = True

        self.checker.visit_call(node)
        self.assertNoMessages(self.checker)

    def test_stranger_variable_violation(self):
        """W9006: Calling method on stranger variable."""
        # x = other.get_x() -> x is stranger
        # x.do_something() -> Violation

        # 1. Assign local
        assign = create_strict_mock(astroid.nodes.Assign)
        self._add_root_mock(assign)

        target = create_strict_mock(astroid.nodes.AssignName, name="x")
        assign.targets = [target]

        # Call needs func attribute for our new primitive checking logic
        call_value = create_strict_mock(astroid.nodes.Call)
        call_value.func = MagicMock()  # Add func attribute
        assign.value = call_value

        # Mock gateway methods to ensure it's not excluded as trusted/primitive
        self.ast_gateway.is_trusted_authority_call.return_value = False
        self.ast_gateway.get_return_type_qname_from_expr.return_value = None  # Not a primitive

        self.checker.visit_assign(assign)

        # 2. Call on stranger
        call = create_strict_mock(astroid.nodes.Call)
        self._add_root_mock(call)

        call.func = create_strict_mock(astroid.nodes.Attribute)
        call.func.attrname = "do_something"
        call.func.expr = create_strict_mock(astroid.nodes.Name, name="x")

        # Mock to ensure the stranger check isn't excluded
        self.checker._is_chain_excluded = MagicMock(return_value=False)

        self.checker.visit_call(call)
        self.assertAddsMessage(self.checker, "clean-arch-demeter", node=call, args=("x.do_something (Stranger)",))

def create_strict_mock(spec_cls, **attrs):
    """Helper duplicate."""
    m = MagicMock(spec=spec_cls)
    for k, v in attrs.items():
        setattr(m, k, v)
    return m
