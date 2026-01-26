from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union


@dataclass(frozen=True)
class LinterResult:
    """Standardized linter result."""
    code: str
    message: str
    locations: List[str] = field(default_factory=list)

    def add_location(self, location: str) -> 'LinterResult':
        """
        Add a location to the result.
        Since it's frozen, we return a new instance.
        """
        # JUSTIFICATION: Dataclass replacement is the idiomatic way to handle immutable state updates.
        new_locations = list(self.locations)
        new_locations.append(location)
        import dataclasses
        return dataclasses.replace(self, locations=new_locations)

    def to_dict(self) -> Dict[str, Union[str, List[str]]]:
        """Convert to dictionary for reporter."""
        return {
            "code": self.code,
            "message": self.message,
            "location": ", ".join(self.locations) if self.locations else "N/A",
            "locations": self.locations
        }


@dataclass(frozen=True)
class AuditResult:
    """Result of a complete audit run across all linters."""
    mypy_results: List[LinterResult] = field(default_factory=list)
    excelsior_results: List[LinterResult] = field(default_factory=list)
    import_linter_results: List[LinterResult] = field(default_factory=list)
    ruff_results: List[LinterResult] = field(default_factory=list)
    ruff_enabled: bool = True
    blocked_by: Optional[str] = None  # "ruff", "mypy", or None if not blocked

    def has_violations(self) -> bool:
        """Check if any violations were found."""
        return bool(
            self.mypy_results or
            self.excelsior_results or
            self.import_linter_results or
            self.ruff_results
        )

    def is_blocked(self) -> bool:
        """Check if audit was blocked by a prior linter."""
        return self.blocked_by is not None


@dataclass(frozen=True)
class ViolationWithFixInfo:
    """Domain representation of a violation with fixability information."""
    code: str
    message: str
    location: str
    locations: List[str]
    fixable: bool
    manual_instructions: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "code": self.code,
            "message": self.message,
            "location": self.location,
            "locations": self.locations,
            "fixable": self.fixable,
            "manual_instructions": self.manual_instructions,
        }


@dataclass(frozen=True)
class AuditTrailSummary:
    """Domain representation of audit trail summary statistics."""
    type_integrity: int
    architectural: int
    contracts: int
    code_quality: int

    def to_dict(self) -> Dict[str, int]:
        """Convert to dictionary for serialization."""
        return {
            "type_integrity": self.type_integrity,
            "architectural": self.architectural,
            "contracts": self.contracts,
            "code_quality": self.code_quality,
        }


@dataclass(frozen=True)
class AuditTrailViolations:
    """Domain representation of audit trail violations grouped by category."""
    type_integrity: List[ViolationWithFixInfo]
    architectural: List[ViolationWithFixInfo]
    contracts: List[ViolationWithFixInfo]
    code_quality: List[ViolationWithFixInfo]

    def to_dict(self) -> Dict[str, List[Dict[str, Any]]]:
        """Convert to dictionary for serialization."""
        return {
            "type_integrity": [v.to_dict() for v in self.type_integrity],
            "architectural": [v.to_dict() for v in self.architectural],
            "contracts": [v.to_dict() for v in self.contracts],
            "code_quality": [v.to_dict() for v in self.code_quality],
        }


@dataclass(frozen=True)
class AuditTrail:
    """Domain entity representing a complete audit trail."""
    version: str
    timestamp: str
    summary: AuditTrailSummary
    violations: AuditTrailViolations

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "version": self.version,
            "timestamp": self.timestamp,
            "summary": self.summary.to_dict(),
            "violations": self.violations.to_dict(),
        }
