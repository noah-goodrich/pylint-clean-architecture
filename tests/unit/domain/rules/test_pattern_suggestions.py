"""Unit tests for Pattern Suggestion Rules."""

import unittest
from unittest.mock import MagicMock

import astroid

from excelsior_architect.domain.rules.pattern_suggestions import (
    BuilderSuggestionRule,
    FactorySuggestionRule,
    FacadeSuggestionRule,
    StateSuggestionRule,
    StrategySuggestionRule,
)


def _mock_function_def(name: str, param_count: int = 0) -> MagicMock:
    """Create mock FunctionDef node."""
    node = MagicMock(spec=astroid.nodes.FunctionDef)
    node.name = name
    args_node = MagicMock()
    args_node.args = [MagicMock() for _ in range(param_count)]
    node.args = args_node
    node.is_method = lambda: True
    node.lineno = 1
    node.col_offset = 0
    mock_root = MagicMock()
    mock_root.file = "test.py"
    node.root.return_value = mock_root
    return node


def _mock_class_def(name: str = "TestClass") -> MagicMock:
    """Create mock ClassDef node."""
    node = MagicMock(spec=astroid.nodes.ClassDef)
    node.name = name
    node.body = []
    node.lineno = 1
    node.col_offset = 0
    mock_root = MagicMock()
    mock_root.file = "test.py"
    node.root.return_value = mock_root
    return node


class TestBuilderSuggestionRule(unittest.TestCase):
    """Test BuilderSuggestionRule (W9041)."""

    def setUp(self) -> None:
        self.rule = BuilderSuggestionRule()

    def test_check_returns_empty_for_non_function(self) -> None:
        """check() returns [] for non-FunctionDef nodes."""
        module = MagicMock(spec=astroid.nodes.Module)
        result = self.rule.check(module)
        self.assertEqual(result, [])

    def test_check_returns_empty_for_non_init(self) -> None:
        """check() returns [] for functions that aren't __init__."""
        node = _mock_function_def("regular_method", 10)
        result = self.rule.check(node)
        self.assertEqual(result, [])

    def test_check_returns_empty_for_few_parameters(self) -> None:
        """check() returns [] when __init__ has < 6 parameters."""
        node = _mock_function_def("__init__", 5)  # 5 params + self = 6 total, but only 5 counted
        parent = _mock_class_def("SmallClass")
        node.parent = parent
        result = self.rule.check(node)
        self.assertEqual(result, [])

    def test_check_detects_many_parameters(self) -> None:
        """check() detects __init__ with 6+ parameters."""
        node = _mock_function_def("__init__", 7)  # 7 total params including self
        parent = _mock_class_def("BigClass")
        node.parent = parent
        violations = self.rule.check(node)
        
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].code, "W9041")
        self.assertIn("BigClass", violations[0].message)
        self.assertIn("6", violations[0].message)  # Should see 6 in message (7 - 1 for self)
        self.assertIn("Builder", violations[0].message)

    def test_check_handles_no_args(self) -> None:
        """check() handles FunctionDef with no args attribute."""
        node = _mock_function_def("__init__", 0)
        node.args = None
        parent = _mock_class_def()
        node.parent = parent
        result = self.rule.check(node)
        self.assertEqual(result, [])

    def test_check_handles_non_method(self) -> None:
        """check() handles __init__ that is not a method."""
        node = _mock_function_def("__init__", 7)
        node.is_method = lambda: False
        parent = _mock_class_def("TestClass")
        node.parent = parent
        # When not a method, self is not excluded, so 7 params
        violations = self.rule.check(node)
        self.assertEqual(len(violations), 1)


