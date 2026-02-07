"""GuidanceService: loads the rule registry and provides manual_instructions and proactive_guidance."""

from pathlib import Path
from typing import cast

import yaml

from excelsior_architect.domain.constants import EXCELSIOR_PREFIX
from excelsior_architect.domain.protocols import GuidanceServiceProtocol
from excelsior_architect.domain.registry_types import RuleRegistryEntry


class GuidanceService(GuidanceServiceProtocol):
    """Loads rule_registry.yaml and provides get_manual_instructions / get_proactive_guidance."""

    def __init__(self, registry_path: str | None = None) -> None:
        if registry_path is not None:
            self._path = Path(registry_path)
        else:
            # Default: packaged resource next to this package
            _base = Path(__file__).resolve().parent.parent
            self._path = _base / "resources" / "rule_registry.yaml"
        self._registry: dict[str, RuleRegistryEntry] = {}
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            with open(self._path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
                self._registry = (
                    cast(dict[str, RuleRegistryEntry],
                         data) if isinstance(data, dict) else {}
                )
        else:
            self._registry = {}

    def get_registry(self) -> dict[str, RuleRegistryEntry]:
        """Return a shallow copy of the loaded registry for use by domain/use_cases."""
        return dict(self._registry)

    def get_excelsior_entry(self, rule_code: str) -> RuleRegistryEntry | None:
        """Return the full registry entry for an Excelsior rule by code or symbol."""
        rule_id = f"{EXCELSIOR_PREFIX}{rule_code}"
        entry = self._registry.get(rule_id)
        if entry:
            return cast(RuleRegistryEntry, dict(entry))
        # Resolve by symbol: find excelsior.* entry whose symbol equals rule_code
        for rid, e in self._registry.items():
            if not rid.startswith(EXCELSIOR_PREFIX) or rid == f"{EXCELSIOR_PREFIX}_default":
                continue
            if e.get("symbol") == rule_code:
                return cast(RuleRegistryEntry, dict(e))
        return None

    def get_fixable_codes(self) -> list[str]:
        """Return list of Excelsior rule codes and symbols that are fixable (from registry)."""
        codes: list[str] = []
        for rule_id, entry in self._registry.items():
            if not rule_id.startswith(EXCELSIOR_PREFIX) or rule_id == f"{EXCELSIOR_PREFIX}_default":
                continue
            if not entry.get("fixable"):
                continue
            code = rule_id[len(EXCELSIOR_PREFIX):]
            codes.append(code)
            symbol = entry.get("symbol")
            if symbol and symbol != code:
                codes.append(symbol)
        return sorted(set(codes))

    def get_comment_only_codes(self) -> list[str]:
        """Return list of Excelsior rule codes and symbols that are comment-only (from registry)."""
        codes: list[str] = []
        for rule_id, entry in self._registry.items():
            if not rule_id.startswith(EXCELSIOR_PREFIX) or rule_id == f"{EXCELSIOR_PREFIX}_default":
                continue
            if not entry.get("comment_only"):
                continue
            code = rule_id[len(EXCELSIOR_PREFIX):]
            codes.append(code)
            symbol = entry.get("symbol")
            if symbol and symbol != code:
                codes.append(symbol)
        return sorted(set(codes))

    def get_message_tuple(self, rule_code: str) -> tuple[str, str, str] | None:
        """Return (message_template, symbol, description) for Pylint msgs, or None."""
        entry = self.get_excelsior_entry(rule_code)
        if not entry:
            return None
        msg = entry.get("message_template")
        symbol = entry.get("symbol") or rule_code
        desc = entry.get("display_name") or entry.get(
            "short_description") or rule_code
        if msg:
            return (str(msg), str(symbol), str(desc))
        return None

    def get_display_name(self, rule_code: str) -> str:
        """Return display name for an Excelsior rule (for governance comments etc.)."""
        entry = self.get_excelsior_entry(rule_code)
        if not entry:
            return rule_code.replace("-", " ").title()
        return str(
            entry.get("display_name")
            or entry.get("short_description")
            or rule_code.replace("-", " ").title()
        )

    def get_manual_instructions(self, linter: str, rule_code: str) -> str:
        """Return manual fix instructions for the given linter and rule code.
        For Excelsior, resolves by code or symbol (single YAML entry per rule).
        """
        entry = self._get_entry_for(linter, rule_code)
        if entry and "manual_instructions" in entry:
            return str(entry["manual_instructions"])
        default_entry = self._registry.get(f"{linter}._default")
        if default_entry and "manual_instructions" in default_entry:
            return str(default_entry["manual_instructions"])
        return "See project docs. Fix the violation at the reported location."

    def get_proactive_guidance(self, linter: str, rule_code: str) -> str:
        """Return proactive guidance (how to write code that avoids the violation).
        For Excelsior, resolves by code or symbol (single YAML entry per rule).
        """
        entry = self._get_entry_for(linter, rule_code)
        if entry and "proactive_guidance" in entry:
            return str(entry["proactive_guidance"])
        default_entry = self._registry.get(f"{linter}._default")
        if default_entry and "proactive_guidance" in default_entry:
            return str(default_entry["proactive_guidance"])
        return "Follow project conventions and fix types/architecture at the reported location."

    def _get_entry_for(self, linter: str, rule_code: str) -> RuleRegistryEntry | None:
        """Return the registry entry for (linter, rule_code). For Excelsior, lookup by code or symbol."""
        rule_id = f"{linter}.{rule_code}"
        entry = self._registry.get(rule_id)
        if entry:
            return cast(RuleRegistryEntry, dict(entry))
        if linter == "excelsior":
            return self.get_excelsior_entry(rule_code)
        return None

    def get_entry(self, linter: str, rule_code: str) -> RuleRegistryEntry | None:
        """Return the full registry entry for the rule, or None.
        For Excelsior, resolves by code or symbol (single YAML entry per rule).
        """
        return self._get_entry_for(linter, rule_code)

    def iter_proactive_guidance(
        self,
    ) -> list[tuple[str, str, str]]:
        """Yield (rule_id, short_description, proactive_guidance) for all registry entries that have proactive_guidance."""
        out: list[tuple[str, str, str]] = []
        for rule_id, entry in self._registry.items():
            if rule_id.endswith("._default"):
                continue
            guidance = entry.get("proactive_guidance")
            if not guidance:
                continue
            short = entry.get("short_description") or rule_id
            out.append((rule_id, str(short), str(guidance)))
        return sorted(out, key=lambda x: x[0])
