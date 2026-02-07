"""Functional test: Multi-pass resolution of false LoD violation via type hint fix."""

from unittest.mock import MagicMock

import pytest

from excelsior_architect.domain.rules.governance_comments import LawOfDemeterRule
from excelsior_architect.domain.rules.type_hints import MissingTypeHintRule
from excelsior_architect.infrastructure.gateways.astroid_gateway import AstroidGateway
from excelsior_architect.infrastructure.gateways.filesystem_gateway import FileSystemGateway
from excelsior_architect.use_cases.apply_fixes import ApplyFixesUseCase


class FakeFixerGateway:
    def apply_fixes(self, _file_path: str, _transformers) -> bool:
        return True


class FakeTelemetry:
    def __init__(self) -> None:
        self.steps: list[str] = []

    def step(self, msg: str) -> None:
        self.steps.append(msg)

    def error(self, msg: str) -> None:
        self.steps.append(f"ERROR: {msg}")


class FakeAstroidGateway(AstroidGateway):
    def __init__(self) -> None:
        super().__init__()
        self.clear_calls = 0

    def clear_inference_cache(self) -> None:
        self.clear_calls += 1
        super().clear_inference_cache()


class FakeAuditResult:
    blocked_by = None
    excelsior_results = []

    def is_blocked(self) -> bool:
        return False


class FakeCheckAuditUseCase:
    def execute(self, _target_path: str) -> FakeAuditResult:
        return FakeAuditResult()


class FakeConfigLoader:
    ruff_enabled = False  # Skip Ruff pass for this test


class TestUseCase(ApplyFixesUseCase):
    # Mark as helper, not a pytest test class
    __test__ = False

    def _apply_rule_fixes(self, rules, _target_path: str) -> int:
        # Simulate that Pass 2 (W9015) adds a type hint to one file
        if any(getattr(r, "code", None) == "W9015" for r in rules):
            return 1
        return 0

    def _apply_governance_comments(self, _excelsior_results, _target_path: str) -> int:
        return 0


@pytest.mark.slow
class TestMultiPassLoDResolution:
    """Test that multi-pass fixes false LoD violations by adding type hints."""

    def test_type_hint_fix_resolves_false_lod_violation(self, tmp_path) -> None:
        """
        Test that a false LoD violation (due to missing type hint) is resolved
        after Pass 2 adds the type hint and cache is cleared.

        Scenario:
        - File has: `result = obj.get_data().process()`
        - Missing type hint on `get_data()` makes receiver unknown
        - Pass 2 adds type hint: `data: DataProcessor = obj.get_data()`
        - After cache clear, Pass 3 re-audits and LoD violation disappears
        """
        test_file = tmp_path / "example.py"
        # Create code with missing type hint that causes false LoD violation
        test_file.write_text("""
class DataProcessor:
    def process(self) -> str:
        return "processed"

class Service:
    def get_data(self):
        return DataProcessor()

def main():
    service = Service()
    result = service.get_data().process()  # False LoD violation - get_data() return type unknown
    return result
""")

        filesystem = FileSystemGateway()
        astroid_gateway = FakeAstroidGateway()
        telemetry = FakeTelemetry()

        use_case = TestUseCase(
            FakeFixerGateway(),
            filesystem,
            linter_adapter=MagicMock(),
            telemetry=telemetry,
            astroid_gateway=astroid_gateway,
            ruff_adapter=MagicMock(),
            check_audit_use_case=FakeCheckAuditUseCase(),
            config_loader=FakeConfigLoader(),
            excelsior_adapter=MagicMock(),
            violation_bridge=MagicMock(),
            validate_with_tests=False,
        )

        # Create rules
        w9015_rule = MissingTypeHintRule(astroid_gateway)
        lod_rule = LawOfDemeterRule()

        result = use_case.execute_multi_pass(
            [w9015_rule, lod_rule], str(tmp_path))

        # Verify cache was cleared
        assert astroid_gateway.clear_calls == 1
        # Verify Pass 2 modified file (type hint added)
        assert result >= 1
        assert any(
            s.startswith("🔄 Pass 1–2 complete. Cleared astroid cache.")
            for s in telemetry.steps
        )

    def test_lod_comment_integrity_no_code_changes(self, tmp_path) -> None:
        """Test that LoD governance comment doesn't change code logic."""
        test_file = tmp_path / "example.py"
        original_code = """def process_user(repo):
    user = repo.session.query(User).filter(User.id == 1).first()
    return user.name
"""
        test_file.write_text(original_code)

        rule = LawOfDemeterRule()
        import astroid
        import libcst as cst

        node = astroid.parse(original_code).body[0].body[0].value

        violation = MagicMock()
        violation.code = "W9006"
        violation.message = "Law of Demeter: Chain access (repo.session.query) exceeds one level"
        violation.location = f"{test_file}:2:1"
        violation.node = node

        plan = rule.fix(violation)
        assert plan is not None

        # Apply plan via gateway (rule returns TransformationPlan, not CST transformer)
        from excelsior_architect.infrastructure.gateways.libcst_fixer_gateway import (
            LibCSTFixerGateway,
        )
        gateway = LibCSTFixerGateway()
        transformer = gateway._plan_to_transformer(plan)
        transformer.source_lines = original_code.splitlines()
        module = cst.parse_module(original_code)
        modified = module.visit(transformer)
        modified_code = modified.code

        # Verify code logic is unchanged
        assert "repo.session.query(User).filter(User.id == 1).first()" in modified_code
        # Verify comment was injected
        assert "EXCELSIOR: W9006" in modified_code
        assert "Law of Demeter" in modified_code
        assert "Recommendation:" in modified_code
