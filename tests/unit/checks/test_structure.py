import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import astroid.nodes

from clean_architecture_linter.domain.config import ConfigurationLoader
from clean_architecture_linter.use_cases.checks.structure import ModuleStructureChecker
from tests.unit.checker_test_utils import CheckerTestCase, create_mock_node


class TestModuleStructureChecker(unittest.TestCase, CheckerTestCase):
    def setUp(self) -> None:
        self.linter = MagicMock()
        self.checker = ModuleStructureChecker(
            self.linter, config_loader=ConfigurationLoader({}, {}), registry={})

    def test_god_file_detection(self) -> None:
        """W9010 detected when multiple heavy layers exist."""
        # Mock classdefs for StructureChecker
        # It tracks 'current_layer_types'

        node_usecase = create_mock_node(
            astroid.nodes.ClassDef, name="CreateUser")
        node_infra = create_mock_node(
            astroid.nodes.ClassDef, name="SqlUserRepo")

        # We need a predictable config/layer resolution.
        # We can mock config_loader.get_layer_for_class_node
        self.checker.config_loader.get_layer_for_class_node = MagicMock(side_effect=[
            "UseCase",
            "Infrastructure"
        ])

        # Checking logic calls _is_heavy_component
        # UseCase and Infra are Heavy.

        self.checker.visit_module(MagicMock())
        self.checker.visit_classdef(node_usecase)
        self.checker.visit_classdef(node_infra)

        module_node = create_mock_node(astroid.nodes.Module, name="god_module")
        self.checker.leave_module(module_node)

        # Verify "Mixed layers" detected
        self.assertAddsMessage(
            self.checker, "W9010", node=module_node)

    def test_deep_structure_root(self) -> None:
        """W9011 detected for root files."""
        # Need to mock Path.cwd and relative logic in _is_root_logic

        node = create_mock_node(
            astroid.nodes.Module, name="root_logic", file="/project/root_logic.py")

        with patch("clean_architecture_linter.domain.rules.module_structure.Path.cwd", return_value=Path("/project")):
            self.checker.visit_module(node)

        self.assertAddsMessage(
            self.checker, "W9011", node=node, args=("root_logic",))

    def test_god_module_functions_only_not_flagged(self) -> None:
        """Module with many top-level functions but NO classes must NOT trigger W9010.
        W9010 only counts classes (visit_classdef). CLI-style 'god module' is thus invisible.
        This test documents current behavior; a future 'god module' rule would flag it."""
        module_node = create_mock_node(astroid.nodes.Module, name="cli_like")
        module_node.file = ""  # Skip root-logic check

        self.checker.visit_module(module_node)
        # No visit_classdef — mirrors cli.py (only functions)
        self.checker.leave_module(module_node)

        # Current rule does not fire; we expect no god-file message
        for call in self.checker.linter.add_message.call_args_list:
            args = call[0]
            if len(args) > 0 and args[0] == "W9010":
                raise AssertionError(
                    "W9010 must not fire for modules with no classes (god-module gap)"
                )

    def test_heavy_components_message(self) -> None:
        """W9010 when multiple heavy components (same layer) exist."""
        node_a = create_mock_node(astroid.nodes.ClassDef, name="UseCaseA")
        node_b = create_mock_node(astroid.nodes.ClassDef, name="UseCaseB")
        self.checker.config_loader.get_layer_for_class_node = MagicMock(
            return_value="UseCase"
        )
        self.checker.config_loader.resolve_layer = MagicMock(return_value=None)
        module_node = create_mock_node(
            astroid.nodes.Module, name="multi_use_case")
        module_node.file = "/project/src/app/use_cases.py"
        self.checker.visit_module(module_node)
        self.checker.visit_classdef(node_a)
        self.checker.visit_classdef(node_b)
        self.checker.leave_module(module_node)
        self.assertAddsMessage(
            self.checker, "W9010", node=module_node,
            args=("2 Heavy components found",),
        )

    def test_visit_functiondef_increments_top_level_count(self) -> None:
        """Top-level function (parent is Module) increments top_level_function_count."""
        module_node = create_mock_node(astroid.nodes.Module, name="mod")
        module_node.file = ""
        func_node = create_mock_node(
            astroid.nodes.FunctionDef, name="top_level_fn")
        # Real Module so isinstance(node.parent, astroid.nodes.Module) in checker passes
        func_node.parent = astroid.parse("")
        self.checker.visit_module(module_node)
        self.assertEqual(self.checker._top_level_function_count, 0)
        self.checker.visit_functiondef(func_node)
        self.assertEqual(self.checker._top_level_function_count, 1)

    def test_layer_integrity_unmapped_file_in_src(self) -> None:
        """W9017 when file is under src/ and not in layer_map."""
        module_node = create_mock_node(
            astroid.nodes.Module, name="unmapped", file="/project/src/foo/bar.py"
        )
        mock_loader = MagicMock()
        mock_loader.get_layer_for_module = MagicMock(return_value=None)
        mock_loader.registry.resolve_layer = MagicMock(return_value=None)
        self.checker.config_loader = mock_loader
        self.checker._structure_rule._config_loader = mock_loader
        self.checker.visit_module(module_node)
        self.assertAddsMessage(
            self.checker, "W9017", node=module_node,
            args=("/project/src/foo/bar.py",),
        )

    def test_layer_integrity_mapped_file_not_flagged(self) -> None:
        """W9017 not raised when layer_map resolves the module."""
        module_node = create_mock_node(
            astroid.nodes.Module, name="mapped", file="/project/src/domain/entities.py"
        )
        mock_loader = MagicMock()
        mock_loader.get_layer_for_module = MagicMock(return_value="Domain")
        self.checker.config_loader = mock_loader
        self.checker._structure_rule._config_loader = mock_loader
        self.checker.visit_module(module_node)
        for call in self.checker.linter.add_message.call_args_list:
            if len(call[0]) > 0 and call[0][0] == "W9017":
                raise AssertionError(
                    "W9017 must not fire when layer is mapped")

    def test_class_only_procedural_in_use_case_layer(self) -> None:
        """W9018 when file has top-level functions, no classes, in UseCase layer."""
        module_node = create_mock_node(
            astroid.nodes.Module, name="procedural", file="/project/src/use_cases/ops.py"
        )
        func_node = create_mock_node(
            astroid.nodes.FunctionDef, name="do_thing")
        func_node.parent = astroid.parse("")
        mock_loader = MagicMock()
        mock_loader.registry.resolve_layer = MagicMock(return_value="UseCase")
        self.checker.config_loader = mock_loader
        self.checker._structure_rule._config_loader = mock_loader
        self.checker.visit_module(module_node)
        self.checker.visit_functiondef(func_node)
        self.checker.leave_module(module_node)
        self.assertAddsMessage(
            self.checker, "W9018", node=module_node,
            args=("/project/src/use_cases/ops.py",),
        )

    def test_top_level_functions_allowed_in_main_py(self) -> None:
        """W9018 does NOT fire when file is __main__.py (hard-wired allowlist)."""
        module_node = create_mock_node(
            astroid.nodes.Module, name="__main__", file="/project/src/package/__main__.py"
        )
        func_node = create_mock_node(
            astroid.nodes.FunctionDef, name="main")
        func_node.parent = astroid.parse("")
        mock_loader = MagicMock()
        mock_loader.registry.resolve_layer = MagicMock(
            return_value="Interface")
        self.checker.config_loader = mock_loader
        self.checker._structure_rule._config_loader = mock_loader
        self.checker.visit_module(module_node)
        self.checker.visit_functiondef(func_node)
        self.checker.leave_module(module_node)
        for call in self.checker.linter.add_message.call_args_list:
            if len(call[0]) > 0 and call[0][0] == "clean-arch-class-only":
                raise AssertionError(
                    "W9018 must not fire for __main__.py (allowlisted entry point)")

    def test_global_keyword_triggers_w9020(self) -> None:
        """W9020 when 'global' is used (global state violation)."""
        global_node = create_mock_node(astroid.nodes.Global, names=["_cache"])
        self.checker.visit_global(global_node)
        self.assertAddsMessage(
            self.checker, "W9020", node=global_node, args=("_cache",)
        )

    def test_is_heavy_component_protocol_light(self) -> None:
        """Protocol-named class is not heavy."""
        node = create_mock_node(astroid.nodes.ClassDef, name="MyProtocol")
        self.assertFalse(
            self.checker._structure_rule._is_heavy_component("UseCase", node)
        )

    def test_is_heavy_component_dto_light(self) -> None:
        """DTO-named class is not heavy."""
        node = create_mock_node(astroid.nodes.ClassDef, name="UserDTO")
        self.assertFalse(
            self.checker._structure_rule._is_heavy_component(
                "Infrastructure", node)
        )
