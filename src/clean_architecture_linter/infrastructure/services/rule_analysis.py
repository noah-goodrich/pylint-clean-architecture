"""Service for analyzing rule fixability across adapters."""

from typing import Any


class RuleFixabilityService:
    """Service for determining rule fixability across adapters."""

    def is_rule_fixable(self, adapter: Any, code: str) -> bool:
        """
        Check if adapter can auto-fix this rule code.

        Args:
            adapter: Linter adapter instance
            code: Rule code to check

        Returns:
            True if the adapter can auto-fix this rule code. Ruff uses prefix match.
        """
        if not hasattr(adapter, "supports_autofix") or not adapter.supports_autofix():
            return False
        fixable = getattr(adapter, "get_fixable_rules", lambda: [])()
        if adapter.__class__.__name__ == "RuffAdapter":
            return any(code.startswith(r) for r in fixable)
        return code in fixable
