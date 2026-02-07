"""Adapters for linter outputs."""

from excelsior_architect.domain.entities import LinterResult
from excelsior_architect.infrastructure.adapters.excelsior_adapter import ExcelsiorAdapter
from excelsior_architect.infrastructure.adapters.import_linter_adapter import ImportLinterAdapter
from excelsior_architect.infrastructure.adapters.mypy_adapter import MypyAdapter

__all__ = ["ExcelsiorAdapter", "ImportLinterAdapter",
           "LinterResult", "MypyAdapter"]
