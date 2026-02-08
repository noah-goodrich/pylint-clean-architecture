"""Unit tests for Boundary Rules (W9003, W9004)."""

import unittest
from unittest.mock import MagicMock

import astroid

from excelsior_architect.domain.layer_registry import LayerRegistry
from excelsior_architect.domain.rules.boundary_rules import ResourceRule, VisibilityRule


class TestResourceRule(unittest.TestCase):
    """Test ResourceRule (W9004) detection."""

    def setUp(self) -> None:
        self.mock_python_gateway = MagicMock()
        self.mock_config_loader = MagicMock()
        self.mock_config_loader.config = {}
        self.mock_config_loader.internal_modules = []
        self.rule = ResourceRule(
            python_gateway=self.mock_python_gateway,
            config_loader=self.mock_config_loader,
        )

    def test_is_test_file_detects_tests_directory(self) -> None:
        """_is_test_file() returns True for files in tests/ directory."""
        node = MagicMock()
        root = MagicMock()
        root.file = "/project/tests/unit/test_foo.py"
        root.name = "test_foo"
        node.root.return_value = root

        result = self.rule._is_test_file(node)
        self.assertTrue(result)

    def test_is_test_file_detects_test_directory(self) -> None:
        """_is_test_file() returns True for files in test/ directory."""
        node = MagicMock()
        root = MagicMock()
        root.file = "/project/test/foo.py"
        root.name = "test_foo"
        node.root.return_value = root

        result = self.rule._is_test_file(node)
        self.assertTrue(result)

    def test_is_test_file_detects_test_prefix(self) -> None:
        """_is_test_file() returns True for modules starting with test_."""
        node = MagicMock()
        root = MagicMock()
        root.file = "/project/src/test_foo.py"
        root.name = "test_foo"
        node.root.return_value = root

        result = self.rule._is_test_file(node)
        self.assertTrue(result)

    def test_is_test_file_detects_dot_tests_in_module(self) -> None:
        """_is_test_file() returns True for modules with .tests. in name."""
        node = MagicMock()
        root = MagicMock()
        root.file = "/project/src/foo.py"
        root.name = "mypackage.tests.foo"
        node.root.return_value = root

        result = self.rule._is_test_file(node)
        self.assertTrue(result)

    def test_is_test_file_returns_false_for_regular_file(self) -> None:
        """_is_test_file() returns False for non-test files."""
        node = MagicMock()
        root = MagicMock()
        root.file = "/project/src/domain/user.py"
        root.name = "domain.user"
        node.root.return_value = root

        result = self.rule._is_test_file(node)
        self.assertFalse(result)

    def test_is_test_file_handles_windows_paths(self) -> None:
        """_is_test_file() normalizes Windows paths."""
        node = MagicMock()
        root = MagicMock()
        root.file = "C:\\project\\tests\\test_foo.py"
        root.name = "test_foo"
        node.root.return_value = root

        result = self.rule._is_test_file(node)
        self.assertTrue(result)

    def test_is_test_file_handles_missing_file(self) -> None:
        """_is_test_file() handles missing file attribute."""
        node = MagicMock()
        root = MagicMock()
        root.file = None
        root.name = "module"
        node.root.return_value = root

        result = self.rule._is_test_file(node)
        self.assertFalse(result)

    def test_is_test_file_handles_missing_name(self) -> None:
        """_is_test_file() handles missing name attribute."""
        node = MagicMock()
        root = MagicMock()
        root.file = "/project/src/foo.py"
        root.name = None
        node.root.return_value = root

        result = self.rule._is_test_file(node)
        self.assertFalse(result)

    def test_is_inside_type_checking_detects_type_checking_block(self) -> None:
        """_is_inside_type_checking() returns True for imports inside TYPE_CHECKING."""
        node = MagicMock()

        # Create parent If with TYPE_CHECKING test
        if_parent = MagicMock(spec=astroid.nodes.If)
        test_node = MagicMock(spec=astroid.nodes.Name)
        test_node.name = "TYPE_CHECKING"
        if_parent.test = test_node

        node.parent = if_parent

        result = self.rule._is_inside_type_checking(node)
        self.assertTrue(result)

    def test_is_inside_type_checking_returns_false_outside(self) -> None:
        """_is_inside_type_checking() returns False for imports outside TYPE_CHECKING."""
        node = MagicMock()
        parent = MagicMock()
        parent.parent = None
        node.parent = parent

        result = self.rule._is_inside_type_checking(node)
        self.assertFalse(result)

    def test_is_inside_type_checking_handles_nested_blocks(self) -> None:
        """_is_inside_type_checking() traverses up through nested blocks."""
        node = MagicMock()

        # Nested: node -> some_block -> if TYPE_CHECKING
        some_block = MagicMock()
        if_parent = MagicMock(spec=astroid.nodes.If)
        test_node = MagicMock(spec=astroid.nodes.Name)
        test_node.name = "TYPE_CHECKING"
        if_parent.test = test_node

        node.parent = some_block
        some_block.parent = if_parent
        if_parent.parent = None

        result = self.rule._is_inside_type_checking(node)
        self.assertTrue(result)

    def test_is_inside_type_checking_stops_at_depth_limit(self) -> None:
        """_is_inside_type_checking() stops at depth limit to prevent infinite loops."""
        node = MagicMock()

        # Create circular reference (shouldn't happen but safety check)
        parent1 = MagicMock()
        parent2 = MagicMock()
        node.parent = parent1
        parent1.parent = parent2
        parent2.parent = parent1  # Circular!

        # Should not hang
        result = self.rule._is_inside_type_checking(node)
        self.assertFalse(result)

    def test_is_forbidden_detects_os_import(self) -> None:
        """_is_forbidden() detects os import as forbidden."""
        result = self.rule._is_forbidden("os")
        self.assertTrue(result)

    def test_is_forbidden_detects_sys_import(self) -> None:
        """_is_forbidden() detects sys import as forbidden."""
        result = self.rule._is_forbidden("sys")
        self.assertTrue(result)

    def test_is_forbidden_detects_subprocess_import(self) -> None:
        """_is_forbidden() detects subprocess import as forbidden."""
        result = self.rule._is_forbidden("subprocess")
        self.assertTrue(result)

    def test_is_forbidden_detects_requests_import(self) -> None:
        """_is_forbidden() detects requests import as forbidden."""
        result = self.rule._is_forbidden("requests")
        self.assertTrue(result)

    def test_is_forbidden_detects_sqlalchemy_import(self) -> None:
        """_is_forbidden() detects sqlalchemy import as forbidden."""
        result = self.rule._is_forbidden("sqlalchemy")
        self.assertTrue(result)

    def test_is_forbidden_allows_typing_import(self) -> None:
        """_is_forbidden() allows typing import."""
        result = self.rule._is_forbidden("typing")
        self.assertFalse(result)

    def test_is_forbidden_allows_dataclasses_import(self) -> None:
        """_is_forbidden() allows dataclasses import."""
        result = self.rule._is_forbidden("dataclasses")
        self.assertFalse(result)

    def test_is_forbidden_allows_abc_import(self) -> None:
        """_is_forbidden() allows abc import."""
        result = self.rule._is_forbidden("abc")
        self.assertFalse(result)

    def test_is_forbidden_allows_enum_import(self) -> None:
        """_is_forbidden() allows enum import."""
        result = self.rule._is_forbidden("enum")
        self.assertFalse(result)

    def test_is_forbidden_allows_pathlib_import(self) -> None:
        """_is_forbidden() allows pathlib import."""
        result = self.rule._is_forbidden("pathlib")
        self.assertFalse(result)

    def test_is_forbidden_allows_datetime_import(self) -> None:
        """_is_forbidden() allows datetime import."""
        result = self.rule._is_forbidden("datetime")
        self.assertFalse(result)

    def test_is_forbidden_allows_json_import(self) -> None:
        """_is_forbidden() allows json import."""
        result = self.rule._is_forbidden("json")
        self.assertFalse(result)

    def test_is_forbidden_respects_config_allowed_prefixes(self) -> None:
        """_is_forbidden() respects allowed_prefixes from config."""
        self.mock_config_loader.config = {"allowed_prefixes": ["custom_lib"]}
        result = self.rule._is_forbidden("custom_lib")
        self.assertFalse(result)

    def test_is_forbidden_allows_custom_prefix_submodules(self) -> None:
        """_is_forbidden() allows submodules of custom allowed prefixes."""
        self.mock_config_loader.config = {"allowed_prefixes": ["mylib"]}
        result = self.rule._is_forbidden("mylib.submodule")
        self.assertFalse(result)

    def test_is_forbidden_checks_internal_modules(self) -> None:
        """_is_forbidden() allows internal modules from config."""
        self.mock_config_loader.internal_modules = ["myproject"]
        result = self.rule._is_forbidden("myproject.domain")
        self.assertFalse(result)

    def test_check_skips_infrastructure_layer(self) -> None:
        """check() skips imports in infrastructure layer."""
        node = MagicMock()
        node.modname = "os"
        node.names = None
        root = MagicMock()
        root.file = "/project/src/infrastructure/repo.py"
        root.name = "infrastructure.repo"
        node.root.return_value = root

        self.mock_python_gateway.get_node_layer.return_value = LayerRegistry.LAYER_INFRASTRUCTURE

        result = self.rule.check(node)
        self.assertEqual(result, [])

    def test_check_detects_forbidden_import_in_domain(self) -> None:
        """check() detects forbidden imports in domain layer."""
        node = MagicMock()
        node.modname = "os"
        node.names = None
        root = MagicMock()
        root.file = "/project/src/domain/user.py"
        root.name = "domain.user"
        node.root.return_value = root
        node.lineno = 1
        node.col_offset = 0

        self.mock_python_gateway.get_node_layer.return_value = LayerRegistry.LAYER_DOMAIN

        violations = self.rule.check(node)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].code, "W9004")
        self.assertIn("os", violations[0].message)

    def test_check_detects_forbidden_import_in_use_case(self) -> None:
        """check() detects forbidden imports in use_case layer."""
        node = MagicMock()
        node.modname = "requests"
        node.names = None
        root = MagicMock()
        root.file = "/project/src/use_cases/login.py"
        root.name = "use_cases.login"
        node.root.return_value = root
        node.lineno = 1
        node.col_offset = 0

        self.mock_python_gateway.get_node_layer.return_value = LayerRegistry.LAYER_USE_CASE

        violations = self.rule.check(node)
        self.assertEqual(len(violations), 1)
        self.assertIn("requests", violations[0].message)

    def test_check_skips_type_checking_imports(self) -> None:
        """check() skips imports inside TYPE_CHECKING blocks."""
        node = MagicMock()
        node.modname = "os"
        node.names = None
        root = MagicMock()
        root.file = "/project/src/domain/user.py"
        root.name = "domain.user"
        node.root.return_value = root

        # Inside TYPE_CHECKING block
        if_parent = MagicMock(spec=astroid.nodes.If)
        test_node = MagicMock(spec=astroid.nodes.Name)
        test_node.name = "TYPE_CHECKING"
        if_parent.test = test_node
        node.parent = if_parent

        self.mock_python_gateway.get_node_layer.return_value = LayerRegistry.LAYER_DOMAIN

        result = self.rule.check(node)
        self.assertEqual(result, [])

    def test_check_skips_test_files(self) -> None:
        """check() skips imports in test files."""
        node = MagicMock()
        node.modname = "os"
        node.names = None
        root = MagicMock()
        root.file = "/project/tests/test_user.py"
        root.name = "test_user"
        node.root.return_value = root

        self.mock_python_gateway.get_node_layer.return_value = LayerRegistry.LAYER_DOMAIN

        result = self.rule.check(node)
        self.assertEqual(result, [])

    def test_check_allows_allowed_prefix(self) -> None:
        """check() allows imports matching allowed_prefixes."""
        node = MagicMock()
        node.modname = "typing"
        node.names = None
        root = MagicMock()
        root.file = "/project/src/domain/user.py"
        root.name = "domain.user"
        node.root.return_value = root

        self.mock_python_gateway.get_node_layer.return_value = LayerRegistry.LAYER_DOMAIN

        result = self.rule.check(node)
        self.assertEqual(result, [])

    def test_check_handles_from_import(self) -> None:
        """check() handles 'from x import y' statements."""
        node = MagicMock()
        node.modname = None
        node.names = [("os", None), ("sys", None)]
        root = MagicMock()
        root.file = "/project/src/domain/user.py"
        root.name = "domain.user"
        node.root.return_value = root
        node.lineno = 1
        node.col_offset = 0

        self.mock_python_gateway.get_node_layer.return_value = LayerRegistry.LAYER_DOMAIN

        violations = self.rule.check(node)
        self.assertEqual(len(violations), 1)  # First forbidden import

    def test_check_returns_first_forbidden_only(self) -> None:
        """check() returns only first forbidden import when multiple present."""
        node = MagicMock()
        node.modname = None
        node.names = [("os", None), ("sys", None), ("subprocess", None)]
        root = MagicMock()
        root.file = "/project/src/domain/user.py"
        root.name = "domain.user"
        node.root.return_value = root
        node.lineno = 1
        node.col_offset = 0

        self.mock_python_gateway.get_node_layer.return_value = LayerRegistry.LAYER_DOMAIN

        violations = self.rule.check(node)
        self.assertEqual(len(violations), 1)

    def test_allowed_prefixes_includes_defaults(self) -> None:
        """allowed_prefixes property includes default allowed modules."""
        prefixes = self.rule.allowed_prefixes
        self.assertIn("typing", prefixes)
        self.assertIn("dataclasses", prefixes)
        self.assertIn("abc", prefixes)
        self.assertIn("datetime", prefixes)

    def test_allowed_prefixes_merges_config(self) -> None:
        """allowed_prefixes property merges config with defaults."""
        self.mock_config_loader.config = {"allowed_prefixes": ["custom"]}
        prefixes = self.rule.allowed_prefixes
        self.assertIn("typing", prefixes)  # Default
        self.assertIn("custom", prefixes)  # From config

    def test_allowed_prefixes_handles_non_list_config(self) -> None:
        """allowed_prefixes property handles non-list config gracefully."""
        self.mock_config_loader.config = {"allowed_prefixes": "not_a_list"}
        prefixes = self.rule.allowed_prefixes
        self.assertIn("typing", prefixes)  # Still has defaults


