import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import astroid.nodes

from clean_architecture_linter.use_cases.checks.structure import ModuleStructureChecker
from tests.unit.checker_test_utils import CheckerTestCase, create_mock_node


class TestModuleStructureChecker(unittest.TestCase, CheckerTestCase):
    def setUp(self) -> None:
        self.linter = MagicMock()
        self.checker = ModuleStructureChecker(self.linter)
        self.checker.open()  # Load config

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
            self.checker, "clean-arch-god-file", node=module_node)

    def test_deep_structure_root(self) -> None:
        """W9011 detected for root files."""
        # Need to mock Path.cwd and relative logic in _is_root_logic

        node = create_mock_node(
            astroid.nodes.Module, name="root_logic", file="/project/root_logic.py")

        with patch("clean_architecture_linter.use_cases.checks.structure.Path.cwd", return_value=Path("/project")):
            self.checker.visit_module(node)

        self.assertAddsMessage(
            self.checker, "clean-arch-folder-structure", node=node, args=("root_logic",))

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
            if len(args) > 0 and args[0] == "clean-arch-god-file":
                raise AssertionError(
                    "clean-arch-god-file must not fire for modules with no classes (god-module gap)"
                )
