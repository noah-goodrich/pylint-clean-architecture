"""Protocol for audit reporting - no infrastructure imports."""

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from excelsior_architect.domain.entities import ArchitecturalHealthReport, AuditResult


class AuditReporter(Protocol):
    """Protocol for reporting audit results and health reports."""

    def report_audit(
        self, audit_result: "AuditResult", view: str = "by_code"
    ) -> None:
        """Report audit results to the user. view: 'by_code' (default) or 'by_file'."""
        ...

    def render_health_report(
        self,
        report: "ArchitecturalHealthReport",
        format: str = "terminal",
        mode: str = "standard",
    ) -> None:
        """Render full architectural health report. format: terminal, json, markdown. mode: standard, eli5, agent."""
        ...
