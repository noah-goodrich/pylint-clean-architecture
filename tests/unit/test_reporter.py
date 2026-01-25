import io
import unittest
from collections import namedtuple
from unittest.mock import MagicMock

from clean_architecture_linter.reporter import CleanArchitectureSummaryReporter

Message = namedtuple("Message", ["msg_id", "symbol", "path"])


class TestCleanArchitectureSummaryReporter(unittest.TestCase):
    def test_collect_stats(self):
        reporter = CleanArchitectureSummaryReporter()
        reporter.handle_message(Message("W9001", "dependency-violation", "packages/core/src/domain/file.py"))
        reporter.handle_message(Message("W9001", "dependency-violation", "packages/audit/src/domain/file.py"))
        reporter.handle_message(Message("W9004", "io-violation", "packages/core/src/domain/file.py"))

        errors, packages = reporter._collect_stats()

        self.assertIn("W9001", errors)
        self.assertIn("W9004", errors)
        self.assertIn("core", packages)
        self.assertIn("audit", packages)

        self.assertEqual(errors["W9001"]["core"], 1)
        self.assertEqual(errors["W9001"]["audit"], 1)
        self.assertEqual(errors["W9001"]["total"], 2)

    def test_summary_reporter(self):
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

    def test_summary_reporter_empty(self):
        reporter = CleanArchitectureSummaryReporter()

        out = io.StringIO()
        reporter.out = out
        reporter.display_reports(None)
        self.assertIn("Mission Accomplished: No architectural violations detected.", out.getvalue())
        reporter = CleanArchitectureSummaryReporter()
        reporter.handle_message(Message("W9001", "some-error", "src/weird/path.py"))

        errors, packages = reporter._collect_stats()
        self.assertIn("unknown", packages)
        self.assertEqual(errors["W9001"]["unknown"], 1)


if __name__ == "__main__":
    unittest.main()
