"""Custom Pylint reporter for Snowarch summary table."""

from collections import defaultdict
from typing import Any, Dict, List

from pylint.message import Message
from pylint.reporters import BaseReporter


class CleanArchitectureSummaryReporter(BaseReporter):
    """
    A custom Pylint reporter that displays a summary table of errors
    grouped by error code/name and package.
    """

    name = "clean-arch-summary"

    def __init__(self, output=None):
        super().__init__(output)
        self.messages: List[Message] = []

    def handle_message(self, msg: Message):
        """Collect messages for summarization."""
        self.messages.append(msg)

    def display_reports(self, layout):
        """Render the summary table."""
        if not self.messages:
            print("No issues found!", file=self.out)
            return

        # Structure: {error_code: {package: count, 'name': error_name}}
        errors, packages = self._collect_stats()

        # Prepare Table Data
        sorted_packages = sorted(list(packages))
        headers = ["Error Code", "Error Name", "Total"] + sorted_packages

        # Calculate column widths
        widths = self._calculate_widths(headers, errors, sorted_packages)

        # Print Table
        self._print_table(headers, widths, errors, sorted_packages)

    def _collect_stats(self):
        """Aggregate error statistics."""
        errors: Dict[str, Dict[str, Any]] = defaultdict(lambda: defaultdict(int))
        packages = set()

        for msg in self.messages:
            path = msg.path
            parts = path.split("/")
            package = "unknown"
            if "packages" in parts:
                try:
                    idx = parts.index("packages")
                    if idx + 1 < len(parts):
                        package = parts[idx + 1].replace("snowarch-", "")
                except ValueError:
                    pass

            packages.add(package)
            errors[msg.msg_id]["name"] = msg.symbol
            errors[msg.msg_id][package] += 1
            errors[msg.msg_id]["total"] = errors[msg.msg_id].get("total", 0) + 1

        return errors, packages

    def _calculate_widths(self, headers, errors, sorted_packages):
        """Calculate dynamic column widths."""
        widths = [len(h) for h in headers]
        for msg_id, details in errors.items():
            widths[0] = max(widths[0], len(msg_id))
            widths[1] = max(widths[1], len(str(details["name"])))
            widths[2] = max(widths[2], len(str(details["total"])))
            for i, pkg in enumerate(sorted_packages):
                widths[3 + i] = max(widths[3 + i], len(str(details.get(pkg, 0))))
        return widths

    def _print_table(self, headers, widths, errors, sorted_packages):
        """Print the formatted table."""
        fmt = " | ".join([f"{{:<{w}}}" for w in widths])
        print(file=self.out)  # Empty line
        print(fmt.format(*headers), file=self.out)
        print("-|-".join(["-" * w for w in widths]), file=self.out)

        total_errors = 0
        package_totals = defaultdict(int)

        # Sort by total count descending
        for msg_id, details in sorted(
            errors.items(), key=lambda x: x[1]["total"], reverse=True
        ):
            row = [msg_id, str(details["name"]), str(details["total"])]
            for pkg in sorted_packages:
                count = details.get(pkg, 0)
                row.append(str(count if count > 0 else 0))
                package_totals[pkg] += count
            print(fmt.format(*row), file=self.out)
            total_errors += details["total"]

        print("-" * (sum(widths) + 3 * (len(widths) - 1)), file=self.out)

        # Totals row
        totals_row = ["Total", "", str(total_errors)]
        for pkg in sorted_packages:
            totals_row.append(str(package_totals[pkg]))
        print(fmt.format(*totals_row), file=self.out)
        print(file=self.out)

    def _display(self, layout):
        """Legacy method for older Pylint versions."""
        self.display_reports(layout)