class TestFactorySuggestionRule(unittest.TestCase):
    """Test FactorySuggestionRule (W9042)."""

    def setUp(self) -> None:
        self.rule = FactorySuggestionRule()

    def test_check_returns_empty_for_non_if(self) -> None:
        """check() returns [] for non-If nodes."""
        module = MagicMock(spec=astroid.nodes.Module)
        result = self.rule.check(module)
        self.assertEqual(result, [])

    def test_check_returns_empty_for_single_class(self) -> None:
        """check() returns [] when if chain instantiates only one class."""
        if_node = MagicMock(spec=astroid.nodes.If)
        # Mock a call to FooClass()
        call = MagicMock(spec=astroid.nodes.Call)
        func = MagicMock(spec=astroid.nodes.Name)
        func.name = "FooClass"
        call.func = func
        if_node.nodes_of_class = lambda cls: [call] if cls == astroid.nodes.Call else []
        if_node.orelse = []
        if_node.lineno = 1
        if_node.col_offset = 0
        mock_root = MagicMock()
        mock_root.file = "test.py"
        if_node.root.return_value = mock_root
        
        result = self.rule.check(if_node)
        self.assertEqual(result, [])

    def test_check_detects_multiple_classes(self) -> None:
        """check() detects if/elif instantiating different classes."""
        if_node = MagicMock(spec=astroid.nodes.If)
        
        # First branch - FooClass()
        call1 = MagicMock(spec=astroid.nodes.Call)
        func1 = MagicMock(spec=astroid.nodes.Name)
        func1.name = "FooClass"
        call1.func = func1
        
        # elif branch - BarClass()
        elif_node = MagicMock(spec=astroid.nodes.If)
        call2 = MagicMock(spec=astroid.nodes.Call)
        func2 = MagicMock(spec=astroid.nodes.Name)
        func2.name = "BarClass"
        call2.func = func2
        elif_node.nodes_of_class = lambda cls: [call2] if cls == astroid.nodes.Call else []
        elif_node.orelse = []
        
        if_node.nodes_of_class = lambda cls: [call1] if cls == astroid.nodes.Call else []
        if_node.orelse = [elif_node]
        if_node.lineno = 1
        if_node.col_offset = 0
        mock_root = MagicMock()
        mock_root.file = "test.py"
        if_node.root.return_value = mock_root
        
        violations = self.rule.check(if_node)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].code, "W9042")
        self.assertIn("Factory", violations[0].message)

    def test_call_class_name_handles_attribute(self) -> None:
        """_call_class_name() extracts name from Attribute nodes."""
        call = MagicMock(spec=astroid.nodes.Call)
        func = MagicMock(spec=astroid.nodes.Attribute)
        func.attrname = "SomeClass"
        call.func = func
        
        name = self.rule._call_class_name(call)
        self.assertEqual(name, "SomeClass")

    def test_call_class_name_handles_none_func(self) -> None:
        """_call_class_name() handles Call with no func attribute."""
        call = MagicMock(spec=astroid.nodes.Call)
        call.func = None
        
        name = self.rule._call_class_name(call)
        self.assertIsNone(name)


class TestStrategySuggestionRule(unittest.TestCase):
    """Test StrategySuggestionRule (W9043)."""

    def setUp(self) -> None:
        self.rule = StrategySuggestionRule()

    def test_check_returns_empty_for_non_if(self) -> None:
        """check() returns [] for non-If nodes."""
        module = MagicMock(spec=astroid.nodes.Module)
        result = self.rule.check(module)
        self.assertEqual(result, [])

    def test_check_returns_empty_for_simple_if(self) -> None:
        """check() returns [] for simple if without elif."""
        if_node = MagicMock(spec=astroid.nodes.If)
        if_node.orelse = []
        if_node.lineno = 1
        if_node.col_offset = 0
        mock_root = MagicMock()
        mock_root.file = "test.py"
        if_node.root.return_value = mock_root
        
        result = self.rule.check(if_node)
        self.assertEqual(result, [])

    def test_check_detects_multiple_elif_branches(self) -> None:
        """check() detects if/elif chains with 2+ elif."""
        if_node = MagicMock(spec=astroid.nodes.If)
        
        # First elif
        elif1 = MagicMock(spec=astroid.nodes.If)
        # Second elif
        elif2 = MagicMock(spec=astroid.nodes.If)
        elif2.orelse = []
        
        elif1.orelse = [elif2]
        if_node.orelse = [elif1]
        if_node.lineno = 1
        if_node.col_offset = 0
        mock_root = MagicMock()
        mock_root.file = "test.py"
        if_node.root.return_value = mock_root
        
        violations = self.rule.check(if_node)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].code, "W9043")
        self.assertIn("Strategy", violations[0].message)
        self.assertIn("3", violations[0].message)  # 3 branches total

    def test_count_elif_branches_handles_else(self) -> None:
        """_count_elif_branches() stops at else clause."""
        if_node = MagicMock(spec=astroid.nodes.If)
        # else clause (not an If node)
        else_stmt = MagicMock(spec=astroid.nodes.Expr)
        if_node.orelse = [else_stmt]
        
        count = self.rule._count_elif_branches(if_node)
        self.assertEqual(count, 0)  # Only the initial if, no elif


