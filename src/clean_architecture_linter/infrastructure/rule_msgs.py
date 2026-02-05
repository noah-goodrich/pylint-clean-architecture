"""Build Pylint msgs dict from rule_registry.yaml. Single source for checker message tuples. No top-level functions (W9018)."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from clean_architecture_linter.domain.protocols import GuidanceServiceProtocol
    from clean_architecture_linter.infrastructure.services.guidance_service import (
        GuidanceService,
    )


class ExcelsiorRegistryHolder:
    """
    Lazy singleton for Excelsior rule registry (GuidanceService). No top-level functions (W9018).
    """

    _registry: "GuidanceService | None" = None

    @classmethod
    def get_excelsior_registry(cls) -> "GuidanceService":
        """Return GuidanceService singleton. Used by checkers to build msgs."""
        if cls._registry is None:
            from clean_architecture_linter.infrastructure.services.guidance_service import (
                GuidanceService,
            )
            cls._registry = GuidanceService()
        return cls._registry

    @staticmethod
    def build_msgs_for_codes(
        registry: "GuidanceServiceProtocol", codes: list[str]
    ) -> dict[str, tuple[str, str, str]]:
        """Build Pylint msgs dict from registry for given rule codes.

        Returns { code: (message_template, symbol, description) } for use as checker.msgs.
        Skips codes that have no message_template in the registry (fallback not added here).
        """
        result: dict[str, tuple[str, str, str]] = {}
        get_tuple = getattr(registry, "get_message_tuple", None)
        if not callable(get_tuple):
            return result
        for code in codes:
            t = get_tuple(code)
            if t and len(t) == 3:
                result[code] = (str(t[0]), str(t[1]), str(t[2]))
        return result
