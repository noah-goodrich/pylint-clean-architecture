"""Adapters for linter outputs."""

from clean_architecture_linter.domain.entities import LinterResult
from clean_architecture_linter.infrastructure.adapters.mypy_adapter import MypyAdapter
from clean_architecture_linter.infrastructure.adapters.excelsior_adapter import ExcelsiorAdapter
from clean_architecture_linter.infrastructure.adapters.import_linter_adapter import ImportLinterAdapter

__all__ = ["LinterResult", "MypyAdapter", "ExcelsiorAdapter", "ImportLinterAdapter"]
