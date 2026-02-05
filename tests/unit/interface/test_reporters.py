"""Unit tests for interface/reporters.py (TerminalAuditReporter)."""

from unittest.mock import MagicMock, patch

from clean_architecture_linter.domain.entities import AuditResult, LinterResult
from clean_architecture_linter.infrastructure.services.rule_analysis import RuleFixabilityService


@patch("stellar_ui_kit.TerminalReporter", MagicMock())
class TestTerminalAuditReporter:
    """Test TerminalAuditReporter.report_audit and helpers."""

    def test_report_audit_blocked_by_ruff_prints_message_and_reports_ruff(self) -> None:
        """When blocked by Ruff, prints block message and shows Ruff table."""
        from clean_architecture_linter.infrastructure.reporters import TerminalAuditReporter

        rule_svc = RuleFixabilityService()
        rep = TerminalAuditReporter(
            rule_svc,
            config_loader=MagicMock(),
            guidance_service=MagicMock(),
            raw_log_port=MagicMock(),
            telemetry=MagicMock(),
        )
        rep.reporter = MagicMock()

        audit = AuditResult(
            blocked_by="ruff",
            ruff_results=[LinterResult("E501", "Line too long", ["f.py:1"])],
            ruff_enabled=True,
        )
        with patch("builtins.print") as mock_print:
            rep.report_audit(audit)

        printed = " ".join(str(c) for c in mock_print.call_args_list)
        assert "AUDIT BLOCKED" in printed
        assert "RUFF" in printed
        rep.reporter.generate_report.assert_called_once()

    def test_report_audit_blocked_by_mypy_prints_message_and_reports_mypy(self) -> None:
        """When blocked by Mypy, prints block message and shows Mypy table."""
        from clean_architecture_linter.infrastructure.reporters import TerminalAuditReporter

        rule_svc = RuleFixabilityService()
        rep = TerminalAuditReporter(
            rule_svc,
            config_loader=MagicMock(),
            guidance_service=MagicMock(),
            raw_log_port=MagicMock(),
            telemetry=MagicMock(),
        )
        rep.reporter = MagicMock()

        audit = AuditResult(
            blocked_by="mypy",
            mypy_results=[LinterResult("error", "Missing type", ["f.py:1"])],
        )
        with patch("builtins.print"):
            rep.report_audit(audit)

        rep.reporter.generate_report.assert_called_once()

    def test_report_audit_not_blocked_shows_mypy_table_when_results(self) -> None:
        """When not blocked and mypy_results present, generates Mypy report."""
        rule_svc = RuleFixabilityService()
        with patch(
            "stellar_ui_kit.TerminalReporter"
        ) as mock_tr_class:
            mock_tr = MagicMock()
            mock_tr_class.return_value = mock_tr
            with patch(
                "stellar_ui_kit.ReportSchema",
            ), patch(
                "stellar_ui_kit.ColumnDefinition",
            ), patch(
                "clean_architecture_linter.infrastructure.adapters.linter_adapters.MypyAdapter",
            ), patch(
                "clean_architecture_linter.infrastructure.adapters.linter_adapters.ExcelsiorAdapter",
            ), patch(
                "clean_architecture_linter.infrastructure.adapters.ruff_adapter.RuffAdapter",
            ):
                from clean_architecture_linter.infrastructure.reporters import TerminalAuditReporter

                rep = TerminalAuditReporter(
                    rule_svc,
                    config_loader=MagicMock(),
                    guidance_service=MagicMock(),
                    raw_log_port=MagicMock(),
                    telemetry=MagicMock(),
                )

        audit = AuditResult(
            mypy_results=[LinterResult("err", "msg", ["a.py:1"])],
            ruff_enabled=False,
        )
        rep.report_audit(audit)
        assert mock_tr.generate_report.call_count >= 1

    def test_report_audit_not_blocked_shows_excelsior_table_when_results(self) -> None:
        """When not blocked and excelsior_results present, generates Excelsior report."""
        rule_svc = RuleFixabilityService()
        with patch(
            "stellar_ui_kit.TerminalReporter"
        ) as mock_tr_class:
            mock_tr = MagicMock()
            mock_tr_class.return_value = mock_tr
            with patch(
                "stellar_ui_kit.ReportSchema",
            ), patch(
                "stellar_ui_kit.ColumnDefinition",
            ), patch(
                "clean_architecture_linter.infrastructure.adapters.linter_adapters.MypyAdapter",
            ), patch(
                "clean_architecture_linter.infrastructure.adapters.linter_adapters.ExcelsiorAdapter",
            ), patch(
                "clean_architecture_linter.infrastructure.adapters.ruff_adapter.RuffAdapter",
            ):
                from clean_architecture_linter.infrastructure.reporters import TerminalAuditReporter

                rep = TerminalAuditReporter(
                    rule_svc,
                    config_loader=MagicMock(),
                    guidance_service=MagicMock(),
                    raw_log_port=MagicMock(),
                    telemetry=MagicMock(),
                )

        audit = AuditResult(
            excelsior_results=[LinterResult(
                "W9001", "Dependency", ["b.py:1"])],
            ruff_enabled=False,
        )
        rep.report_audit(audit)
        assert mock_tr.generate_report.call_count >= 1

    def test_report_audit_import_linter_results_generates_report(self) -> None:
        """When import_linter_results present, generates Import-Linter table."""
        rule_svc = RuleFixabilityService()
        with patch(
            "stellar_ui_kit.TerminalReporter"
        ) as mock_tr_class:
            mock_tr = MagicMock()
            mock_tr_class.return_value = mock_tr
            with patch(
                "stellar_ui_kit.ReportSchema",
            ), patch(
                "stellar_ui_kit.ColumnDefinition",
            ), patch(
                "clean_architecture_linter.infrastructure.adapters.linter_adapters.MypyAdapter",
            ), patch(
                "clean_architecture_linter.infrastructure.adapters.linter_adapters.ExcelsiorAdapter",
            ), patch(
                "clean_architecture_linter.infrastructure.adapters.ruff_adapter.RuffAdapter",
            ):
                from clean_architecture_linter.infrastructure.reporters import TerminalAuditReporter

                rep = TerminalAuditReporter(
                    rule_svc,
                    config_loader=MagicMock(),
                    guidance_service=MagicMock(),
                    raw_log_port=MagicMock(),
                    telemetry=MagicMock(),
                )

        audit = AuditResult(
            import_linter_results=[LinterResult("IL", "Boundary", ["c.py:1"])],
            ruff_enabled=False,
        )
        rep.report_audit(audit)
        calls = [c[0][0] for c in mock_tr.generate_report.call_args_list]
        assert any(isinstance(rows, list) and rows for rows in calls)

    def test_report_audit_ruff_enabled_with_results_generates_ruff_report(self) -> None:
        """When ruff_enabled and ruff_results, generates Ruff table."""
        rule_svc = RuleFixabilityService()
        with patch(
            "stellar_ui_kit.TerminalReporter"
        ) as mock_tr_class:
            mock_tr = MagicMock()
            mock_tr_class.return_value = mock_tr
            with patch(
                "stellar_ui_kit.ReportSchema",
            ), patch(
                "stellar_ui_kit.ColumnDefinition",
            ), patch(
                "clean_architecture_linter.infrastructure.adapters.linter_adapters.MypyAdapter",
            ), patch(
                "clean_architecture_linter.infrastructure.adapters.linter_adapters.ExcelsiorAdapter",
            ), patch(
                "clean_architecture_linter.infrastructure.adapters.ruff_adapter.RuffAdapter",
                return_value=MagicMock(),
            ):
                from clean_architecture_linter.infrastructure.reporters import TerminalAuditReporter

                rep = TerminalAuditReporter(
                    rule_svc,
                    config_loader=MagicMock(),
                    guidance_service=MagicMock(),
                    raw_log_port=MagicMock(),
                    telemetry=MagicMock(),
                )

        audit = AuditResult(
            ruff_enabled=True,
            ruff_results=[LinterResult("E501", "Line too long", ["d.py:1"])],
        )
        rep.report_audit(audit)
        assert mock_tr.generate_report.call_count >= 1

    def test_process_results_comment_only_sets_fix_comment(self) -> None:
        """_process_results sets fix to Comment when adapter says comment_only."""
        rule_svc = RuleFixabilityService()
        with patch(
            "stellar_ui_kit.TerminalReporter",
            MagicMock(),
        ):
            from clean_architecture_linter.infrastructure.reporters import TerminalAuditReporter

            rep = TerminalAuditReporter(
            rule_svc,
            config_loader=MagicMock(),
            guidance_service=MagicMock(),
            raw_log_port=MagicMock(),
            telemetry=MagicMock(),
        )

        adapter = MagicMock()
        adapter.is_comment_only_rule = lambda code: True
        rule_svc.is_rule_fixable = lambda a, c: False
        results = [LinterResult("W9001", "Dep", ["x.py:1"])]
        out = rep._process_results(results, adapter)
        assert len(out) == 1
        assert out[0]["fix"] == "💬 Comment"

    def test_process_results_auto_fixable_sets_fix_auto(self) -> None:
        """_process_results sets fix to Auto when rule is fixable."""
        rule_svc = RuleFixabilityService()
        with patch(
            "stellar_ui_kit.TerminalReporter",
            MagicMock(),
        ):
            from clean_architecture_linter.infrastructure.reporters import TerminalAuditReporter

            rep = TerminalAuditReporter(
            rule_svc,
            config_loader=MagicMock(),
            guidance_service=MagicMock(),
            raw_log_port=MagicMock(),
            telemetry=MagicMock(),
        )

        adapter = MagicMock()
        adapter.is_comment_only_rule = lambda code: False
        rule_svc.is_rule_fixable = lambda a, c: True
        results = [LinterResult("W9015", "Hint", ["y.py:1"])]
        out = rep._process_results(results, adapter)
        assert len(out) == 1
        assert out[0]["fix"] == "✅ Auto"

    def test_process_results_manual_sets_fix_manual(self) -> None:
        """_process_results sets fix to Manual when not fixable and not comment_only."""
        rule_svc = RuleFixabilityService()
        with patch(
            "stellar_ui_kit.TerminalReporter",
            MagicMock(),
        ):
            from clean_architecture_linter.infrastructure.reporters import TerminalAuditReporter

            rep = TerminalAuditReporter(
            rule_svc,
            config_loader=MagicMock(),
            guidance_service=MagicMock(),
            raw_log_port=MagicMock(),
            telemetry=MagicMock(),
        )

        adapter = MagicMock()
        adapter.is_comment_only_rule = lambda code: False
        rule_svc.is_rule_fixable = lambda a, c: False
        results = [LinterResult("W9017", "Layer", ["z.py:1"])]
        out = rep._process_results(results, adapter)
        assert len(out) == 1
        assert out[0]["fix"] == "⚠️ Manual"