class TestVisibilityRule(unittest.TestCase):
    """Test VisibilityRule (W9003) detection."""

    def setUp(self) -> None:
        self.mock_config_loader = MagicMock()
        self.mock_config_loader.visibility_enforcement = True
        self.rule = VisibilityRule(config_loader=self.mock_config_loader)

    def test_check_returns_empty_for_non_attribute(self) -> None:
        """check() returns [] for non-Attribute nodes."""
        node = MagicMock()
        node.attrname = None
        result = self.rule.check(node)
        self.assertEqual(result, [])

    def test_check_returns_empty_for_public_attribute(self) -> None:
        """check() returns [] for public attributes (no leading underscore)."""
        node = MagicMock(spec=astroid.nodes.Attribute)
        node.attrname = "public_attr"
        node.expr = MagicMock()
        result = self.rule.check(node)
        self.assertEqual(result, [])

    def test_check_returns_empty_for_dunder_attribute(self) -> None:
        """check() returns [] for dunder attributes (__foo__)."""
        node = MagicMock(spec=astroid.nodes.Attribute)
        node.attrname = "__private__"
        node.expr = MagicMock()
        result = self.rule.check(node)
        self.assertEqual(result, [])

    def test_check_detects_protected_access(self) -> None:
        """check() detects access to protected members (_foo)."""
        node = MagicMock(spec=astroid.nodes.Attribute)
        node.attrname = "_protected"
        expr = MagicMock(spec=astroid.nodes.Name)
        expr.name = "other"
        node.expr = expr
        node.lineno = 1
        node.col_offset = 0
        mock_root = MagicMock()
        mock_root.file = "test.py"
        node.root.return_value = mock_root

        violations = self.rule.check(node)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].code, "W9003")
        self.assertIn("_protected", violations[0].message)

    def test_check_allows_self_protected_access(self) -> None:
        """check() allows self._protected access."""
        node = MagicMock(spec=astroid.nodes.Attribute)
        node.attrname = "_protected"
        expr = MagicMock(spec=astroid.nodes.Name)
        expr.name = "self"
        node.expr = expr

        result = self.rule.check(node)
        self.assertEqual(result, [])

    def test_check_allows_cls_protected_access(self) -> None:
        """check() allows cls._protected access."""
        node = MagicMock(spec=astroid.nodes.Attribute)
        node.attrname = "_protected"
        expr = MagicMock(spec=astroid.nodes.Name)
        expr.name = "cls"
        node.expr = expr

        result = self.rule.check(node)
        self.assertEqual(result, [])

    def test_check_allows_chained_self_access(self) -> None:
        """check() allows self.obj._protected access through chain."""
        node = MagicMock(spec=astroid.nodes.Attribute)
        node.attrname = "_protected"

        # self.obj._protected - the expr is self.obj
        middle_attr = MagicMock(spec=astroid.nodes.Attribute)
        middle_attr.attrname = "obj"
        self_node = MagicMock(spec=astroid.nodes.Name)
        self_node.name = "self"
        middle_attr.expr = self_node
        node.expr = middle_attr

        result = self.rule.check(node)
        self.assertEqual(result, [])

    def test_check_respects_visibility_enforcement_flag(self) -> None:
        """check() respects visibility_enforcement config flag."""
        self.mock_config_loader.visibility_enforcement = False

        node = MagicMock(spec=astroid.nodes.Attribute)
        node.attrname = "_protected"
        expr = MagicMock(spec=astroid.nodes.Name)
        expr.name = "other"
        node.expr = expr

        result = self.rule.check(node)
        self.assertEqual(result, [])

    def test_receiver_is_self_or_cls_with_complex_chain(self) -> None:
        """_receiver_is_self_or_cls() traverses attribute chains."""
        node = MagicMock(spec=astroid.nodes.Attribute)
        node.attrname = "_method"

        # Create chain: self.a.b.c._method
        attr3 = MagicMock(spec=astroid.nodes.Attribute)
        attr3.attrname = "c"
        attr2 = MagicMock(spec=astroid.nodes.Attribute)
        attr2.attrname = "b"
        attr1 = MagicMock(spec=astroid.nodes.Attribute)
        attr1.attrname = "a"
        self_node = MagicMock(spec=astroid.nodes.Name)
        self_node.name = "self"

        attr1.expr = self_node
        attr2.expr = attr1
        attr3.expr = attr2
        node.expr = attr3

        result = self.rule._receiver_is_self_or_cls(node)
        self.assertTrue(result)

    def test_receiver_is_self_or_cls_returns_false_for_other(self) -> None:
        """_receiver_is_self_or_cls() returns False for non-self/cls receivers."""
        node = MagicMock(spec=astroid.nodes.Attribute)
        node.attrname = "_method"
        expr = MagicMock(spec=astroid.nodes.Name)
        expr.name = "other_obj"
        node.expr = expr

        result = self.rule._receiver_is_self_or_cls(node)
        self.assertFalse(result)
