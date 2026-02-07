"""Unit tests for MethodComplexityRule (W9032)."""

import unittest
from unittest.mock import MagicMock

import astroid

from excelsior_architect.domain.rules.complexity_rule import MethodComplexityRule


class TestMethodComplexityRule(unittest.TestCase):
    """Test MethodComplexityRule cyclomatic complexity detection."""

    def setUp(self) -> None:
        self.rule = MethodComplexityRule(threshold=10)

    def test_check_returns_empty_for_non_function(self) -> None:
        """check() returns [] for non-FunctionDef nodes."""
        node = MagicMock()
        del node.name  # Not a FunctionDef
        result = self.rule.check(node)
        self.assertEqual(result, [])

    def test_check_returns_empty_for_simple_function(self) -> None:
        """check() returns [] for functions below complexity threshold."""
        func = MagicMock(spec=astroid.nodes.FunctionDef)
        func.name = "simple_func"
        # 3 calls: all return empty
        func.nodes_of_class.side_effect = [iter([]), iter([]), iter([])]
        
        result = self.rule.check(func)
        self.assertEqual(result, [])

    def test_check_detects_high_complexity(self) -> None:
        """check() detects functions exceeding complexity threshold."""
        func = MagicMock(spec=astroid.nodes.FunctionDef)
        func.name = "complex_func"
        func.lineno = 10
        func.col_offset = 0
        mock_root = MagicMock()
        mock_root.file = "test.py"
        func.root.return_value = mock_root
        
        # Create 15 if statements (base=1 + 15 = 16 complexity)
        if_nodes = [MagicMock(spec=astroid.nodes.If) for _ in range(15)]
        
        # nodes_of_class is called 3 times: once for decision nodes tuple, once for BoolOp, once for IfExp
        call_sequence = [[if_nodes, [], []]]
        call_index = [0]
        
        def mock_nodes_of_class(types):
            result = call_sequence[0][call_index[0]]
            call_index[0] += 1
            return iter(result)
        
        func.nodes_of_class.side_effect = mock_nodes_of_class
        
        violations = self.rule.check(func)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].code, "W9032")
        self.assertIn("complex_func", violations[0].message)
        self.assertIn("16", violations[0].message)

    def test_check_uses_custom_threshold(self) -> None:
        """check() uses custom threshold when provided."""
        rule = MethodComplexityRule(threshold=5)
        func = MagicMock(spec=astroid.nodes.FunctionDef)
        func.name = "func"
        func.lineno = 1
        func.col_offset = 0
        mock_root = MagicMock()
        mock_root.file = "test.py"
        func.root.return_value = mock_root
        
        # Create 6 if statements (base=1 + 6 = 7 complexity)
        if_nodes = [MagicMock(spec=astroid.nodes.If) for _ in range(6)]
        
        # 3 calls: decision nodes, BoolOp, IfExp
        call_sequence = [[if_nodes, [], []]]
        call_index = [0]
        
        def mock_nodes_of_class(types):
            result = call_sequence[0][call_index[0]]
            call_index[0] += 1
            return iter(result)
        
        func.nodes_of_class.side_effect = mock_nodes_of_class
        
        violations = rule.check(func)
        self.assertEqual(len(violations), 1)
        self.assertIn("7", violations[0].message)
        self.assertIn("5", violations[0].message)  # Threshold

    def test_check_uses_default_threshold(self) -> None:
        """check() uses DEFAULT_THRESHOLD when None provided."""
        rule = MethodComplexityRule(threshold=None)
        self.assertEqual(rule._threshold, MethodComplexityRule.DEFAULT_THRESHOLD)

    def test_cyclomatic_complexity_counts_if_statements(self) -> None:
        """_cyclomatic_complexity() counts if statements."""
        func = MagicMock(spec=astroid.nodes.FunctionDef)
        if_nodes = [MagicMock(spec=astroid.nodes.If) for _ in range(3)]
        func.nodes_of_class.return_value = iter(if_nodes + [])  # First call
        
        complexity = self.rule._cyclomatic_complexity(func)
        # Called 3 times, need to set up side_effect
        func.nodes_of_class.side_effect = [iter(if_nodes), iter([]), iter([])]
        complexity = self.rule._cyclomatic_complexity(func)
        self.assertEqual(complexity, 4)  # base=1 + 3 ifs

    def test_cyclomatic_complexity_counts_for_loops(self) -> None:
        """_cyclomatic_complexity() counts for loops."""
        func = MagicMock(spec=astroid.nodes.FunctionDef)
        for_nodes = [MagicMock(spec=astroid.nodes.For) for _ in range(2)]
        func.nodes_of_class.side_effect = [iter(for_nodes), iter([]), iter([])]
        
        complexity = self.rule._cyclomatic_complexity(func)
        self.assertEqual(complexity, 3)  # base=1 + 2 fors

    def test_cyclomatic_complexity_counts_while_loops(self) -> None:
        """_cyclomatic_complexity() counts while loops."""
        func = MagicMock(spec=astroid.nodes.FunctionDef)
        while_nodes = [MagicMock(spec=astroid.nodes.While) for _ in range(2)]
        func.nodes_of_class.side_effect = [iter(while_nodes), iter([]), iter([])]
        
        complexity = self.rule._cyclomatic_complexity(func)
        self.assertEqual(complexity, 3)  # base=1 + 2 whiles

    def test_cyclomatic_complexity_counts_except_handlers(self) -> None:
        """_cyclomatic_complexity() counts except handlers."""
        func = MagicMock(spec=astroid.nodes.FunctionDef)
        except_nodes = [MagicMock(spec=astroid.nodes.ExceptHandler) for _ in range(3)]
        func.nodes_of_class.side_effect = [iter(except_nodes), iter([]), iter([])]
        
        complexity = self.rule._cyclomatic_complexity(func)
        self.assertEqual(complexity, 4)  # base=1 + 3 excepts

    def test_cyclomatic_complexity_counts_with_statements(self) -> None:
        """_cyclomatic_complexity() counts with statements."""
        func = MagicMock(spec=astroid.nodes.FunctionDef)
        with_nodes = [MagicMock(spec=astroid.nodes.With) for _ in range(2)]
        func.nodes_of_class.side_effect = [iter(with_nodes), iter([]), iter([])]
        
        complexity = self.rule._cyclomatic_complexity(func)
        self.assertEqual(complexity, 3)  # base=1 + 2 withs

    def test_cyclomatic_complexity_counts_asserts(self) -> None:
        """_cyclomatic_complexity() counts assert statements."""
        func = MagicMock(spec=astroid.nodes.FunctionDef)
        assert_nodes = [MagicMock(spec=astroid.nodes.Assert) for _ in range(2)]
        func.nodes_of_class.side_effect = [iter(assert_nodes), iter([]), iter([])]
        
        complexity = self.rule._cyclomatic_complexity(func)
        self.assertEqual(complexity, 3)  # base=1 + 2 asserts

    def test_cyclomatic_complexity_counts_comprehensions(self) -> None:
        """_cyclomatic_complexity() counts list/dict/set comprehensions."""
        func = MagicMock(spec=astroid.nodes.FunctionDef)
        comp_nodes = [MagicMock(), MagicMock()]
        func.nodes_of_class.side_effect = [iter(comp_nodes), iter([]), iter([])]
        
        complexity = self.rule._cyclomatic_complexity(func)
        self.assertEqual(complexity, 3)  # base=1 + 2 comps

    def test_cyclomatic_complexity_counts_bool_ops(self) -> None:
        """_cyclomatic_complexity() counts and/or operations."""
        func = MagicMock(spec=astroid.nodes.FunctionDef)
        
        # Create BoolOp with 3 values (adds 2 to complexity)
        bool_op1 = MagicMock(spec=astroid.nodes.BoolOp)
        bool_op1.values = [MagicMock(), MagicMock(), MagicMock()]
        
        # Create BoolOp with 4 values (adds 3 to complexity)
        bool_op2 = MagicMock(spec=astroid.nodes.BoolOp)
        bool_op2.values = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]
        
        # 3 calls: decision nodes (empty), BoolOps, IfExp (empty)
        func.nodes_of_class.side_effect = [iter([]), iter([bool_op1, bool_op2]), iter([])]
        
        complexity = self.rule._cyclomatic_complexity(func)
        self.assertEqual(complexity, 6)  # base=1 + (3-1) + (4-1) = 6

    def test_cyclomatic_complexity_counts_ternary_expressions(self) -> None:
        """_cyclomatic_complexity() counts ternary expressions (IfExp)."""
        func = MagicMock(spec=astroid.nodes.FunctionDef)
        ifexp_nodes = [MagicMock(spec=astroid.nodes.IfExp) for _ in range(3)]
        
        # 3 calls: decision nodes (empty), BoolOp (empty), IfExp
        func.nodes_of_class.side_effect = [iter([]), iter([]), iter(ifexp_nodes)]
        
        complexity = self.rule._cyclomatic_complexity(func)
        self.assertEqual(complexity, 4)  # base=1 + 3 ternaries

    def test_cyclomatic_complexity_combines_multiple_types(self) -> None:
        """_cyclomatic_complexity() combines all decision point types."""
        func = MagicMock(spec=astroid.nodes.FunctionDef)
        
        if_nodes = [MagicMock(spec=astroid.nodes.If) for _ in range(2)]
        for_nodes = [MagicMock(spec=astroid.nodes.For) for _ in range(1)]
        while_nodes = [MagicMock(spec=astroid.nodes.While) for _ in range(1)]
        except_nodes = [MagicMock(spec=astroid.nodes.ExceptHandler) for _ in range(1)]
        
        bool_op = MagicMock(spec=astroid.nodes.BoolOp)
        bool_op.values = [MagicMock(), MagicMock()]  # adds 1
        
        ifexp_nodes = [MagicMock(spec=astroid.nodes.IfExp)]
        
        # Store all decision nodes for first call
        all_decision_nodes = if_nodes + for_nodes + while_nodes + except_nodes
        
        # 3 calls: decision nodes tuple, BoolOp, IfExp
        func.nodes_of_class.side_effect = [
            iter(all_decision_nodes),
            iter([bool_op]),
            iter(ifexp_nodes)
        ]
        
        complexity = self.rule._cyclomatic_complexity(func)
        # base=1 + 2 ifs + 1 for + 1 while + 1 except + (2-1) bool + 1 ifexp = 8
        self.assertEqual(complexity, 8)

    def test_cyclomatic_complexity_handles_empty_function(self) -> None:
        """_cyclomatic_complexity() returns 1 for empty function (base complexity)."""
        func = MagicMock(spec=astroid.nodes.FunctionDef)
        # 3 calls: all return empty
        func.nodes_of_class.side_effect = [iter([]), iter([]), iter([])]
        
        complexity = self.rule._cyclomatic_complexity(func)
        self.assertEqual(complexity, 1)

    def test_cyclomatic_complexity_handles_single_value_bool_op(self) -> None:
        """_cyclomatic_complexity() handles BoolOp with single value (adds 0)."""
        func = MagicMock(spec=astroid.nodes.FunctionDef)
        
        bool_op = MagicMock(spec=astroid.nodes.BoolOp)
        bool_op.values = [MagicMock()]  # Only 1 value
        
        # 3 calls: decision nodes (empty), BoolOp with 1 value, IfExp (empty)
        func.nodes_of_class.side_effect = [iter([]), iter([bool_op]), iter([])]
        
        complexity = self.rule._cyclomatic_complexity(func)
        self.assertEqual(complexity, 1)  # base=1 + max(0, 1-1) = 1

    def test_cyclomatic_complexity_handles_empty_bool_op(self) -> None:
        """_cyclomatic_complexity() handles BoolOp with no values."""
        func = MagicMock(spec=astroid.nodes.FunctionDef)
        
        bool_op = MagicMock(spec=astroid.nodes.BoolOp)
        bool_op.values = []
        
        # 3 calls: decision nodes (empty), BoolOp with 0 values, IfExp (empty)
        func.nodes_of_class.side_effect = [iter([]), iter([bool_op]), iter([])]
        
        complexity = self.rule._cyclomatic_complexity(func)
        self.assertEqual(complexity, 1)  # base=1 + max(0, 0-1) = 1
