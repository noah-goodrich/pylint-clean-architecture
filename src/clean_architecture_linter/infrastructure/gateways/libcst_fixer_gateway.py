"""LibCST based Fixer Gateway."""

from typing import List

import libcst as cst

from clean_architecture_linter.domain.protocols import FixerGatewayProtocol


class LibCSTFixerGateway(FixerGatewayProtocol):
    """Gateway for applying safe code modifications using LibCST."""

    def apply_fixes(self, file_path: str, transformers: List[cst.CSTTransformer]) -> bool:
        """
        Apply a list of CST transformers to a file.

        Args:
            file_path: Path to the file to modify
            transformers: List of LibCST transformers to apply sequentially

        Returns:
            True if the file was modified, False otherwise
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                source = f.read()
            source_lines = source.splitlines()
            module = cst.parse_module(source)
            original_code = module.code

            # Apply all transformers sequentially
            # Pass source_lines to transformers that need them (e.g., GovernanceCommentTransformer)
            for transformer in transformers:
                if transformer is not None:
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

