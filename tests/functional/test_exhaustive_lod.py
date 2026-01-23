import pytest
import astroid
from unittest import mock
from pylint.testutils import CheckerTestCase, MessageTest
from clean_architecture_linter.checks.patterns import CouplingChecker
from clean_architecture_linter.di.container import ExcelsiorContainer

class TestLoDExhaustive(CheckerTestCase):
    CHECKER_CLASS = CouplingChecker

    def test_safe_zone_passes(self):
        """Verify 0 messages for SAFE_ZONE."""
        # Mock LayerRegistry to return 'Domain' for the current file to satisfy Category 5
        with mock.patch("clean_architecture_linter.config.ConfigurationLoader.get_layer_for_module", return_value="Domain"):
            with open("tests/benchmarks/lod-samples.py", "r") as f:
                content = f.read()

            node = astroid.parse(content)
            # Find all functions in SAFE_ZONE (everything before 'VIOLATION_ZONE')
            safe_funcs = [
                f for f in node.body
                if isinstance(f, astroid.nodes.FunctionDef)
                and f.lineno < content.find("VIOLATION_ZONE") / 40 # Rough heuristic
            ]
            # Actually, let's just use the whole node but only assert no messages for safe lines
            self.walk(node)

            # Filter messages: any message on a line < VIOLATION_ZONE start is a failure
            v_line = 0
            for i, line in enumerate(content.splitlines()):
                if "VIOLATION_ZONE" in line:
                    v_line = i + 1
                    break

            unexpected = []
            for msg in self.linter.release_messages():
                if msg.msg_id in ["clean-arch-demeter", "W9006"] and msg.line < v_line:
                    unexpected.append(msg)

            assert not unexpected, f"Unexpected LoD violations in SAFE_ZONE: {unexpected}"

    def test_violation_zone_fails(self):
        """Verify exhaustive violations are caught in VIOLATION_ZONE."""
        with open("tests/benchmarks/lod-samples.py", "r") as f:
             content = f.read()

        node = astroid.parse(content)
        self.walk(node)

        v_line = 0
        for i, line in enumerate(content.splitlines()):
            if "VIOLATION_ZONE" in line:
                v_line = i + 1
                break

        v_count = 0
        for msg in self.linter.release_messages():
            if msg.msg_id in ["clean-arch-demeter", "W9006"] and msg.line >= v_line:
                v_count += 1

        assert v_count >= 2, f"Expected at least 2 LoD violations in VIOLATION_ZONE, found {v_count}"
