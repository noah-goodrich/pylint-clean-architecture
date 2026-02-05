"""Protocol for audit reporting - no infrastructure imports."""

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from clean_architecture_linter.domain.entities import AuditResult


class AuditReporter(Protocol):
    """Protocol for reporting audit results."""

    def report_audit(
        self, audit_result: "AuditResult", view: str = "by_code"
    ) -> None:
        """Report audit results to the user. view: 'by_code' (default) or 'by_file'."""
        ...
