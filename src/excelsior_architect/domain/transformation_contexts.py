"""Typed context payloads for TransformationPlan. Single source of truth for plan params."""

from typing import TypedDict


class FreezeDataclassContext(TypedDict):
    """Context for FreezeDataclassTransformer."""

    class_name: str


class ImportContext(TypedDict):
    """Context for AddImportTransformer: module and import names."""

    module: str
    imports: list[str]


class ReturnTypeContext(TypedDict):
    """Context for AddReturnTypeTransformer."""

    function_name: str
    return_type: str


class ParameterTypeContext(TypedDict):
    """Context for AddParameterTypeTransformer."""

    function_name: str
    param_name: str
    param_type: str


class GovernanceCommentContext(TypedDict):
    """Context for GovernanceCommentTransformer. source_lines is injected by gateway after construction."""

    rule_code: str
    rule_name: str
    problem: str
    recommendation: str
    context_info: str
    target_line: int


class EmptyContext(TypedDict, total=False):
    """Context for transformers that accept but do not use context (e.g. LifecycleReturnTypeTransformer)."""

    pass


class FilePathContext(TypedDict, total=False):
    """Context for DomainImmutabilityTransformer."""

    file_path: str


# Union of all plan params for TransformationPlan.params
PlanParams = (
    FreezeDataclassContext
    | ImportContext
    | ReturnTypeContext
    | ParameterTypeContext
    | GovernanceCommentContext
)