class TestStateSuggestionRule(unittest.TestCase):
    """Test StateSuggestionRule (W9044)."""

    def setUp(self) -> None:
        self.rule = StateSuggestionRule()

    def test_check_returns_empty_for_non_class(self) -> None:
        """check() returns [] for non-ClassDef nodes."""
        module = MagicMock(spec=astroid.nodes.Module)
        result = self.rule.check(module)
        self.assertEqual(result, [])

    def test_check_returns_empty_when_no_repeated_state(self) -> None:
        """check() returns [] when no attribute appears in 3+ methods."""
        class_node = _mock_class_def("TestClass")
        # Method 1 checks self.status
        method1 = MagicMock(spec=astroid.nodes.FunctionDef)
        method1.name = "method1"
        if_node1 = MagicMock(spec=astroid.nodes.If)
        compare1 = MagicMock(spec=astroid.nodes.Compare)
        left1 = MagicMock(spec=astroid.nodes.Attribute)
        left1.attrname = "status"
        expr1 = MagicMock(spec=astroid.nodes.Name)
        expr1.name = "self"
        left1.expr = expr1
        compare1.left = left1
        compare1.ops = [("==", MagicMock())]
        if_node1.test = compare1
        method1.nodes_of_class = lambda cls: [if_node1] if cls == astroid.nodes.If else []
        
        # Method 2 checks self.other_attr (different attribute)
        method2 = MagicMock(spec=astroid.nodes.FunctionDef)
        method2.name = "method2"
        if_node2 = MagicMock(spec=astroid.nodes.If)
        compare2 = MagicMock(spec=astroid.nodes.Compare)
        left2 = MagicMock(spec=astroid.nodes.Attribute)
        left2.attrname = "other_attr"
        expr2 = MagicMock(spec=astroid.nodes.Name)
        expr2.name = "self"
        left2.expr = expr2
        compare2.left = left2
        compare2.ops = [("==", MagicMock())]
        if_node2.test = compare2
        method2.nodes_of_class = lambda cls: [if_node2] if cls == astroid.nodes.If else []
        
        class_node.body = [method1, method2]
        
        result = self.rule.check(class_node)
        self.assertEqual(result, [])

    def test_check_detects_repeated_state_checks(self) -> None:
        """check() detects when 3+ methods check the same self attribute."""
        class_node = _mock_class_def("StatefulClass")
        
        # Create 3 methods that all check self.status
        methods = []
        for i in range(3):
            method = MagicMock(spec=astroid.nodes.FunctionDef)
            method.name = f"method{i}"
            
            if_node = MagicMock(spec=astroid.nodes.If)
            compare = MagicMock(spec=astroid.nodes.Compare)
            left = MagicMock(spec=astroid.nodes.Attribute)
            left.attrname = "status"
            expr = MagicMock(spec=astroid.nodes.Name)
            expr.name = "self"
            left.expr = expr
            compare.left = left
            compare.ops = [("==", MagicMock())]
            if_node.test = compare
            
            method.nodes_of_class = lambda cls, n=if_node: [n] if cls == astroid.nodes.If else []
            methods.append(method)
        
        class_node.body = methods
        
        violations = self.rule.check(class_node)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].code, "W9044")
        self.assertIn("status", violations[0].message)
        self.assertIn("State", violations[0].message)
        self.assertIn("3", violations[0].message)

    def test_attr_in_compare_handles_boolop(self) -> None:
        """_attr_in_compare() extracts attribute from BoolOp."""
        bool_op = MagicMock(spec=astroid.nodes.BoolOp)
        
        compare = MagicMock(spec=astroid.nodes.Compare)
        left = MagicMock(spec=astroid.nodes.Attribute)
        left.attrname = "flag"
        expr = MagicMock(spec=astroid.nodes.Name)
        expr.name = "self"
        left.expr = expr
        compare.left = left
        compare.ops = [("==", MagicMock())]
        
        bool_op.values = [compare]
        
        attr = self.rule._attr_in_compare(bool_op)
        self.assertEqual(attr, "flag")

    def test_attr_in_compare_handles_none(self) -> None:
        """_attr_in_compare() returns None for None input."""
        attr = self.rule._attr_in_compare(None)
        self.assertIsNone(attr)


