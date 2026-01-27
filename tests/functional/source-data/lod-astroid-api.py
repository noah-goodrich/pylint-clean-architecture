"""LoD exemptions for astroid API usage. These must NOT be flagged.

Mimics: immutability.py:59 (node.locals.get), contracts.py:91 (method.name.startswith).
Requires resolving built-in attributes (ClassDef.locals, FunctionDef.name) via typeshed/astroid.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from astroid.nodes import ClassDef, FunctionDef


def classdef_locals_get(node: "ClassDef", key: str) -> list:
    # Allowed: ClassDef.locals is a dict-like (astroid API); .get is the right usage. (immutability.py:59)
    return list(node.locals.get(key, []))


def functiondef_name_startswith(method: FunctionDef, prefix: str) -> bool:
    # Allowed: FunctionDef.name is str; .startswith is str method. (contracts.py:91)
    return method.name.startswith(prefix)
