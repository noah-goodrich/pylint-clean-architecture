"""Unit tests for RuleFixabilityService."""

from unittest.mock import Mock

from clean_architecture_linter.infrastructure.services.rule_analysis import RuleFixabilityService


class TestRuleFixabilityService:
    """Test RuleFixabilityService rule fixability logic."""

    def test_is_rule_fixable_returns_false_when_adapter_has_no_supports_autofix(self) -> None:
        """Test that fixability check returns False when supports_autofix returns False."""
        service = RuleFixabilityService()
        adapter = Mock()
        adapter.supports_autofix.return_value = False

        result = service.is_rule_fixable(adapter, "W9015")
        assert result is False

    def test_is_rule_fixable_returns_false_when_supports_autofix_returns_false(self) -> None:
        """Test that fixability check returns False when supports_autofix returns False."""
        service = RuleFixabilityService()
        adapter = Mock()
        adapter.supports_autofix.return_value = False

        result = service.is_rule_fixable(adapter, "W9015")
        assert result is False

    def test_is_rule_fixable_returns_true_when_code_in_fixable_rules(self) -> None:
        """Test that fixability check returns True when code is in fixable rules list."""
        service = RuleFixabilityService()
        adapter = Mock()
        adapter.supports_autofix.return_value = True
        adapter.get_fixable_rules.return_value = ["W9015", "W9006"]
        adapter.__class__.__name__ = "ExcelsiorAdapter"

        result = service.is_rule_fixable(adapter, "W9015")
        assert result is True

    def test_is_rule_fixable_returns_false_when_code_not_in_fixable_rules(self) -> None:
        """Test that fixability check returns False when code is not in fixable rules list."""
        service = RuleFixabilityService()
        adapter = Mock()
        adapter.supports_autofix.return_value = True
        adapter.get_fixable_rules.return_value = ["W9015", "W9006"]
        adapter.__class__.__name__ = "ExcelsiorAdapter"

        result = service.is_rule_fixable(adapter, "W9999")
        assert result is False

    def test_is_rule_fixable_uses_prefix_match_for_ruff_adapter(self) -> None:
        """Test that RuffAdapter uses prefix matching with unsafe/unfixable exclusions."""
        service = RuleFixabilityService()
        adapter = Mock()
        adapter.supports_autofix.return_value = True
        adapter.get_fixable_rules.return_value = ["E", "F", "I"]
        adapter.get_unfixable_or_unsafe_ruff_codes.return_value = {
            "E501", "F821", "F841", "B018"}
        adapter.__class__.__name__ = "RuffAdapter"

        # Should match prefix for safe-fix rules
        assert service.is_rule_fixable(adapter, "F401") is True
        assert service.is_rule_fixable(adapter, "I001") is True
        # Exclusions (not fixable without unsafe fixes / manual)
        assert service.is_rule_fixable(adapter, "E501") is False
        assert service.is_rule_fixable(adapter, "F841") is False
        assert service.is_rule_fixable(adapter, "W9015") is False

    def test_is_rule_fixable_handles_missing_get_fixable_rules_gracefully(self) -> None:
        """Test that fixability check handles missing get_fixable_rules method."""
        service = RuleFixabilityService()
        adapter = Mock()
        adapter.supports_autofix.return_value = True
        adapter.__class__.__name__ = "ExcelsiorAdapter"
        # Remove get_fixable_rules attribute so getattr returns the lambda
        del adapter.get_fixable_rules

        result = service.is_rule_fixable(adapter, "W9015")
        assert result is False

    def test_is_rule_fixable_handles_empty_fixable_rules_list(self) -> None:
        """Test that fixability check returns False when fixable rules list is empty."""
        service = RuleFixabilityService()
        adapter = Mock()
        adapter.supports_autofix.return_value = True
        adapter.get_fixable_rules.return_value = []
        adapter.__class__.__name__ = "ExcelsiorAdapter"

        result = service.is_rule_fixable(adapter, "W9015")
        assert result is False
