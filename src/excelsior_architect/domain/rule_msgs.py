"""Pure message-building from a registry dict. No I/O or infrastructure imports."""

from collections.abc import Mapping
from typing import cast

from excelsior_architect.domain.constants import EXCELSIOR_PREFIX
from excelsior_architect.domain.registry_types import RuleRegistryEntry


class RuleMsgBuilder:
    """
    Builds Pylint msgs dict from a registry mapping.

    No top-level functions (W9018): only __main__.py and checker.py may have them.
    """

    @staticmethod
    def get_entry(
        registry: Mapping[str, RuleRegistryEntry], rule_code: str
    ) -> RuleRegistryEntry | None:
        """Return registry entry for an Excelsior rule by code or symbol (public API)."""
        rule_id = f"{EXCELSIOR_PREFIX}{rule_code}"
        entry = registry.get(rule_id)
        if isinstance(entry, dict):
            return cast(RuleRegistryEntry, dict(entry))
        for rid, e in registry.items():
            if not rid.startswith(EXCELSIOR_PREFIX) or rid == f"{EXCELSIOR_PREFIX}_default":
                continue
            if isinstance(e, dict) and e.get("symbol") == rule_code:
                return cast(RuleRegistryEntry, dict(e))
        return None

    @staticmethod
    def build_msgs_for_codes(
        registry: Mapping[str, RuleRegistryEntry], codes: list[str]
    ) -> dict[str, tuple[str, str, str]]:
        """Build Pylint msgs dict from a registry mapping for given rule codes.

        Registry keys are e.g. 'excelsior.W9010'; values are RuleRegistryEntry dicts.
        Returns { code: (message_template, symbol, description) } for checker.msgs.
        """
        result: dict[str, tuple[str, str, str]] = {}
        for code in codes:
            entry = RuleMsgBuilder.get_entry(registry, code)
            if entry and entry.get("message_template"):
                msg = entry["message_template"]
                symbol = entry.get("symbol") or code
                desc = (
                    entry.get("display_name")
                    or entry.get("short_description")
                    or code
                )
                result[code] = (str(msg), str(symbol), str(desc))
        return result
