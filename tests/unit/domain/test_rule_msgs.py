"""Unit tests for RuleMsgBuilder (domain/rule_msgs.py)."""

import unittest

from excelsior_architect.domain.constants import EXCELSIOR_PREFIX
from excelsior_architect.domain.rule_msgs import RuleMsgBuilder


def _registry(*entries: tuple[str, dict[str, object]]) -> dict[str, object]:
    """Build a registry dict from (key, value) pairs."""
    return dict(entries)


class TestRuleMsgBuilderGetEntry(unittest.TestCase):
    """Tests for RuleMsgBuilder.get_entry."""

    def test_returns_entry_when_key_is_excelsior_code(self) -> None:
        """get_entry returns entry when registry key is excelsior.{rule_code}."""
        registry = _registry(
            (f"{EXCELSIOR_PREFIX}W9006", {
                "symbol": "clean-arch-demeter",
                "display_name": "Law of Demeter",
                "message_template": "Law of Demeter: %s",
            }),
        )
        entry = RuleMsgBuilder.get_entry(registry, "W9006")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.get("symbol"), "clean-arch-demeter")
        self.assertEqual(entry.get("message_template"), "Law of Demeter: %s")

    def test_returns_entry_when_lookup_by_symbol(self) -> None:
        """get_entry returns entry when rule_code is the symbol (not code)."""
        registry = _registry(
            (f"{EXCELSIOR_PREFIX}W9006", {
                "symbol": "clean-arch-demeter",
                "display_name": "Law of Demeter",
                "message_template": "Law of Demeter: %s",
            }),
        )
        entry = RuleMsgBuilder.get_entry(registry, "clean-arch-demeter")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.get("symbol"), "clean-arch-demeter")

    def test_returns_none_for_empty_registry(self) -> None:
        """get_entry returns None when registry is empty."""
        entry = RuleMsgBuilder.get_entry({}, "W9006")
        self.assertIsNone(entry)

    def test_returns_none_for_unknown_rule_code(self) -> None:
        """get_entry returns None when rule_code is not in registry."""
        registry = _registry(
            (f"{EXCELSIOR_PREFIX}W9010", {"symbol": "clean-arch-god-file"}),
        )
        entry = RuleMsgBuilder.get_entry(registry, "W9999")
        self.assertIsNone(entry)

    def test_returns_none_when_entry_is_not_dict(self) -> None:
        """get_entry returns None when registry value is not a dict."""
        registry = {f"{EXCELSIOR_PREFIX}W9006": "not a dict"}
        entry = RuleMsgBuilder.get_entry(registry, "W9006")
        self.assertIsNone(entry)

    def test_skips_excelsior_default_when_matching_by_symbol(self) -> None:
        """get_entry does not return excelsior._default when matching by symbol."""
        registry = _registry(
            (f"{EXCELSIOR_PREFIX}_default", {
                "symbol": "default",
                "short_description": "Default",
            }),
            (f"{EXCELSIOR_PREFIX}W9006", {
                "symbol": "clean-arch-demeter",
                "message_template": "Demeter: %s",
            }),
        )
        entry = RuleMsgBuilder.get_entry(registry, "clean-arch-demeter")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.get("symbol"), "clean-arch-demeter")
        entry_default = RuleMsgBuilder.get_entry(registry, "default")
        self.assertIsNone(entry_default)

    def test_returns_copy_of_entry(self) -> None:
        """get_entry returns a copy; mutating it does not affect registry."""
        registry = _registry(
            (f"{EXCELSIOR_PREFIX}W9006", {
                "symbol": "clean-arch-demeter",
                "message_template": "Demeter: %s",
            }),
        )
        entry = RuleMsgBuilder.get_entry(registry, "W9006")
        self.assertIsNotNone(entry)
        entry["symbol"] = "mutated"
        self.assertEqual(
            registry[f"{EXCELSIOR_PREFIX}W9006"].get("symbol"),
            "clean-arch-demeter",
        )