class TestFacadeSuggestionRule(unittest.TestCase):
    """Test FacadeSuggestionRule (W9045)."""

    def setUp(self) -> None:
        self.rule = FacadeSuggestionRule()

    def test_check_returns_empty_for_non_function(self) -> None:
        """check() returns [] for non-FunctionDef nodes."""
        module = MagicMock(spec=astroid.nodes.Module)
        result = self.rule.check(module)
        self.assertEqual(result, [])

    def test_check_returns_empty_for_few_dependencies(self) -> None:
        """check() returns [] when method calls < 5 distinct dependencies."""
        func = MagicMock(spec=astroid.nodes.FunctionDef)
        func.name = "simple_method"
        
        # Create calls to only 3 distinct dependencies
        calls = []
        for i in range(3):
            call = MagicMock(spec=astroid.nodes.Call)
            func_attr = MagicMock(spec=astroid.nodes.Attribute)
            func_attr.attrname = "do_something"
            expr = MagicMock(spec=astroid.nodes.Attribute)
            expr.attrname = f"dep{i}"
            self_node = MagicMock(spec=astroid.nodes.Name)
            self_node.name = "self"
            expr.expr = self_node
            func_attr.expr = expr
            call.func = func_attr
            calls.append(call)
        
        func.nodes_of_class = lambda cls: calls if cls == astroid.nodes.Call else []
        func.lineno = 1
        func.col_offset = 0
        mock_root = MagicMock()
        mock_root.file = "test.py"
        func.root.return_value = mock_root
        
        result = self.rule.check(func)
        self.assertEqual(result, [])

    def test_check_detects_many_dependencies(self) -> None:
        """check() detects methods calling 5+ distinct dependencies."""
        func = MagicMock(spec=astroid.nodes.FunctionDef)
        func.name = "complex_method"
        
        # Create calls to 6 distinct dependencies
        calls = []
        for i in range(6):
            call = MagicMock(spec=astroid.nodes.Call)
            func_attr = MagicMock(spec=astroid.nodes.Attribute)
            func_attr.attrname = "do_something"
            expr = MagicMock(spec=astroid.nodes.Attribute)
            expr.attrname = f"dep{i}"
            self_node = MagicMock(spec=astroid.nodes.Name)
            self_node.name = "self"
            expr.expr = self_node
            func_attr.expr = expr
            call.func = func_attr
            calls.append(call)
        
        func.nodes_of_class = lambda cls: calls if cls == astroid.nodes.Call else []
        func.lineno = 1
        func.col_offset = 0
        mock_root = MagicMock()
        mock_root.file = "test.py"
        func.root.return_value = mock_root
        
        violations = self.rule.check(func)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].code, "W9045")
        self.assertIn("complex_method", violations[0].message)
        self.assertIn("Facade", violations[0].message)
        self.assertIn("6", violations[0].message)

    def test_distinct_attr_calls_handles_direct_self_calls(self) -> None:
        """_distinct_attr_calls() counts self.attr() calls."""
        func = MagicMock(spec=astroid.nodes.FunctionDef)
        
        # Create call to self.service.method()
        call1 = MagicMock(spec=astroid.nodes.Call)
        func_attr = MagicMock(spec=astroid.nodes.Attribute)
        func_attr.attrname = "method"
        self_node = MagicMock(spec=astroid.nodes.Name)
        self_node.name = "self"
        func_attr.expr = self_node
        call1.func = func_attr
        
        func.nodes_of_class = lambda cls: [call1] if cls == astroid.nodes.Call else []
        
        count = self.rule._distinct_attr_calls(func)
        self.assertEqual(count, 1)
