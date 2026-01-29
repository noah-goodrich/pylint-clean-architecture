import io
import re
import unittest
from collections import namedtuple
from unittest.mock import MagicMock

from clean_architecture_linter.interface.reporter import CleanArchitectureSummaryReporter

Message = namedtuple("Message", ["msg_id", "symbol", "path"])


class TestCleanArchitectureSummaryReporter(unittest.TestCase):
    def test_collect_stats(self) -> None:
        reporter = CleanArchitectureSummaryReporter()
        reporter.handle_message(
            Message("W9001", "dependency-violation", "packages/core/src/domain/file.py"))
        reporter.handle_message(
            Message("W9001", "dependency-violation", "packages/audit/src/domain/file.py"))
        reporter.handle_message(
            Message("W9004", "io-violation", "packages/core/src/domain/file.py"))

        out = io.StringIO()
        reporter.out = out
        reporter.display_reports(None)

        # Strip ANSI color codes for stable parsing
        output = re.sub(r"\x1b\[[0-9;]*m", "", out.getvalue())
        lines = output.splitlines()
        header_idx = next(i for i, line in enumerate(
            lines) if line.strip().startswith("Error Code"))
        headers = [h.strip() for h in lines[header_idx].split("|")]
        # Expect packages columns present
        self.assertIn("core", [h.lower() for h in headers])
        self.assertIn("audit", [h.lower() for h in headers])

        def row_for(code: str) -> list[str]:
            row = next(line for line in lines if line.strip().startswith(code))
            return [c.strip() for c in row.split("|")]

        w9001 = row_for("W9001")
        w9004 = row_for("W9004")

        # Map column name -> value
        idx = {h.strip().lower(): i for i, h in enumerate(headers)}
        self.assertEqual(w9001[idx["total"]], "2")
        self.assertEqual(w9001[idx["core"]], "1")
        self.assertEqual(w9001[idx["audit"]], "1")

        self.assertEqual(w9004[idx["total"]], "1")
        self.assertEqual(w9004[idx["core"]], "1")

    def test_summary_reporter(self) -> None:
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
        self.assertIn("W9001", output)
        self.assertIn("W9002", output)
        self.assertIn("core", output)
        self.assertIn("audit", output)
        self.assertIn("Total", output)

    def test_summary_reporter_empty(self) -> None:
        reporter = CleanArchitectureSummaryReporter()

        out = io.StringIO()
        reporter.out = out
        reporter.display_reports(None)
        self.assertIn(
            "Mission Accomplished: No architectural violations detected.", out.getvalue())
        reporter = CleanArchitectureSummaryReporter()
        reporter.handle_message(
            Message("W9001", "some-error", "src/weird/path.py"))

        out = io.StringIO()
        reporter.out = out
        reporter.display_reports(None)
        output = re.sub(r"\x1b\[[0-9;]*m", "", out.getvalue())
        self.assertIn("unknown", output)
        self.assertIn("W9001", output)


if __name__ == "__main__":
    unittest.main()
