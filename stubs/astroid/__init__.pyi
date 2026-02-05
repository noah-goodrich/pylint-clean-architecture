# EXCELSIOR STUB: astroid
# Provides type hints for the untyped astroid package.
# Only covers types actually used in this codebase.

from typing import Any, Iterator

from astroid import nodes as nodes

# Re-export commonly used node types at module level
from astroid.nodes import (
    Arguments as Arguments,
    Assign as Assign,
    AssignAttr as AssignAttr,
    AssignName as AssignName,
    Attribute as Attribute,
    Call as Call,
    ClassDef as ClassDef,
    Const as Const,
    FunctionDef as FunctionDef,
    Global as Global,
    If as If,
    Import as Import,
    ImportFrom as ImportFrom,
    Module as Module,
    Name as Name,
    NodeNG as NodeNG,
    Return as Return,
    Subscript as Subscript,
)

# Exceptions


class InferenceError(Exception):
    ...


class AstroidBuildingError(Exception):
    ...

# Sentinel for failed inference


class _Uninferable:
    def __bool__(self) -> bool: ...
    def __repr__(self) -> str: ...


Uninferable: _Uninferable

# Manager singleton


class AstroidManager:
    prefer_stubs: bool
    def clear_cache(self) -> None: ...
    def ast_from_module_name(self, module_name: str) -> Module: ...


MANAGER: AstroidManager
