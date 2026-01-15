"""Custom Pylint reporter for Snowarch summary table."""

from collections import defaultdict
from typing import Any, Dict, List

from pylint.message import Message
from pylint.reporters import BaseReporter


class CleanArchitectureSummaryReporter(BaseReporter):
    """
    grouped by error code/name and package.
    """

    name = "clean-arch-summary"

    # Stellar Engineering Command Cinematic Palette (24-bit ANSI)
    RED = "\033[38;2;196;30;58m"
    BLUE = "\033[38;2;0;123;255m"
    GOLD = "\033[38;2;249;166;2m"
    WARP = "\033[38;2;0;238;255m"
    RESET = "\033[0m"
    BOLD = "\033[1m"

    def __init__(self, output=None):
        super().__init__(output)
        self.messages: List[Message] = []

    def handle_message(self, msg: Message):
        """Collect messages for summarization."""
        self.messages.append(msg)

    def display_reports(self, layout):
        """Render the summary table."""
        if not self.messages:
            msg = f"{self.BOLD}{self.GOLD}Mission Accomplished: No architectural violations detected.{self.RESET}"
            print(msg, file=self.out)
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
                        package = parts[idx + 1]
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

        # Header with Science Blue
        header_text = fmt.format(*headers)
        print(f"{self.BOLD}{self.BLUE}{header_text}{self.RESET}", file=self.out)
        print(f"{self.BLUE}{'-|-'.join(['-' * w for w in widths])}{self.RESET}", file=self.out)

        total_errors = 0
        package_totals = defaultdict(int)

        # Sort by total count descending
        # Sort by total count descending
        sorted_errors = sorted(errors.items(), key=lambda x: x[1]["total"], reverse=True)
        for msg_id, details in sorted_errors:
            row = [
                f"{self.RED}{msg_id}{self.RESET}",
                f"{self.WARP}{details['name']}{self.RESET}",
                f"{self.BOLD}{details['total']}{self.RESET}",
            ]
            for pkg in sorted_packages:
                count = details.get(pkg, 0)
                row.append(str(count if count > 0 else 0))
                package_totals[pkg] += count

            # We need to handle ANSI codes in width calculation or just use a simpler fmt
            # Since fmt uses {:<w}, and ANSI codes have length, we need to adjust or bypass.
            # Easiest is to format the strings without colors first for padding, then add colors?
            # Or just use the already calculated widths.

            # Re-calculating row with padding but WITHOUT colors first to get strings correct
            padded_row = []
            padded_row.append(f"{self.RED}{msg_id:<{widths[0]}}{self.RESET}")
            padded_row.append(f"{self.WARP}{str(details['name']):<{widths[1]}}{self.RESET}")
            padded_row.append(f"{self.BOLD}{str(details['total']):<{widths[2]}}{self.RESET}")
            for i, pkg in enumerate(sorted_packages):
                count = details.get(pkg, 0)
                val = str(count if count > 0 else 0)
                padded_row.append(f"{val:<{widths[3+i]}}")

            print(" | ".join(padded_row), file=self.out)
            total_errors += details["total"]

        print(f"{self.BLUE}{'-' * (sum(widths) + 3 * (len(widths) - 1))}{self.RESET}", file=self.out)

        # Totals row with Ops Gold
        totals_row = [f"{self.BOLD}{self.GOLD}Fleet Total{self.RESET}"]
        totals_row.append(f"{' ':<{widths[1]}}")
        totals_row.append(f"{self.BOLD}{self.GOLD}{total_errors:<{widths[2]}}{self.RESET}")
        for i, pkg in enumerate(sorted_packages):
            val = str(package_totals[pkg])
            totals_row.append(f"{self.BOLD}{self.GOLD}{val:<{widths[3+i]}}{self.RESET}")

        print(" | ".join(totals_row), file=self.out)
        print(file=self.out)

        if total_errors > 0:
            msg = (
                f"{self.BOLD}{self.RED}Hull Integrity Breach: {total_errors} "
                f"violations detected across the fleet.{self.RESET}"
            )
            print(msg, file=self.out)
        else:
            msg = f"{self.BOLD}{self.GOLD}Prime Directives Satisfied: " f"System integrity nominal.{self.RESET}"
            print(msg, file=self.out)

    def _display(self, layout):
        """Legacy method for older Pylint versions."""
        self.display_reports(layout)
