"""Tests for multi-pass fix refinement with cache clearing and LoD resolution."""

from unittest.mock import MagicMock, patch

from clean_architecture_linter.domain.rules.governance_comments import LawOfDemeterRule
from clean_architecture_linter.domain.rules.immutability import DomainImmutabilityRule
from clean_architecture_linter.domain.rules.type_hints import MissingTypeHintRule
from clean_architecture_linter.infrastructure.gateways.filesystem_gateway import FileSystemGateway
from clean_architecture_linter.use_cases.apply_fixes import ApplyFixesUseCase


class TestMultiPassRefinement:
    """Test multi-pass fix refinement with cache clearing."""

    def test_multi_pass_clears_cache_after_type_hints(self) -> None:
        """Test that astroid cache is cleared after Pass 2 (type hints)."""
        fixer_gateway = MagicMock()
        filesystem = FileSystemGateway()
        astroid_gateway = MagicMock()
        telemetry = MagicMock()
        use_case = ApplyFixesUseCase(
            fixer_gateway, filesystem, astroid_gateway=astroid_gateway, telemetry=telemetry
        )

        with patch.object(use_case, '_run_baseline_if_enabled'), \
                patch.object(use_case, '_execute_pass1_ruff', return_value=0), \
                patch.object(use_case, '_execute_pass2_type_hints', return_value=1), \
                patch.object(use_case, '_execute_pass3_architecture_code', return_value=0), \
                patch.object(use_case, '_execute_pass4_governance_comments', return_value=0):
            use_case.execute_multi_pass([], "test_path")

        # Verify cache was cleared after Pass 2
        astroid_gateway.clear_inference_cache.assert_called_once()
        telemetry.step.assert_any_call(
            "🔄 Pass 1–2 complete. Cleared astroid cache. Re-inferring architecture for Pass 3…"
        )

    def test_multi_pass_phases_execute_in_order(self) -> None:
        """Test that multi-pass executes phases in correct order."""
        fixer_gateway = MagicMock()
        filesystem = FileSystemGateway()
        telemetry = MagicMock()
        use_case = ApplyFixesUseCase(
            fixer_gateway, filesystem, telemetry=telemetry)

        call_order = []

        def track_pass1(*args, **kwargs) -> int:
            call_order.append("pass1")
            return 1

        def track_pass2(*args, **kwargs) -> int:
            call_order.append("pass2")
            return 2

        def track_cache_clear(*args, **kwargs):
            call_order.append("clear_cache")

        def track_pass3(*args, **kwargs) -> int:
            call_order.append("pass3")
            return 3

        def track_pass4(*args, **kwargs) -> int:
            call_order.append("pass4")
            return 4

        with patch.object(use_case, '_run_baseline_if_enabled'), \
                patch.object(use_case, '_execute_pass1_ruff', side_effect=track_pass1), \
                patch.object(use_case, '_execute_pass2_type_hints', side_effect=track_pass2), \
                patch.object(use_case, '_clear_astroid_cache', side_effect=track_cache_clear), \
                patch.object(use_case, '_execute_pass3_architecture_code', side_effect=track_pass3), \
                patch.object(use_case, '_execute_pass4_governance_comments', side_effect=track_pass4):
            result = use_case.execute_multi_pass([], "test_path")

        assert result == 10  # 1 + 2 + 3 + 4
        assert call_order == ["pass1", "pass2",
                              "clear_cache", "pass3", "pass4"]

    def test_pass3_excludes_w9015_and_w9006(self) -> None:
        """Test that Pass 3 excludes W9015 (type hints) and W9006 (LoD comments)."""
        fixer_gateway = MagicMock()
        filesystem = FileSystemGateway()
        telemetry = MagicMock()
        use_case = ApplyFixesUseCase(
            fixer_gateway, filesystem, telemetry=telemetry)

        w9015_rule = MissingTypeHintRule(MagicMock())
        w9015_rule.code = "W9015"
        w9015_rule.fix_type = "code"

        lod_rule = LawOfDemeterRule()
        lod_rule.code = "W9006"
        lod_rule.fix_type = "comment"

        immutability_rule = DomainImmutabilityRule()
        immutability_rule.code = "W9601"
        immutability_rule.fix_type = "code"

        rules = [w9015_rule, lod_rule, immutability_rule]

        architecture_rules = use_case._get_architecture_code_rules(rules)

        # Should include W9601 but exclude W9015 and W9006
        rule_codes = [r.code for r in architecture_rules]
        assert "W9601" in rule_codes
        assert "W9015" not in rule_codes
        assert "W9006" not in rule_codes

    def test_pass4_only_processes_w9006(self, tmp_path) -> None:
        """Test that Pass 4 only processes W9006 violations for governance comments."""
        test_file = tmp_path / "example.py"
        test_file.write_text("x = obj.a.b.c()\n")

        fixer_gateway = MagicMock()
        fixer_gateway.apply_fixes.return_value = True
        filesystem = FileSystemGateway()
        from clean_architecture_linter.infrastructure.gateways.astroid_gateway import AstroidGateway
        astroid_gateway = AstroidGateway()
        telemetry = MagicMock()
        check_audit = MagicMock()

        # Create mock audit result with W9006 violation
        from clean_architecture_linter.domain.entities import LinterResult
        lod_result = LinterResult(
            code="W9006",
            message="Law of Demeter: Chain access (obj.a.b.c) exceeds one level",
            locations=[f"{test_file}:1:1"]
        )

        mock_audit_result = MagicMock()
        mock_audit_result.is_blocked = lambda: False
        mock_audit_result.excelsior_results = [lod_result]
        check_audit.execute.return_value = mock_audit_result

        use_case = ApplyFixesUseCase(
            fixer_gateway,
            filesystem,
            astroid_gateway=astroid_gateway,
            telemetry=telemetry,
            check_audit_use_case=check_audit,
            validate_with_tests=False
        )

        with patch.object(use_case, '_apply_transformers_to_file', return_value=1):
            result = use_case._execute_pass4_governance_comments(
                [], str(tmp_path))

        assert result == 1
        telemetry.step.assert_any_call(
            "Pass 4: Applying governance comments for architectural violations..."
        )


