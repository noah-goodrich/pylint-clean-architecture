import io
from unittest.mock import MagicMock

from clean_architecture_linter.reporter import CleanArchitectureSummaryReporter


def test_summary_reporter():
    reporter = CleanArchitectureSummaryReporter()

    # Create dummy messages
    m1 = MagicMock()
    m1.msg_id = "W9001"
    m1.symbol = "first-error"
    m1.path = "packages/snowarch-core/src/foo.py"

    m2 = MagicMock()
    m2.msg_id = "W9001"
    m2.symbol = "first-error"
    m2.path = "packages/snowarch-audit/src/bar.py"

    m3 = MagicMock()
    m3.msg_id = "W9002"
    m3.symbol = "second-error"
    m3.path = "packages/snowarch-core/src/baz.py"

    reporter.handle_message(m1)
    reporter.handle_message(m2)
    reporter.handle_message(m3)

    # Capture output

    out = io.StringIO()
    reporter.out = out
    reporter.display_reports(None)

    output = out.getvalue()
    assert "W9001" in output
    assert "W9002" in output
    assert "core" in output
    assert "audit" in output
    assert "Total" in output


def test_summary_reporter_empty():
    reporter = CleanArchitectureSummaryReporter()

    out = io.StringIO()
    reporter.out = out
    reporter.display_reports(None)
    assert "No issues found!" in out.getvalue()
