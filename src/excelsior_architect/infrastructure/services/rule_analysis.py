"""Service for analyzing rule fixability across adapters."""

from excelsior_architect.domain.protocols import LinterAdapterProtocol


class RuleFixabilityService:
    """Service for determining rule fixability across adapters."""

    def is_rule_fixable(self, adapter: LinterAdapterProtocol, code: str) -> bool:
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
        fixable: list[str] = getattr(
            adapter, "get_fixable_rules", lambda: [])()
        if adapter.__class__.__name__ == "RuffAdapter":
            unfixable: set[str] = getattr(
                adapter, "get_unfixable_or_unsafe_ruff_codes", lambda: set()
            )()
            if code in unfixable:
                return False
            return any(code.startswith(r) for r in fixable)
        return code in fixable
