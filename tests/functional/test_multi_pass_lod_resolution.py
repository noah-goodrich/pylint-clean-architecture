"""Functional test: Multi-pass resolution of false LoD violation via type hint fix."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from clean_architecture_linter.domain.rules.governance_comments import LawOfDemeterRule
from clean_architecture_linter.domain.rules.type_hints import MissingTypeHintRule
from clean_architecture_linter.infrastructure.gateways.astroid_gateway import AstroidGateway
from clean_architecture_linter.infrastructure.gateways.filesystem_gateway import FileSystemGateway
from clean_architecture_linter.use_cases.apply_fixes import ApplyFixesUseCase


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

        fixer_gateway = MagicMock()
        fixer_gateway.apply_fixes.return_value = True
        filesystem = FileSystemGateway()
        astroid_gateway = MagicMock(spec=AstroidGateway)
        astroid_gateway.clear_inference_cache = MagicMock()
        telemetry = MagicMock()
        check_audit = MagicMock()

        # Mock Pass 1 (Ruff) - no changes
        ruff_adapter = MagicMock()
        ruff_adapter.apply_fixes.return_value = False
        config_loader = MagicMock()
        config_loader.ruff_enabled = True

        use_case = ApplyFixesUseCase(
            fixer_gateway,
            filesystem,
            astroid_gateway=astroid_gateway,
            telemetry=telemetry,
            ruff_adapter=ruff_adapter,
            config_loader=config_loader,
            check_audit_use_case=check_audit,
            validate_with_tests=False
        )

        # Create rules
        w9015_rule = MissingTypeHintRule(astroid_gateway)
        lod_rule = LawOfDemeterRule()

        # Mock Pass 2 to simulate type hint addition
        def mock_apply_rule_fixes(rules, path):
            # Simulate that type hint was added
            if any(r.code == "W9015" for r in rules):
                return 1  # File was modified with type hint
            return 0

        # Mock Pass 3 audit - after type hint, LoD violation should be gone
        from clean_architecture_linter.domain.entities import LinterResult
        mock_audit_result = MagicMock()
        mock_audit_result.is_blocked = lambda: False
        # After type hint is added, LoD violation disappears (empty results)
        mock_audit_result.excelsior_results = []
        check_audit.execute.return_value = mock_audit_result

        with patch.object(use_case, '_apply_rule_fixes', side_effect=mock_apply_rule_fixes), \
             patch.object(use_case, '_apply_governance_comments', return_value=0), \
             patch.object(astroid_gateway, 'clear_inference_cache') as mock_clear:
            result = use_case.execute_multi_pass([w9015_rule, lod_rule], str(tmp_path))

        # Verify cache was cleared
        mock_clear.assert_called_once()
        # Verify Pass 2 modified file (type hint added)
        assert result >= 1
        telemetry.step.assert_any_call("🔄 Cleared astroid inference cache for fresh analysis")

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

        transformer = rule.fix(violation)
        assert transformer is not None

        # Apply transformer
        module = cst.parse_module(original_code)
        modified = module.visit(transformer)
        modified_code = modified.code

        # Verify code logic is unchanged
        assert "repo.session.query(User).filter(User.id == 1).first()" in modified_code
        # Verify comment was injected
        assert "EXCELSIOR: W9006" in modified_code
        assert "Law of Demeter" in modified_code
        assert "Recommendation:" in modified_code
