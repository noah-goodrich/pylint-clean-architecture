"""Unit tests for PlanFixUseCase."""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from clean_architecture_linter.infrastructure.gateways.artifact_storage_gateway import (
    LocalArtifactStorage,
)
from clean_architecture_linter.infrastructure.gateways.filesystem_gateway import (
    FileSystemGateway,
)
from clean_architecture_linter.use_cases.plan_fix import PlanFixUseCase


class TestPlanFixUseCase:
    """Test plan-fix use case."""

    def test_execute_raises_file_not_found_when_handover_missing(
        self, tmp_path: Path
    ) -> None:
        """When handover JSON does not exist, raise FileNotFoundError."""
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            fs = FileSystemGateway()
            artifact_storage = LocalArtifactStorage(".excelsior", fs)
            use_case = PlanFixUseCase(
                artifact_storage=artifact_storage,
                guidance_service=MagicMock(),
            )
            with pytest.raises(FileNotFoundError) as exc_info:
                use_case.execute("excelsior.W9015", 0, "check")
            assert "Handover not found" in str(exc_info.value)
            assert "check/ai_handover.json" in str(exc_info.value)
        finally:
            os.chdir(original_cwd)

    def test_execute_writes_fix_plan_when_handover_has_matching_violation(
        self,
        tmp_path: Path,
    ) -> None:
        """When handover has a violation for rule_id, write fix plan markdown."""
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            excelsior = Path(".excelsior")
            excelsior.mkdir()
            (excelsior / "check").mkdir(exist_ok=True)
            handover = {
                "version": "1.0.0",
                "violations_by_rule": {
                    "W9015": [
                        {
                            "rule_id": "excelsior.W9015",
                            "code": "W9015",
                            "message": "Missing type hint",
                            "locations": ["src/foo.py:10"],
                            "manual_instructions": "Add type hints.",
                            "prompt_fragment": "Fix [excelsior.W9015]: ...",
                        },
                    ],
                },
            }
            (excelsior / "check" / "ai_handover.json").write_text(
                json.dumps(handover), encoding="utf-8"
            )

            fs = FileSystemGateway()
            artifact_storage = LocalArtifactStorage(".excelsior", fs)
            guidance = MagicMock()
            guidance.get_entry.return_value = None
            use_case = PlanFixUseCase(
                artifact_storage=artifact_storage, guidance_service=guidance)
            out_key = use_case.execute("excelsior.W9015", 0, "check")

            assert "fix_plans" in out_key
            assert "excelsior_W9015" in out_key
            assert out_key.endswith(".md")
            content = Path(".excelsior").joinpath(out_key).read_text()
            assert "# Fix plan: excelsior.W9015" in content
            assert "Missing type hint" in content
            assert "src/foo.py:10" in content
            assert "Add type hints." in content
            assert "Prompt fragment" in content
            assert "excelsior check" in content
        finally:
            os.chdir(original_cwd)
