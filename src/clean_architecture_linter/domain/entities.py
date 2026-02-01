from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Union


class TransformationType(Enum):
    """Types of code transformations the fixer can apply."""
    FREEZE_DATACLASS = "freeze_dataclass"
    ADD_IMPORT = "add_import"
    ADD_RETURN_TYPE = "add_return_type"
    ADD_PARAMETER_TYPE = "add_parameter_type"
    ADD_GOVERNANCE_COMMENT = "add_governance_comment"


@dataclass(frozen=True)
class TransformationPlan:
    """
    Pure data structure describing a code transformation.
    
    This is a domain entity that rules return instead of LibCST transformers.
    The infrastructure layer (fixer gateway) interprets this plan and applies
    the actual LibCST transformation.
    """
    transformation_type: TransformationType
    params: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def freeze_dataclass(cls, class_name: str) -> "TransformationPlan":
        """Create plan to convert a class to frozen dataclass."""
        return cls(
            transformation_type=TransformationType.FREEZE_DATACLASS,
            params={"class_name": class_name}
        )

    @classmethod
    def add_import(cls, module: str, imports: list[str]) -> "TransformationPlan":
        """Create plan to add an import statement."""
        return cls(
            transformation_type=TransformationType.ADD_IMPORT,
            params={"module": module, "imports": imports}
        )

    @classmethod
    def add_return_type(cls, function_name: str, return_type: str) -> "TransformationPlan":
        """Create plan to add return type annotation."""
        return cls(
            transformation_type=TransformationType.ADD_RETURN_TYPE,
            params={"function_name": function_name, "return_type": return_type}
        )

    @classmethod
    def add_parameter_type(cls, function_name: str, param_name: str, param_type: str) -> "TransformationPlan":
        """Create plan to add parameter type annotation."""
        return cls(
            transformation_type=TransformationType.ADD_PARAMETER_TYPE,
            params={"function_name": function_name, "param_name": param_name, "param_type": param_type}
        )

    @classmethod
    def governance_comment(
        cls,
        rule_code: str,
        rule_name: str,
        problem: str,
        recommendation: str,
        context_info: str,
        target_line: int,
    ) -> "TransformationPlan":
        """Create plan to add governance comment above a line."""
        return cls(
            transformation_type=TransformationType.ADD_GOVERNANCE_COMMENT,
            params={
                "rule_code": rule_code,
                "rule_name": rule_name,
                "problem": problem,
                "recommendation": recommendation,
                "context_info": context_info,
                "target_line": target_line,
            }
        )


@dataclass(frozen=True)
class LinterResult:
    """Standardized linter result."""
    code: str
    message: str
    locations: list[str] = field(default_factory=list)

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

    def to_dict(self) -> dict[str, Union[str, list[str]]]:
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
    mypy_results: list[LinterResult] = field(default_factory=list)
    excelsior_results: list[LinterResult] = field(default_factory=list)
    import_linter_results: list[LinterResult] = field(default_factory=list)
    ruff_results: list[LinterResult] = field(default_factory=list)
    ruff_enabled: bool = True
    blocked_by: Optional[str] = None  # "import_linter", "ruff", "mypy", "excelsior", or None

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
    locations: list[str]
    fixable: bool
    manual_instructions: Optional[str] = None
    comment_only: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "code": self.code,
            "message": self.message,
            "location": self.location,
            "locations": self.locations,
            "fixable": self.fixable,
            "manual_instructions": self.manual_instructions,
            "comment_only": self.comment_only,
        }


@dataclass(frozen=True)
class AuditTrailSummary:
    """Domain representation of audit trail summary statistics."""
    type_integrity: int
    architectural: int
    contracts: int
    code_quality: int

    def to_dict(self) -> dict[str, int]:
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
    type_integrity: list[ViolationWithFixInfo]
    architectural: list[ViolationWithFixInfo]
    contracts: list[ViolationWithFixInfo]
    code_quality: list[ViolationWithFixInfo]

    def to_dict(self) -> dict[str, list[dict[str, Any]]]:
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

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "version": self.version,
            "timestamp": self.timestamp,
            "summary": self.summary.to_dict(),
            "violations": self.violations.to_dict(),
        }
