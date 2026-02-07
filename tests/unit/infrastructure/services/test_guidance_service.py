"""Unit tests for GuidanceService."""

import unittest
from pathlib import Path

from excelsior_architect.infrastructure.services.guidance_service import (
    GuidanceService,
)


class TestGuidanceService(unittest.TestCase):
    """Test GuidanceService loads registry and returns manual_instructions / proactive_guidance."""

    def setUp(self) -> None:
        """Use default packaged registry path."""
        self.service = GuidanceService()

    def test_get_manual_instructions_mypy_type_arg(self) -> None:
        """Registry returns manual_instructions for mypy.type-arg."""
        text = self.service.get_manual_instructions("mypy", "type-arg")
        self.assertIn("type annotation", text)
        self.assertIn("typing.List", text)

    def test_get_manual_instructions_unknown_falls_back_to_default(self) -> None:
        """Unknown rule code falls back to linter _default."""
        text = self.service.get_manual_instructions("mypy", "unknown-code-xyz")
        self.assertIn("mypy", text.lower() or "Fix" in text)

    def test_get_proactive_guidance_mypy_type_arg(self) -> None:
        """Registry returns proactive_guidance for mypy.type-arg."""
        text = self.service.get_proactive_guidance("mypy", "type-arg")
        self.assertIn("generics", text.lower())
        self.assertIn("type parameters", text.lower())

    def test_get_manual_instructions_excelsior_w9006(self) -> None:
        """Registry returns manual_instructions for excelsior.W9006."""
        text = self.service.get_manual_instructions("excelsior", "W9006")
        self.assertIn("delegated method", text)
        self.assertIn("encapsulation", text)

    def test_get_manual_instructions_import_linter_contract(self) -> None:
        """Registry returns manual_instructions for import_linter.contract."""
        text = self.service.get_manual_instructions(
            "import_linter", "contract")
        self.assertIn("import", text)
        self.assertIn("contract", text.lower())

    def test_init_with_custom_registry_path(self) -> None:
        """Custom registry_path is used when provided."""
        # Use packaged registry path explicitly to hit branch
        from excelsior_architect.infrastructure.services import guidance_service
        _base = Path(guidance_service.__file__).resolve().parent.parent
        custom = str(_base / "resources" / "rule_registry.yaml")
        svc = GuidanceService(registry_path=custom)
        self.assertEqual(svc._path, Path(custom))
        text = svc.get_manual_instructions("mypy", "type-arg")
        self.assertIn("type", text.lower())

    def test_init_with_nonexistent_path_empty_registry(self) -> None:
        """When registry path does not exist, _registry is empty."""
        svc = GuidanceService(registry_path="/nonexistent/rule_registry.yaml")
        self.assertEqual(svc._registry, {})

    def test_get_manual_instructions_fallback_when_no_default(self) -> None:
        """When rule and linter _default are missing, return generic fallback."""
        svc = GuidanceService(registry_path="/nonexistent/rule_registry.yaml")
        text = svc.get_manual_instructions("unknown_linter", "unknown_code")
        self.assertIn("See project docs", text)
        self.assertIn("Fix the violation", text)

    def test_get_proactive_guidance_fallback_when_no_default(self) -> None:
        """When rule and linter _default are missing, return generic fallback."""
        svc = GuidanceService(registry_path="/nonexistent/rule_registry.yaml")
        text = svc.get_proactive_guidance("unknown_linter", "unknown_code")
        self.assertIn("Follow project conventions", text)

    def test_get_entry_returns_entry_when_found(self) -> None:
        """get_entry returns full dict for known rule."""
        entry = self.service.get_entry("mypy", "type-arg")
        self.assertIsNotNone(entry)
        self.assertIsInstance(entry, dict)
        self.assertIn("manual_instructions", entry)

    def test_get_entry_returns_none_when_not_found(self) -> None:
        """get_entry returns None for unknown rule."""
        entry = self.service.get_entry("unknown_linter", "unknown_code")
        self.assertIsNone(entry)

    def test_iter_proactive_guidance_returns_sorted_tuples(self) -> None:
        """iter_proactive_guidance returns (rule_id, short_description, proactive_guidance) sorted."""
        out = self.service.iter_proactive_guidance()
        self.assertIsInstance(out, list)
        for item in out:
            self.assertIsInstance(item, tuple)
            self.assertEqual(len(item), 3)
            rule_id, short, guidance = item
            self.assertIsInstance(rule_id, str)
            self.assertIsInstance(short, str)
            self.assertIsInstance(guidance, str)
        self.assertEqual(out, sorted(out, key=lambda x: x[0]))

    def test_iter_proactive_guidance_skips_default_entries(self) -> None:
        """Entries ending with ._default are not included."""
        out = self.service.iter_proactive_guidance()
        default_entries = [x[0] for x in out if x[0].endswith("._default")]
        self.assertEqual(default_entries, [])
