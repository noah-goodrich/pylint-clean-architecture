"""Tests for EntropyChecker (W9030: architectural entropy / concept scatter)."""

import unittest
from pathlib import Path
from unittest.mock import MagicMock

import astroid

from excelsior_architect.use_cases.checks.entropy import EntropyChecker
from tests.unit.checker_test_utils import CheckerTestCase


def _minimal_registry() -> dict[str, object]:
    """Registry with W9030 so checker has msgs."""
    return {
        "excelsior.W9030": {
            "message_template": "Architectural entropy: identifier '%s' defined in %d place(s): %s.",
            "symbol": "architectural-entropy",
            "short_description": "Same concept defined in multiple places",
        },
    }


class TestEntropyChecker(unittest.TestCase, CheckerTestCase):
    """EntropyChecker detects same string literal in definition context in 2+ files."""

    def setUp(self) -> None:
        self.linter = MagicMock()
        self.checker = EntropyChecker(
            self.linter, registry=_minimal_registry())

    def test_no_scatter_single_file(self) -> None:
        """Single file with identifier in definition context does not emit W9030."""
        code = 'RULES = ["W9010"]'
        node = astroid.parse(code)
        node.file = str(Path("/project/src/module_a.py"))
        self.checker.visit_module(node)
        self.checker.close()
        self.assertNoMessages(self.checker)

    def test_scatter_two_files_emits_w9030(self) -> None:
        """Same identifier in definition context in two files emits W9030 (once per identifier)."""
        code_a = 'RULES = ["W9010"]'
        code_b = 'CODES = ["W9010"]'
        node_a = astroid.parse(code_a)
        node_b = astroid.parse(code_b)
        node_a.file = str(Path("/project/src/module_a.py"))
        node_b.file = str(Path("/project/src/module_b.py"))

        self.checker.visit_module(node_a)
        self.checker.visit_module(node_b)
        self.checker.close()

        self.assertAddsMessage(
            self.checker,
            "W9030",
            args=("W9010", 2, "/project/src/module_a.py, /project/src/module_b.py"),
        )

    def test_scatter_emits_once_per_identifier(self) -> None:
        """Multiple files with same identifier emit one W9030 when we first see the second file."""
        code = 'RULES = ["W9006"]'
        nodes = [
            (astroid.parse(code), f"/project/src/file_{i}.py")
            for i in range(3)
        ]
        for node, path in nodes:
            node.file = path
            self.checker.visit_module(node)
        self.checker.close()

        calls = [
            c for c in self.checker.linter.add_message.call_args_list if c[0][0] == "W9030"]
        self.assertEqual(
            len(calls), 1, "Should emit exactly one W9030 per scattered identifier")
        # Emit happens at first duplicate (file_1), so args are (identifier, 2, file_0, file_1)
        args = calls[0][1].get("args") or (
            calls[0][0][3] if len(calls[0][0]) > 3 else None)
        self.assertEqual(args[0], "W9006")
        self.assertGreaterEqual(int(args[1]), 2)
        self.assertIn("/project/src/file_0.py", args[2])
        self.assertIn("/project/src/file_1.py", args[2])

    def test_definition_context_dict_key(self) -> None:
        """String as dict key (e.g. Pylint msgs) is definition context."""
        code = 'msgs = {"W9010": ("msg", "sym", "desc")}'
        node_a = astroid.parse(code)
        node_b = astroid.parse(code)
        node_a.file = "/project/a.py"
        node_b.file = "/project/b.py"
        self.checker.visit_module(node_a)
        self.checker.visit_module(node_b)
        self.checker.close()
        self.assertAddsMessage(self.checker, "W9030", args=(
            "W9010", "2", "/project/a.py, /project/b.py"))
