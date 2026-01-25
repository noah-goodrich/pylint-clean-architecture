import os

# Hack path to import src
import sys
import unittest
from unittest.mock import MagicMock

sys.path.append(os.path.abspath("src"))

import astroid.nodes
from clean_architecture_linter.checks.rules.missing_type_hint import MissingTypeHintRule


# We need a strict mock creator that sets attributes properly
def create_strict_mock(spec_cls, **attrs):
    m = MagicMock(spec=spec_cls)
    for k, v in attrs.items():
        setattr(m, k, v)
    if not hasattr(m, "lineno"):
        m.lineno = 1
    return m

class TestMissingTypeHintRule(unittest.TestCase):
    def setUp(self) -> None:
        self.rule = MissingTypeHintRule()

    def test_check_return_type_missing(self) -> None:
        node = create_strict_mock(astroid.nodes.FunctionDef)
        node.name = "foo"
        node.returns = None
        node.args = MagicMock()
        node.args.args = []
        node.args.annotations = []

        violations = self.rule.check(node, {})
        self.assertEqual(len(violations), 1)
        self.assertIn("Missing return type hint", violations[0].message)

    def test_check_parameter_type_missing(self) -> None:
        node = create_strict_mock(astroid.nodes.FunctionDef)
        node.name = "foo"
        node.returns = MagicMock() # Return type ok
        node.is_method.return_value = False

        # Args: x
        arg_x = create_strict_mock(astroid.nodes.AssignName, name="x")
        # Annotations (None)

        args = MagicMock()
        args.args = [arg_x]
        args.annotations = [None]
        node.args = args

        violations = self.rule.check(node, {})
        self.assertEqual(len(violations), 1)
        self.assertIn("parameter 'x'", violations[0].message)

        # Test Fix Suggestion
        fix = self.rule.fix(violations[0])
        self.assertIsNotNone(fix)
        self.assertEqual(fix.context["command"], "add_parameter_type")
        self.assertEqual(fix.context["param_name"], "x")
        self.assertEqual(fix.context["function_name"], "foo")

if __name__ == '__main__':
    unittest.main()