class TestRuleMsgBuilderBuildMsgsForCodes(unittest.TestCase):
    """Tests for RuleMsgBuilder.build_msgs_for_codes."""

    def test_returns_single_entry_with_full_metadata(self) -> None:
        """build_msgs_for_codes returns (message_template, symbol, description) for one code."""
        registry = _registry(
            (f"{EXCELSIOR_PREFIX}W9006", {
                "symbol": "clean-arch-demeter",
                "display_name": "Law of Demeter",
                "message_template": "Law of Demeter: %s",
            }),
        )
        result = RuleMsgBuilder.build_msgs_for_codes(registry, ["W9006"])
        self.assertEqual(len(result), 1)
        self.assertIn("W9006", result)
        msg, symbol, desc = result["W9006"]
        self.assertEqual(msg, "Law of Demeter: %s")
        self.assertEqual(symbol, "clean-arch-demeter")
        self.assertEqual(desc, "Law of Demeter")

    def test_returns_multiple_entries_for_multiple_codes(self) -> None:
        """build_msgs_for_codes returns one tuple per code that has message_template."""
        registry = _registry(
            (f"{EXCELSIOR_PREFIX}W9006", {
                "symbol": "clean-arch-demeter",
                "display_name": "Law of Demeter",
                "message_template": "Demeter: %s",
            }),
            (f"{EXCELSIOR_PREFIX}W9010", {
                "symbol": "clean-arch-god-file",
                "display_name": "God File",
                "message_template": "God File: %s",
            }),
        )
        result = RuleMsgBuilder.build_msgs_for_codes(
            registry, ["W9006", "W9010"])
        self.assertEqual(len(result), 2)
        self.assertEqual(result["W9006"][0], "Demeter: %s")
        self.assertEqual(result["W9010"][0], "God File: %s")

    def test_uses_short_description_when_display_name_missing(self) -> None:
        """build_msgs_for_codes uses short_description when display_name is absent."""
        registry = _registry(
            (f"{EXCELSIOR_PREFIX}W9003", {
                "symbol": "clean-arch-protected",
                "short_description": "Access to protected member",
                "message_template": "Protected: %s",
            }),
        )
        result = RuleMsgBuilder.build_msgs_for_codes(registry, ["W9003"])
        self.assertEqual(result["W9003"][2], "Access to protected member")

    def test_uses_code_as_symbol_when_symbol_missing_in_entry(self) -> None:
        """build_msgs_for_codes uses rule code as symbol when entry has no symbol."""
        registry = _registry(
            (f"{EXCELSIOR_PREFIX}W9006", {
                "display_name": "Law of Demeter",
                "message_template": "Demeter: %s",
            }),
        )
        result = RuleMsgBuilder.build_msgs_for_codes(registry, ["W9006"])
        self.assertEqual(result["W9006"][1], "W9006")

    def test_uses_code_as_description_when_both_display_and_short_missing(self) -> None:
        """build_msgs_for_codes uses rule code as description when no display/short."""
        registry = _registry(
            (f"{EXCELSIOR_PREFIX}W9006", {"message_template": "Demeter: %s"}),
        )
        result = RuleMsgBuilder.build_msgs_for_codes(registry, ["W9006"])
        self.assertEqual(result["W9006"][2], "W9006")

    def test_skips_code_with_no_message_template(self) -> None:
        """build_msgs_for_codes omits code when entry has no message_template."""
        registry = _registry(
            (f"{EXCELSIOR_PREFIX}W9006", {
                "symbol": "clean-arch-demeter",
                "display_name": "Law of Demeter",
            }),
        )
        result = RuleMsgBuilder.build_msgs_for_codes(registry, ["W9006"])
        self.assertEqual(len(result), 0)

    def test_skips_unknown_code(self) -> None:
        """build_msgs_for_codes omits code when get_entry returns None."""
        registry = _registry(
            (f"{EXCELSIOR_PREFIX}W9010", {
                "symbol": "clean-arch-god-file",
                "message_template": "God: %s",
            }),
        )
        result = RuleMsgBuilder.build_msgs_for_codes(
            registry, ["W9010", "W9999"])
        self.assertEqual(len(result), 1)
        self.assertIn("W9010", result)
        self.assertNotIn("W9999", result)

    def test_returns_empty_dict_for_empty_codes_list(self) -> None:
        """build_msgs_for_codes returns {} when codes is empty."""
        registry = _registry(
            (f"{EXCELSIOR_PREFIX}W9006", {"message_template": "Demeter: %s"}),
        )
        result = RuleMsgBuilder.build_msgs_for_codes(registry, [])
        self.assertEqual(result, {})

    def test_returns_empty_dict_for_empty_registry(self) -> None:
        """build_msgs_for_codes returns {} when registry is empty."""
        result = RuleMsgBuilder.build_msgs_for_codes({}, ["W9006", "W9010"])
        self.assertEqual(result, {})

    def test_all_values_are_tuples_of_three_strings(self) -> None:
        """build_msgs_for_codes returns dict of (str, str, str) for Pylint msgs."""
        registry = _registry(
            (f"{EXCELSIOR_PREFIX}W9006", {
                "symbol": "clean-arch-demeter",
                "display_name": "Law of Demeter",
                "message_template": "Law of Demeter: %s",
            }),
        )
        result = RuleMsgBuilder.build_msgs_for_codes(registry, ["W9006"])
        for code, triple in result.items():
            self.assertIsInstance(code, str)
            self.assertIsInstance(triple, tuple)
            self.assertEqual(len(triple), 3)
            self.assertIsInstance(triple[0], str)
            self.assertIsInstance(triple[1], str)
            self.assertIsInstance(triple[2], str)
