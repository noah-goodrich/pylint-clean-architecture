from unittest import mock

import astroid
from pylint.testutils import CheckerTestCase, UnittestLinter

from clean_architecture_linter.infrastructure.di.container import ExcelsiorContainer
from clean_architecture_linter.use_cases.checks.patterns import CouplingChecker


class TestLoDExhaustive(CheckerTestCase):
    CHECKER_CLASS = CouplingChecker

    def setup_method(self) -> None:
        self.linter = UnittestLinter()
        container = ExcelsiorContainer.get_instance()
        python_gateway = container.get("PythonGateway")
        ast_gateway = container.get("AstroidGateway")
        stub_resolver = container.get("StubAuthority")
        config_loader = container.get_config_loader()
        registry = container.get_guidance_service().get_registry()
        self.checker = self.CHECKER_CLASS(
            self.linter,
            ast_gateway=ast_gateway,
            python_gateway=python_gateway,
            stub_resolver=stub_resolver,
            config_loader=config_loader,
            registry=registry,
        )

    def test_safe_zone_passes(self) -> None:
        """Verify 0 messages for SAFE_ZONE."""
        # Mock LayerRegistry to return 'Domain' for the current file to satisfy Category 5
        with mock.patch(
            "clean_architecture_linter.domain.config.ConfigurationLoader.get_layer_for_module",
            return_value="Domain",
        ):
            with open("tests/benchmarks/lod-samples.py") as f:
                content = f.read()

            node = astroid.parse(content)
            # Find all functions in SAFE_ZONE (everything before 'VIOLATION_ZONE')
            _ = [
                f for f in node.body
                if isinstance(f, astroid.nodes.FunctionDef)
                # Rough heuristic
                and f.lineno < content.find("VIOLATION_ZONE") / 40
            ]
            # Actually, let's just use the whole node but only assert no messages for safe lines
            self.walk(node)

            # Filter messages: any message on a line < VIOLATION_ZONE start is a failure
            v_line: int = 0
            for i, line in enumerate(content.splitlines()):
                if "VIOLATION_ZONE" in line:
                    v_line = i + 1
                    break

            unexpected = []
            for msg in self.linter.release_messages():
                if msg.msg_id in ["clean-arch-demeter", "W9006"] and msg.line < v_line:
                    unexpected.append(msg)

            assert not unexpected, f"Unexpected LoD violations in SAFE_ZONE: {unexpected}"

    def test_violation_zone_fails(self) -> None:
        """Verify exhaustive violations are caught in VIOLATION_ZONE."""
        with open("tests/benchmarks/lod-samples.py") as f:
            content = f.read()

        node = astroid.parse(content)
        self.walk(node)

        v_line: int = 0
        for i, line in enumerate(content.splitlines()):
            if "VIOLATION_ZONE" in line:
                v_line = i + 1
                break

        v_count: int = 0
        for msg in self.linter.release_messages():
            if msg.msg_id in ["clean-arch-demeter", "W9006"] and msg.line >= v_line:
                v_count += 1

        assert v_count >= 2, f"Expected at least 2 LoD violations in VIOLATION_ZONE, found {v_count}"
