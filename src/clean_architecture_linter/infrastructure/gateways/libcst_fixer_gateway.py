"""LibCST based Fixer Gateway."""

from typing import Any, Union

import libcst as cst

from clean_architecture_linter.domain.entities import TransformationPlan, TransformationType
from clean_architecture_linter.domain.protocols import FixerGatewayProtocol
from clean_architecture_linter.infrastructure.gateways.transformers import (
    AddImportTransformer,
    AddParameterTypeTransformer,
    AddReturnTypeTransformer,
    FreezeDataclassTransformer,
    GovernanceCommentTransformer,
)


class LibCSTFixerGateway(FixerGatewayProtocol):
    """Gateway for applying safe code modifications using LibCST."""

    def _plan_to_transformer(self, plan: TransformationPlan) -> cst.CSTTransformer:
        """Convert a TransformationPlan to a LibCST transformer."""
        params = plan.params
        t = plan.transformation_type
        if t == TransformationType.FREEZE_DATACLASS:
            return FreezeDataclassTransformer(params)
        elif t == TransformationType.ADD_IMPORT:
            return AddImportTransformer(params)
        elif t == TransformationType.ADD_RETURN_TYPE:
            return AddReturnTypeTransformer(params)
        elif t == TransformationType.ADD_PARAMETER_TYPE:
            return AddParameterTypeTransformer(params)
        elif t == TransformationType.ADD_GOVERNANCE_COMMENT:
            return GovernanceCommentTransformer(params)
        else:
            raise ValueError(f"Unknown transformation type: {plan.transformation_type}")

    def apply_fixes(
        self, file_path: str, fixes: list[Union[cst.CSTTransformer, TransformationPlan, Any]]
    ) -> bool:
        """
        Apply a list of fixes to a file.

        Args:
            file_path: Path to the file to modify
            fixes: List of LibCST transformers or TransformationPlans to apply

        Returns:
            True if the file was modified, False otherwise
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                source = f.read()
            source_lines = source.splitlines()
            module = cst.parse_module(source)
            original_code = module.code

            # Convert TransformationPlans to transformers and apply all
            for fix in fixes:
                if fix is None:
                    continue

                # Convert plan to transformer if needed
                if isinstance(fix, TransformationPlan):
                    transformer = self._plan_to_transformer(fix)
                else:
                    transformer = fix

                # If transformer needs source_lines, inject them
                if hasattr(transformer, "source_lines") and not transformer.source_lines:
                    transformer.source_lines = source_lines
                module = module.visit(transformer)

            # Only write if code changed
            if module.code != original_code:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(module.code)
                return True
            return False
        except Exception:
            return False