class TestDomainImmutabilityFix:
    """Test Domain Immutability Rule (W9601) fix implementation."""

    def test_domain_immutability_rule_has_fix_type_code(self) -> None:
        """Test that DomainImmutabilityRule has fix_type='code'."""
        rule = DomainImmutabilityRule()
        assert rule.fix_type == "code"
        assert rule.code == "W9601"

    def test_domain_immutability_rule_aborts_on_custom_setattr(self) -> None:
        """Test that fix() aborts when custom __setattr__ is detected."""
        rule = DomainImmutabilityRule()
        import astroid

        from clean_architecture_linter.domain.rules import Violation

        # Create a class with custom __setattr__
        source = """
class User:
    def __setattr__(self, name, value):
        super().__setattr__(name, value)
"""
        module = astroid.parse(source)
        class_node = module.body[0]

        violation = Violation(
            code="W9601",
            message="Domain Immutability Violation",
            location="test.py:2:1",
            node=class_node,
            fixable=True
        )

        transformer = rule.fix(violation)

        # Should return None when custom __setattr__ is detected
        assert transformer is None

    def test_domain_immutability_rule_returns_transformer_for_valid_class(self) -> None:
        """Test that fix() returns transformer for valid Domain class."""
        rule = DomainImmutabilityRule()
        import astroid

        from clean_architecture_linter.domain.rules import Violation

        # Create a class without custom __setattr__
        source = """
class User:
    name: str
    age: int
"""
        module = astroid.parse(source)
        class_node = module.body[0]

        violation = Violation(
            code="W9601",
            message="Domain Immutability Violation",
            location="test.py:2:1",
            node=class_node,
            fixable=True
        )

        transformer = rule.fix(violation)

        assert transformer is not None
        assert hasattr(transformer, 'class_name')
        assert transformer.class_name == "User"


class TestLoDCommentOnly:
    """Test that Law of Demeter rule is comment-only."""

    def test_lod_rule_has_fix_type_comment(self) -> None:
        """Test that LawOfDemeterRule has fix_type='comment'."""
        rule = LawOfDemeterRule()
        assert rule.fix_type == "comment"
        assert rule.code == "W9006"

    def test_lod_rule_injects_comment_not_code(self, tmp_path) -> None:
        """Test that LoD rule injects comment without changing code logic."""
        test_file = tmp_path / "example.py"
        original_code = "result = repo.session.query(User).filter(User.id == 1).first()\n"
        test_file.write_text(original_code)

        rule = LawOfDemeterRule()
        import astroid

        node = astroid.parse(original_code).body[0].value

        violation = MagicMock()
        violation.code = "W9006"
        violation.message = "Law of Demeter: Chain access (repo.session.query) exceeds one level"
        violation.location = f"{test_file}:1:1"
        violation.node = node

        transformer = rule.fix(violation)

        assert transformer is not None
        assert transformer.target_line == 1

        # Apply transformer and verify code logic unchanged
        import libcst as cst
        module = cst.parse_module(original_code)
        modified = module.visit(transformer)

        # Code should still contain the original logic
        assert "repo.session.query" in modified.code
        # But should have governance comment
        assert "EXCELSIOR: W9006" in modified.code
        assert "Law of Demeter" in modified.code
