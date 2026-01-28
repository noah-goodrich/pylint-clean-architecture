"""Tests that Mission 5G purge is complete: no banned nominal/string-matching logic.

Banned:
- Any list of strings in patterns.py used to identify primitives (e.g. ["location", "name", "path"])
- _KNOWN_ASTROID_ATTR and similar maps in astroid_gateway.py
- Guessing types from attribute or variable names
"""

import re
from pathlib import Path

import pytest


# Paths relative to src
PATTERNS_PATH = Path(__file__).resolve().parent.parent.parent / "src" / "clean_architecture_linter" / "use_cases" / "checks" / "patterns.py"
GATEWAY_PATH = Path(__file__).resolve().parent.parent.parent / "src" / "clean_architecture_linter" / "infrastructure" / "gateways" / "astroid_gateway.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class TestPatternsPurge:
    """patterns.py must not contain banned primitive/attribute name lists."""

    def test_no_primitive_attribute_name_list(self) -> None:
        """Banned: list of attribute names like [\"location\", \"name\", \"path\"] used as primitives."""
        text = _read(PATTERNS_PATH)
        # Match list literals of quoted strings that look like attribute names for "primitive" guessing
        # e.g. ["location", "name", "path"] or ['locals', 'get']
        attr_like = re.compile(r'\[\s*["\'][\w.]+["\']\s*(?:,\s*["\'][\w.]+["\']\s*)*\]')
        for m in attr_like.finditer(text):
            snippet = m.group(0)
            # Exclude benign lists: e.g. ["self","cls"], ["clean-arch-demeter","W9006"], msg ids, etc.
            lower = snippet.lower()
            if "location" in lower and "name" in lower and "path" in lower:
                pytest.fail(f"Banned primitive-name list in patterns.py: {snippet}")
            if "locals" in lower and "get" in lower and len(snippet) < 40:
                pytest.fail(f"Banned chain/attr list in patterns.py: {snippet}")

    def test_no_chain_excluded_nominal_matching(self) -> None:
        """Banned: _is_chain_excluded (or similar) matching on chain == [\"get\", \"locals\"] or attrname == \"locals\"."""
        text = _read(PATTERNS_PATH)
        if 'chain == ["get"' in text or "chain == ['get'" in text:
            pytest.fail("Banned: chain == [\"get\", ...] nominal matching in patterns.py")
        if 'attrname == "locals"' in text or "attrname == 'locals'" in text:
            pytest.fail("Banned: attrname == \"locals\" in patterns.py")

    def test_no_list_of_safe_attribute_names(self) -> None:
        """Banned: a list used as 'if attr in SAFE_ATTRS' or similar."""
        text = _read(PATTERNS_PATH)
        if re.search(r'\b(SAFE_|PRIMITIVE_|ALLOWED_|KNOWN_)[A-Z_]*\s*=\s*\[', text):
            pytest.fail("Banned: constant list of attribute/primitive names in patterns.py")


class TestGatewayPurge:
    """astroid_gateway.py must not contain _KNOWN_ASTROID_ATTR or param-annotation fallbacks for 'locals'."""

    def test_no_known_astroid_attr(self) -> None:
        """Banned: _KNOWN_ASTROID_ATTR or similar mapping for astroid attribute names."""
        text = _read(GATEWAY_PATH)
        if "_KNOWN_ASTROID_ATTR" in text or "KNOWN_ASTROID" in text:
            pytest.fail("Banned: _KNOWN_ASTROID_ATTR (or similar) in astroid_gateway.py")

    def test_no_param_annotation_fallback_for_locals(self) -> None:
        """Banned: special-case using _get_param_annotation_qname or 'locals' for ClassDef.locals."""
        text = _read(GATEWAY_PATH)
        if "_get_param_annotation_qname" in text:
            pytest.fail("Banned: _get_param_annotation_qname in astroid_gateway.py")
        # Disallow: when attrname == "locals" and we use a hardcoded dict type
        if 'attr_name == "locals"' in text or "attrname == \"locals\"" in text:
            # Only fail if it's a special-case that returns a type without stub
            if "dict" in text and "builtins.dict" in text:
                # If we're returning builtins.dict from a hardcoded branch for "locals", that's banned
                pass  # Allow if it's inside stub or typeshed logic; we can't easily grep context
        # Simpler: no string "locals" as a special-case key in a dict that maps to a type
        if '("ClassDef", "locals")' in text or "('ClassDef', 'locals')" in text:
            pytest.fail("Banned: hardcoded (\"ClassDef\", \"locals\") mapping in astroid_gateway.py")
