"""Unit tests for AuditTrailService."""

import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock

from clean_architecture_linter.domain.config import ConfigurationLoader
from clean_architecture_linter.domain.entities import AuditResult, LinterResult
from clean_architecture_linter.infrastructure.gateways.artifact_storage_gateway import (
    LocalArtifactStorage,
)
from clean_architecture_linter.infrastructure.gateways.filesystem_gateway import FileSystemGateway
from clean_architecture_linter.infrastructure.services.audit_trail import AuditTrailService
from clean_architecture_linter.infrastructure.services.rule_analysis import RuleFixabilityService


class TestAuditTrailService:
    """Test AuditTrailService persistence logic."""

    def test_save_audit_trail_creates_excelsior_directory(self) -> None:
        """Test that .excelsior directory is created if it doesn't exist."""
        telemetry = Mock()
        rule_fixability_service = RuleFixabilityService()
        filesystem = FileSystemGateway()
        artifact_storage = LocalArtifactStorage(".excelsior", filesystem)
        config_loader = ConfigurationLoader({}, {})
        guidance = Mock()
        guidance.get_fixable_codes.return_value = []
        guidance.get_comment_only_codes.return_value = set()
        guidance.get_manual_instructions.return_value = ""
        guidance.get_display_name.return_value = "Rule"
        service = AuditTrailService(
            telemetry, rule_fixability_service, artifact_storage, config_loader,
            guidance_service=guidance, raw_log_port=Mock())

        with TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)

                audit_result = AuditResult()
                service.save_audit_trail(audit_result)

                assert Path(".excelsior").exists()
                assert Path(".excelsior").is_dir()
            finally:
                os.chdir(original_cwd)

    def test_save_audit_trail_creates_json_file(self) -> None:
        """Test that last_audit.json is created."""
        telemetry = Mock()
        rule_fixability_service = RuleFixabilityService()
        filesystem = FileSystemGateway()
        artifact_storage = LocalArtifactStorage(".excelsior", filesystem)
        config_loader = ConfigurationLoader({}, {})
        guidance = Mock()
        guidance.get_fixable_codes.return_value = []
        guidance.get_comment_only_codes.return_value = set()
        guidance.get_manual_instructions.return_value = ""
        guidance.get_display_name.return_value = "Rule"
        service = AuditTrailService(
            telemetry, rule_fixability_service, artifact_storage, config_loader,
            guidance_service=guidance, raw_log_port=Mock())

        with TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                Path(".excelsior").mkdir(exist_ok=True)

                audit_result = AuditResult(
                    mypy_results=[LinterResult(
                        "M001", "Type error", ["file.py:1"])],
                    excelsior_results=[LinterResult(
                        "W9015", "Missing hint", ["file.py:2"])],
                )
                service.save_audit_trail(audit_result)

                json_path = Path(".excelsior/last_audit.json")
                assert json_path.exists()

                import json
                data = json.loads(json_path.read_text())
                assert data["version"] == "2.0.0"
                assert data["summary"]["type_integrity"] == 1
                assert data["summary"]["architectural"] == 1
            finally:
                os.chdir(original_cwd)

    def test_save_audit_trail_creates_txt_file(self) -> None:
        """Test that last_audit.txt is created."""
        telemetry = Mock()
        rule_fixability_service = RuleFixabilityService()
        filesystem = FileSystemGateway()
        artifact_storage = LocalArtifactStorage(".excelsior", filesystem)
        config_loader = ConfigurationLoader({}, {})
        guidance = Mock()
        guidance.get_fixable_codes.return_value = []
        guidance.get_comment_only_codes.return_value = set()
        guidance.get_manual_instructions.return_value = ""
        guidance.get_display_name.return_value = "Rule"
        service = AuditTrailService(
            telemetry, rule_fixability_service, artifact_storage, config_loader,
            guidance_service=guidance, raw_log_port=Mock())

        with TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                Path(".excelsior").mkdir(exist_ok=True)

                audit_result = AuditResult(
                    excelsior_results=[LinterResult(
                        "W9015", "Missing hint", ["file.py:2"])],
                )
                service.save_audit_trail(audit_result)

                txt_path = Path(".excelsior/last_audit.txt")
                assert txt_path.exists()

                content = txt_path.read_text()
                assert "EXCELSIOR v2 AUDIT LOG" in content
                assert "ARCHITECTURAL VIOLATIONS" in content
            finally:
                os.chdir(original_cwd)

    def test_save_audit_trail_includes_fixability_info(self) -> None:
        """Test that fixability information is included in JSON."""
        telemetry = Mock()
        rule_fixability_service = RuleFixabilityService()
        filesystem = FileSystemGateway()
        artifact_storage = LocalArtifactStorage(".excelsior", filesystem)
        config_loader = ConfigurationLoader({}, {})
        guidance = Mock()
        guidance.get_fixable_codes.return_value = []
        guidance.get_comment_only_codes.return_value = set()
        guidance.get_manual_instructions.return_value = ""
        guidance.get_display_name.return_value = "Rule"
        service = AuditTrailService(
            telemetry, rule_fixability_service, artifact_storage, config_loader,
            guidance_service=guidance, raw_log_port=Mock())

        with TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                Path(".excelsior").mkdir(exist_ok=True)

                audit_result = AuditResult(
                    excelsior_results=[LinterResult(
                        "W9015", "Missing hint", ["file.py:2"])],
                )
                service.save_audit_trail(audit_result)

                import json
                json_path = Path(".excelsior/last_audit.json")
                data = json.loads(json_path.read_text())

                violations = data["violations"]["architectural"]
                assert len(violations) == 1
                assert "fixable" in violations[0]
                assert "manual_instructions" in violations[0]
            finally:
                os.chdir(original_cwd)

    def test_save_audit_trail_handles_empty_results(self) -> None:
        """Test that empty audit results are handled correctly."""
        telemetry = Mock()
        rule_fixability_service = RuleFixabilityService()
        filesystem = FileSystemGateway()
        artifact_storage = LocalArtifactStorage(".excelsior", filesystem)
        config_loader = ConfigurationLoader({}, {})
        guidance = Mock()
        guidance.get_fixable_codes.return_value = []
        guidance.get_comment_only_codes.return_value = set()
        guidance.get_manual_instructions.return_value = ""
        guidance.get_display_name.return_value = "Rule"
        service = AuditTrailService(
            telemetry, rule_fixability_service, artifact_storage, config_loader,
            guidance_service=guidance, raw_log_port=Mock())

        with TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                Path(".excelsior").mkdir(exist_ok=True)

                audit_result = AuditResult()
                service.save_audit_trail(audit_result)

                json_path = Path(".excelsior/last_audit.json")
                assert json_path.exists()

                import json
                data = json.loads(json_path.read_text())
                assert data["summary"]["type_integrity"] == 0
                assert data["summary"]["architectural"] == 0
            finally:
                os.chdir(original_cwd)

    def test_save_audit_trail_calls_telemetry(self) -> None:
        """Test that telemetry.step is called with persistence message."""
        telemetry = Mock()
        rule_fixability_service = RuleFixabilityService()
        filesystem = FileSystemGateway()
        artifact_storage = LocalArtifactStorage(".excelsior", filesystem)
        config_loader = ConfigurationLoader({}, {})
        guidance = Mock()
        guidance.get_fixable_codes.return_value = []
        guidance.get_comment_only_codes.return_value = set()
        guidance.get_manual_instructions.return_value = ""
        guidance.get_display_name.return_value = "Rule"
        service = AuditTrailService(
            telemetry, rule_fixability_service, artifact_storage, config_loader,
            guidance_service=guidance, raw_log_port=Mock())

        with TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                Path(".excelsior").mkdir(exist_ok=True)

                audit_result = AuditResult()
                service.save_audit_trail(audit_result)

                telemetry.step.assert_called()
                # Check that the call includes the path
                call_args = [str(call)
                             for call in telemetry.step.call_args_list]
                assert any("Audit Trail persisted" in str(call)
                           for call in call_args)
            finally:
                os.chdir(original_cwd)

    def test_save_audit_trail_handles_ruff_when_disabled(self) -> None:
        """Test that ruff violations are skipped when ruff_enabled is False."""
        telemetry = Mock()
        rule_fixability_service = RuleFixabilityService()
        filesystem = FileSystemGateway()
        artifact_storage = LocalArtifactStorage(".excelsior", filesystem)
        config_loader = ConfigurationLoader({}, {})
        guidance = Mock()
        guidance.get_fixable_codes.return_value = []
        guidance.get_comment_only_codes.return_value = set()
        guidance.get_manual_instructions.return_value = ""
        guidance.get_display_name.return_value = "Rule"
        service = AuditTrailService(
            telemetry, rule_fixability_service, artifact_storage, config_loader,
            guidance_service=guidance, raw_log_port=Mock())

        with TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                Path(".excelsior").mkdir(exist_ok=True)

                audit_result = AuditResult(
                    ruff_results=[LinterResult(
                        "E501", "Line too long", ["file.py:1"])],
                    ruff_enabled=False,
                )
                service.save_audit_trail(audit_result)

                import json
                json_path = Path(".excelsior/last_audit.json")
                data = json.loads(json_path.read_text())
                assert data["violations"]["code_quality"] == []
            finally:
                os.chdir(original_cwd)

    def test_save_ai_handover_creates_json_file(self) -> None:
        """Test that save_ai_handover creates .excelsior/ai_handover.json and returns path."""
        telemetry = Mock()
        rule_fixability_service = RuleFixabilityService()
        filesystem = FileSystemGateway()
        artifact_storage = LocalArtifactStorage(".excelsior", filesystem)
        config_loader = ConfigurationLoader({}, {})
        guidance = Mock()
        guidance.get_fixable_codes.return_value = []
        guidance.get_comment_only_codes.return_value = set()
        guidance.get_manual_instructions.return_value = ""
        guidance.get_display_name.return_value = "Rule"
        service = AuditTrailService(
            telemetry, rule_fixability_service, artifact_storage, config_loader,
            guidance_service=guidance, raw_log_port=Mock())

        with TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                Path(".excelsior").mkdir(exist_ok=True)

                audit_result = AuditResult(
                    ruff_results=[LinterResult(
                        "E501", "Line too long", ["src/foo.py:10"])],
                    excelsior_results=[
                        LinterResult(
                            "W9006",
                            "Law of Demeter",
                            ["src/bar.py:20"],
                        )
                    ],
                    ruff_enabled=True,
                )
                path = service.save_ai_handover(audit_result)

                assert path == "ai_handover.json"
                assert Path(".excelsior", path).exists()
                telemetry.step.assert_called()
                call_str = str(telemetry.step.call_args)
                assert "ai_handover" in call_str or "AI Handover" in call_str
            finally:
                os.chdir(original_cwd)

    def test_save_ai_handover_json_structure(self) -> None:
        """Test that ai_handover.json has version, summary, violations_by_rule, next_steps."""
        telemetry = Mock()
        rule_fixability_service = RuleFixabilityService()
        filesystem = FileSystemGateway()
        artifact_storage = LocalArtifactStorage(".excelsior", filesystem)
        config_loader = ConfigurationLoader({}, {})
        guidance = Mock()
        guidance.get_fixable_codes.return_value = []
        guidance.get_comment_only_codes.return_value = set()
        guidance.get_manual_instructions.return_value = ""
        guidance.get_display_name.return_value = "Rule"
        service = AuditTrailService(
            telemetry, rule_fixability_service, artifact_storage, config_loader,
            guidance_service=guidance, raw_log_port=Mock())

        with TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                Path(".excelsior").mkdir(exist_ok=True)

                audit_result = AuditResult(
                    excelsior_results=[
                        LinterResult("W9015", "Missing hint", ["file.py:2"]),
                    ],
                )
                service.save_ai_handover(audit_result)

                import json
                data = json.loads(
                    Path(".excelsior/ai_handover.json").read_text())
                assert data["version"] == "1.0.0"
                assert "summary" in data
                assert "total_violations" in data["summary"]
                assert "rule_ids" in data
                assert isinstance(data["rule_ids"], list)
                assert "violations_by_rule" in data
                assert "next_steps" in data
                assert "files_with_governance_comments" in data
            finally:
                os.chdir(original_cwd)

    def test_save_ai_handover_includes_rule_id_and_prompt_fragment(self) -> None:
        """Test that each violation in handover has rule_id and prompt_fragment (B+)."""
        telemetry = Mock()
        rule_fixability_service = RuleFixabilityService()
        filesystem = FileSystemGateway()
        artifact_storage = LocalArtifactStorage(".excelsior", filesystem)
        config_loader = ConfigurationLoader({}, {})
        guidance = Mock()
        guidance.get_fixable_codes.return_value = []
        guidance.get_comment_only_codes.return_value = set()
        guidance.get_manual_instructions.return_value = ""
        guidance.get_display_name.return_value = "Rule"
        service = AuditTrailService(
            telemetry, rule_fixability_service, artifact_storage, config_loader,
            guidance_service=guidance, raw_log_port=Mock())

        with TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                Path(".excelsior").mkdir(exist_ok=True)

                audit_result = AuditResult(
                    excelsior_results=[
                        LinterResult(
                            "W9015",
                            "Missing type hint",
                            ["src/foo.py:10"],
                        ),
                    ],
                )
                service.save_ai_handover(audit_result)

                import json
                data = json.loads(
                    Path(".excelsior/ai_handover.json").read_text())
                violations_by_rule = data["violations_by_rule"]
                assert "W9015" in violations_by_rule
                entries = violations_by_rule["W9015"]
                assert len(entries) == 1
                entry = entries[0]
                assert entry["rule_id"] == "excelsior.W9015"
                assert "prompt_fragment" in entry
                frag = entry["prompt_fragment"]
                assert "Fix [excelsior.W9015]" in frag
                assert "Missing type hint" in frag
                assert "src/foo.py:10" in frag
                assert "Instructions:" in frag
            finally:
                os.chdir(original_cwd)

    def test_save_ai_handover_next_steps_when_blocked(self) -> None:
        """Test next_steps when audit is blocked."""
        telemetry = Mock()
        rule_fixability_service = RuleFixabilityService()
        filesystem = FileSystemGateway()
        artifact_storage = LocalArtifactStorage(".excelsior", filesystem)
        config_loader = ConfigurationLoader({}, {})
        guidance = Mock()
        guidance.get_fixable_codes.return_value = []
        guidance.get_comment_only_codes.return_value = set()
        guidance.get_manual_instructions.return_value = ""
        guidance.get_display_name.return_value = "Rule"
        service = AuditTrailService(
            telemetry, rule_fixability_service, artifact_storage, config_loader,
            guidance_service=guidance, raw_log_port=Mock())

        with TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                Path(".excelsior").mkdir(exist_ok=True)

                audit_result = AuditResult(
                    blocked_by="ruff", ruff_enabled=True)
                service.save_ai_handover(audit_result)

                import json
                data = json.loads(
                    Path(".excelsior/ai_handover.json").read_text())
                steps = data["next_steps"]
                assert any("BLOCKED" in s for s in steps)
                assert any("ruff" in s.lower() for s in steps)
                assert any("plan-fix" in s for s in steps)
            finally:
                os.chdir(original_cwd)

    def test_save_ai_handover_next_steps_comment_only_violations(self) -> None:
        """Test next_steps when there are comment-only (governance) violations."""
        telemetry = Mock()
        rule_fixability_service = RuleFixabilityService()
        filesystem = FileSystemGateway()
        artifact_storage = LocalArtifactStorage(".excelsior", filesystem)
        config_loader = ConfigurationLoader({}, {})
        guidance = Mock()
        guidance.get_fixable_codes.return_value = []
        guidance.get_comment_only_codes.return_value = {"W9006"}
        guidance.get_manual_instructions.return_value = ""
        guidance.get_display_name.return_value = "Rule"
        service = AuditTrailService(
            telemetry, rule_fixability_service, artifact_storage, config_loader,
            guidance_service=guidance, raw_log_port=Mock())

        with TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                Path(".excelsior").mkdir(exist_ok=True)

                audit_result = AuditResult(
                    excelsior_results=[
                        LinterResult(
                            "W9006",
                            "Law of Demeter",
                            ["src/bar.py:20"],
                        ),
                    ],
                    ruff_enabled=True,
                )
                service.save_ai_handover(audit_result)

                import json
                data = json.loads(
                    Path(".excelsior/ai_handover.json").read_text())
                steps = data["next_steps"]
                assert any("governance" in s.lower()
                           or "EXCELSIOR" in s for s in steps)
                assert "files_with_governance_comments" in data
                assert "src/bar.py" in data["files_with_governance_comments"]
                assert 20 in data["files_with_governance_comments"]["src/bar.py"]
            finally:
                os.chdir(original_cwd)

    def test_save_ai_handover_next_steps_no_violations(self) -> None:
        """Test next_steps when there are no violations."""
        telemetry = Mock()
        rule_fixability_service = RuleFixabilityService()
        filesystem = FileSystemGateway()
        artifact_storage = LocalArtifactStorage(".excelsior", filesystem)
        config_loader = ConfigurationLoader({}, {})
        guidance = Mock()
        guidance.get_fixable_codes.return_value = []
        guidance.get_comment_only_codes.return_value = set()
        guidance.get_manual_instructions.return_value = ""
        guidance.get_display_name.return_value = "Rule"
        service = AuditTrailService(
            telemetry, rule_fixability_service, artifact_storage, config_loader,
            guidance_service=guidance, raw_log_port=Mock())

        with TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                Path(".excelsior").mkdir(exist_ok=True)

                audit_result = AuditResult(ruff_enabled=True)
                service.save_ai_handover(audit_result)

                import json
                data = json.loads(
                    Path(".excelsior/ai_handover.json").read_text())
                steps = data["next_steps"]
                assert any("clean" in s.lower() for s in steps)
                assert data["summary"]["total_violations"] == 0
            finally:
                os.chdir(original_cwd)

    def test_save_ai_handover_next_steps_auto_fixable(self) -> None:
        """Test next_steps when there are auto-fixable violations (e.g. Ruff fixable)."""
        telemetry = Mock()
        rule_fixability_service = RuleFixabilityService()
        filesystem = FileSystemGateway()
        artifact_storage = LocalArtifactStorage(".excelsior", filesystem)
        config_loader = ConfigurationLoader({}, {})
        guidance = Mock()
        guidance.get_fixable_codes.return_value = []
        guidance.get_comment_only_codes.return_value = set()
        guidance.get_manual_instructions.return_value = ""
        guidance.get_display_name.return_value = "Rule"
        service = AuditTrailService(
            telemetry, rule_fixability_service, artifact_storage, config_loader,
            guidance_service=guidance, raw_log_port=Mock())

        with TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                Path(".excelsior").mkdir(exist_ok=True)

                audit_result = AuditResult(
                    ruff_results=[
                        LinterResult("I001", "Import order", ["file.py:1"]),
                    ],
                    ruff_enabled=True,
                )
                service.save_ai_handover(audit_result)

                import json
                data = json.loads(
                    Path(".excelsior/ai_handover.json").read_text())
                steps = data["next_steps"]
                assert any("auto" in s.lower() or "fix" in s.lower()
                           for s in steps)
            finally:
                os.chdir(original_cwd)

    def test_save_ai_handover_next_steps_manual_fix_only(self) -> None:
        """Test next_steps when there are only manual-fix (non-comment-only) violations."""
        telemetry = Mock()
        rule_fixability_service = RuleFixabilityService()
        filesystem = FileSystemGateway()
        artifact_storage = LocalArtifactStorage(".excelsior", filesystem)
        config_loader = ConfigurationLoader({}, {})
        guidance = Mock()
        guidance.get_fixable_codes.return_value = []
        guidance.get_comment_only_codes.return_value = set()
        guidance.get_manual_instructions.return_value = ""
        guidance.get_display_name.return_value = "Rule"
        service = AuditTrailService(
            telemetry, rule_fixability_service, artifact_storage, config_loader,
            guidance_service=guidance, raw_log_port=Mock())

        with TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                Path(".excelsior").mkdir(exist_ok=True)

                audit_result = AuditResult(
                    mypy_results=[
                        LinterResult("error", "Type error", ["file.py:1"]),
                    ],
                    ruff_enabled=True,
                )
                service.save_ai_handover(audit_result)

                import json
                data = json.loads(
                    Path(".excelsior/ai_handover.json").read_text())
                steps = data["next_steps"]
                assert any("manual" in s.lower() for s in steps)
                assert any("plan-fix" in s for s in steps)
            finally:
                os.chdir(original_cwd)

    def test_save_audit_trail_txt_includes_comment_label_for_comment_only(self) -> None:
        """Test that last_audit.txt uses Comment label for comment-only (W9006) violations."""
        telemetry = Mock()
        rule_fixability_service = RuleFixabilityService()
        filesystem = FileSystemGateway()
        artifact_storage = LocalArtifactStorage(".excelsior", filesystem)
        config_loader = ConfigurationLoader({}, {})
        guidance = Mock()
        guidance.get_fixable_codes.return_value = []
        guidance.get_comment_only_codes.return_value = {"W9006"}
        guidance.get_manual_instructions.return_value = ""
        guidance.get_display_name.return_value = "Rule"
        service = AuditTrailService(
            telemetry, rule_fixability_service, artifact_storage, config_loader,
            guidance_service=guidance, raw_log_port=Mock())

        with TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                Path(".excelsior").mkdir(exist_ok=True)

                audit_result = AuditResult(
                    excelsior_results=[
                        LinterResult(
                            "W9006",
                            "Law of Demeter: Chain access (x.y) exceeds one level",
                            ["file.py:1"],
                        ),
                    ],
                    ruff_enabled=True,
                )
                service.save_audit_trail(audit_result)

                txt_content = Path(".excelsior/last_audit.txt").read_text()
                assert "Comment" in txt_content or "💬" in txt_content
            finally:
                os.chdir(original_cwd)

    def test_save_audit_trail_with_source_writes_source_specific_files(
        self,
    ) -> None:
        """With source='check', writes check/last_audit.json and check/last_audit.txt."""
        telemetry = Mock()
        rule_fixability_service = RuleFixabilityService()
        filesystem = FileSystemGateway()
        artifact_storage = LocalArtifactStorage(".excelsior", filesystem)
        config_loader = ConfigurationLoader({}, {})
        guidance = Mock()
        guidance.get_fixable_codes.return_value = []
        guidance.get_comment_only_codes.return_value = set()
        guidance.get_manual_instructions.return_value = ""
        guidance.get_display_name.return_value = "Rule"
        service = AuditTrailService(
            telemetry, rule_fixability_service, artifact_storage, config_loader,
            guidance_service=guidance, raw_log_port=Mock())

        with TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                audit_result = AuditResult(ruff_enabled=True)
                service.save_audit_trail(audit_result, source="check")

                assert Path(".excelsior/check/last_audit.json").exists()
                assert Path(".excelsior/check/last_audit.txt").exists()
            finally:
                os.chdir(original_cwd)

    def test_save_ai_handover_with_source_writes_source_specific_file(
        self,
    ) -> None:
        """With source='fix', returns path to ai_handover_fix.json."""
        telemetry = Mock()
        rule_fixability_service = RuleFixabilityService()
        filesystem = FileSystemGateway()
        artifact_storage = LocalArtifactStorage(".excelsior", filesystem)
        config_loader = ConfigurationLoader({}, {})
        guidance = Mock()
        guidance.get_fixable_codes.return_value = []
        guidance.get_comment_only_codes.return_value = set()
        guidance.get_manual_instructions.return_value = ""
        guidance.get_display_name.return_value = "Rule"
        service = AuditTrailService(
            telemetry, rule_fixability_service, artifact_storage, config_loader,
            guidance_service=guidance, raw_log_port=Mock())

        with TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                audit_result = AuditResult(ruff_enabled=True)
                path = service.save_ai_handover(audit_result, source="fix")

                assert path == "fix/ai_handover.json"
                assert Path(".excelsior/fix/ai_handover.json").exists()
            finally:
                os.chdir(original_cwd)

    def test_append_audit_history_appends_line(self) -> None:
        """append_audit_history appends one NDJSON line; multiple calls grow the file."""
        telemetry = Mock()
        rule_fixability_service = RuleFixabilityService()
        filesystem = FileSystemGateway()
        artifact_storage = LocalArtifactStorage(".excelsior", filesystem)
        config_loader = ConfigurationLoader({}, {})
        guidance = Mock()
        guidance.get_fixable_codes.return_value = []
        guidance.get_comment_only_codes.return_value = set()
        guidance.get_manual_instructions.return_value = ""
        guidance.get_display_name.return_value = "Rule"
        service = AuditTrailService(
            telemetry, rule_fixability_service, artifact_storage, config_loader,
            guidance_service=guidance, raw_log_port=Mock())

        with TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                Path(".excelsior").mkdir(exist_ok=True)
                audit_result = AuditResult(ruff_enabled=True)

                service.append_audit_history(
                    audit_result,
                    source="check",
                    json_path="check/last_audit.json",
                    txt_path="check/last_audit.txt",
                )
                content1 = Path(".excelsior/audit_history.jsonl").read_text()
                lines1 = [l for l in content1.strip().split("\n") if l.strip()]

                service.append_audit_history(
                    audit_result,
                    source="fix",
                    json_path="fix/last_audit.json",
                    txt_path="fix/last_audit.txt",
                )
                content2 = Path(".excelsior/audit_history.jsonl").read_text()
                lines2 = [l for l in content2.strip().split("\n") if l.strip()]

                assert len(lines1) == 1
                assert len(lines2) == 2
                import json as _json
                rec1 = _json.loads(lines1[0])
                assert rec1["source"] == "check"
                rec2 = _json.loads(lines2[1])
                assert rec2["source"] == "fix"
            finally:
                os.chdir(original_cwd)
