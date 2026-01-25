"""Custom Pylint reporter for Snowarch summary table."""

from collections import defaultdict
from typing import Any, Optional, Union

from pylint.message import Message
from pylint.reporters import BaseReporter


class CleanArchitectureSummaryReporter(BaseReporter):
    """
    grouped by error code/name and package.
    """

    name: str = "clean-arch-summary"

    # Stellar Engineering Command Cinematic Palette (24-bit ANSI)
    RED: str = "\033[38;2;196;30;58m"
    BLUE: str = "\033[38;2;0;123;255m"
    GOLD: str = "\033[38;2;249;166;2m"
    WARP: str = "\033[38;2;0;238;255m"
    RESET: str = "\033[0m"
    BOLD: str = "\033[1m"

    # JUSTIFICATION: BaseReporter __init__ uses Any for output
    def __init__(self, output: Optional[Any] = None) -> None:  # pylint: disable=banned-any-usage
        super().__init__(output)
        self.messages: list[Message] = []

    def handle_message(self, msg: Message) -> None:
        """Collect messages for summarization."""
        self.messages.append(msg)

    # JUSTIFICATION: Pylint API requires generic layout
    def display_reports(self, _layout: Any) -> None:  # pylint: disable=banned-any-usage
        """Render the summary table."""
        if not self.messages:
            msg = f"{self.BOLD}{self.GOLD}Mission Accomplished: No architectural violations detected.{self.RESET}"
            print(msg, file=self.out)
            return

        # Structure: {error_code: {package: count, 'name': error_name, 'total': count}}
        errors, packages = self._collect_stats()

        # Prepare Table Data
        sorted_packages = sorted(packages)
        headers = ["Error Code", "Error Name", "Total", *sorted_packages]

        # Calculate column widths
        widths = self._calculate_widths(headers, errors, sorted_packages)

        # Print Table
        self._print_table(headers, widths, errors, sorted_packages)

    def _collect_stats(self) -> tuple[dict[str, dict[str, Union[str, int]]], set[str]]:
        """Aggregate error statistics."""
        errors: dict[str, dict[str, Union[str, int]]] = defaultdict(lambda: defaultdict(int))
        packages: set[str] = set()

        for msg in self.messages:
            path = msg.path
            parts: list[str] = path.split("/")
            package: str = "unknown"
            if "packages" in parts:
                try:
                    idx = parts.index("packages")
                    if idx + 1 < len(parts):
                        package = parts[idx + 1]
                except ValueError:
                    pass

            packages.add(package)
            errors[msg.msg_id]["name"] = msg.symbol

            # Explicitly handle int counters to satisfy Mypy
            curr_pkg_count = errors[msg.msg_id].get(package, 0)
            if isinstance(curr_pkg_count, int):
                errors[msg.msg_id][package] = curr_pkg_count + 1

            curr_total = errors[msg.msg_id].get("total", 0)
            if isinstance(curr_total, int):
                errors[msg.msg_id]["total"] = curr_total + 1

        return dict(errors), packages

    def _calculate_widths(
        self,
        headers: list[str],
        errors: dict[str, dict[str, Union[str, int]]],
        sorted_packages: list[str],
    ) -> list[int]:
        """Calculate dynamic column widths."""
        widths = [len(h) for h in headers]
        for msg_id, details in errors.items():
            widths[0] = max(widths[0], len(msg_id))
            widths[1] = max(widths[1], len(str(details.get("name", ""))))
            widths[2] = max(widths[2], len(str(details.get("total", 0))))
            for i, pkg in enumerate(sorted_packages):
                widths[3 + i] = max(widths[3 + i], len(str(details.get(pkg, 0))))
        return widths

    def _print_table(
        self,
        headers: list[str],
        widths: list[int],
        errors: dict[str, dict[str, Union[str, int]]],
        sorted_packages: list[str],
    ) -> None:
        """Print the formatted table."""
        fmt: str = " | ".join([f"{{:<{w}}}" for w in widths])
        print(file=self.out)  # Empty line

        # Header with Science Blue
        header_text = fmt.format(*headers)
        print(f"{self.BOLD}{self.BLUE}{header_text}{self.RESET}", file=self.out)
        line_parts = ["-" * w for w in widths]
        print(f"{self.BLUE}{'-|-'.join(line_parts)}{self.RESET}", file=self.out)

        total_errors: int = 0
        package_totals: dict[str, int] = defaultdict(int)

        # Sort by total count descending
        sorted_errors = sorted(errors.items(), key=lambda x: int(x[1].get("total", 0)), reverse=True)
        for msg_id, details in sorted_errors:
            # Re-calculating row with padding but WITHOUT colors first to get strings correct
            padded_row = []
            padded_row.append(f"{self.RED}{msg_id:<{widths[0]}}{self.RESET}")
            name_val = str(details.get("name", ""))
            padded_row.append(f"{self.WARP}{name_val:<{widths[1]}}{self.RESET}")
            total_val = str(details.get("total", 0))
            padded_row.append(f"{self.BOLD}{total_val:<{widths[2]}}{self.RESET}")

            for i, pkg in enumerate(sorted_packages):
                count = details.get(pkg, 0)
                val = str(count if count > 0 else 0)
                padded_row.append(f"{val:<{widths[3 + i]}}")
                if isinstance(count, int):
                    package_totals[pkg] += count

            print(" | ".join(padded_row), file=self.out)
            total_val_int = details.get("total", 0)
            if isinstance(total_val_int, int):
                total_errors += total_val_int

        divider_len = sum(widths) + 3 * (len(widths) - 1)
        print(f"{self.BLUE}{'-' * divider_len}{self.RESET}", file=self.out)

        # Totals row with Ops Gold
        totals_row = [f"{self.BOLD}{self.GOLD}{'Fleet Total':<{widths[0]}}{self.RESET}"]
        totals_row.append(f"{' ':<{widths[1]}}")
        totals_row.append(f"{self.BOLD}{self.GOLD}{str(total_errors):<{widths[2]}}{self.RESET}")
        for i, pkg in enumerate(sorted_packages):
            val = str(package_totals[pkg])
            totals_row.append(f"{self.BOLD}{self.GOLD}{val:<{widths[3 + i]}}{self.RESET}")

        print(" | ".join(totals_row), file=self.out)
        print(file=self.out)

        if total_errors > 0:
            msg = (
                f"{self.BOLD}{self.RED}Hull Integrity Breach: {total_errors} "
                f"violations detected across the fleet.{self.RESET}"
            )
            print(msg, file=self.out)
        else:
            msg = f"{self.BOLD}{self.GOLD}Prime Directives Satisfied: System integrity nominal.{self.RESET}"
            print(msg, file=self.out)

    # JUSTIFICATION: Legacy method override from Pylint base class requires generic layout
    def _display(self, _layout: Any) -> None:  # pylint: disable=banned-any-usage
        """Legacy method for older Pylint versions."""
        self.display_reports(_layout)
