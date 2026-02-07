from dataclasses import dataclass, field
from enum import Enum
from typing import TypedDict

from excelsior_architect.domain.transformation_contexts import (
    FreezeDataclassContext,
    GovernanceCommentContext,
    ImportContext,
    ParameterTypeContext,
    PlanParams,
    ReturnTypeContext,
)


class OutputMode(Enum):
    """Verbosity mode for health/docs output."""
    ELI5 = "eli5"       # Junior/learning: expanded explanations, pattern glossary inline
    STANDARD = "standard"  # Default: findings with recommendations, action plan, legend
    # AI mode: structured data, minimal prose (use --format json)
    AGENT = "agent"


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
    params: PlanParams

    @classmethod
    def freeze_dataclass(cls, class_name: str) -> "TransformationPlan":
        """Create plan to convert a class to frozen dataclass."""
        p: FreezeDataclassContext = {"class_name": class_name}
        return cls(
            transformation_type=TransformationType.FREEZE_DATACLASS,
            params=p,
        )

    @classmethod
    def add_import(cls, module: str, imports: list[str]) -> "TransformationPlan":
        """Create plan to add an import statement."""
        p: ImportContext = {"module": module, "imports": imports}
        return cls(
            transformation_type=TransformationType.ADD_IMPORT,
            params=p,
        )

    @classmethod
    def add_return_type(cls, function_name: str, return_type: str) -> "TransformationPlan":
        """Create plan to add return type annotation."""
        p: ReturnTypeContext = {
            "function_name": function_name, "return_type": return_type}
        return cls(
            transformation_type=TransformationType.ADD_RETURN_TYPE,
            params=p,
        )

    @classmethod
    def add_parameter_type(cls, function_name: str, param_name: str, param_type: str) -> "TransformationPlan":
        """Create plan to add parameter type annotation."""
        p: ParameterTypeContext = {
            "function_name": function_name,
            "param_name": param_name,
            "param_type": param_type,
        }
        return cls(
            transformation_type=TransformationType.ADD_PARAMETER_TYPE,
            params=p,
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
        p: GovernanceCommentContext = {
            "rule_code": rule_code,
            "rule_name": rule_name,
            "problem": problem,
            "recommendation": recommendation,
            "context_info": context_info,
            "target_line": target_line,
        }
        return cls(
            transformation_type=TransformationType.ADD_GOVERNANCE_COMMENT,
            params=p,
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

    def to_dict(self) -> dict[str, str | list[str]]:
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
    # "check" = gated exit code for CI; "health" = full analysis, no gating
    mode: str = "check"
    # Which gate would block CI: "import_linter", "ruff", "mypy", "excelsior", or None
    blocking_gate: str | None = None

    def has_violations(self) -> bool:
        """Check if any violations were found."""
        return bool(
            self.mypy_results or
            self.excelsior_results or
            self.import_linter_results or
            self.ruff_results
        )

    def is_blocked(self) -> bool:
        """Check if the audit would be blocked by a gate (for CI)."""
        return self.blocking_gate is not None

    @property
    def blocked_by(self) -> str | None:
        """Backward-compat alias for blocking_gate."""
        return self.blocking_gate


class ViolationWithFixInfoDictRequired(TypedDict):
    """Required fields for ViolationWithFixInfo serialization."""
    code: str
    message: str
    location: str
    locations: list[str]
    fixable: bool


class ViolationWithFixInfoDict(ViolationWithFixInfoDictRequired, total=False):
    """Serialization shape for ViolationWithFixInfo including optional fields."""
    manual_instructions: str | None
    comment_only: bool


@dataclass(frozen=True)
class ViolationWithFixInfo:
    """Domain representation of a violation with fixability information."""
    code: str
    message: str
    location: str
    locations: list[str]
    fixable: bool
    manual_instructions: str | None = None
    comment_only: bool = False

    def to_dict(self) -> ViolationWithFixInfoDict:
        """Convert to dictionary for serialization."""
        out: ViolationWithFixInfoDict = {
            "code": self.code,
            "message": self.message,
            "location": self.location,
            "locations": self.locations,
            "fixable": self.fixable,
            "manual_instructions": self.manual_instructions,
        }
        if self.comment_only:
            out["comment_only"] = self.comment_only
        return out


@dataclass(frozen=True)
class DesignPatternRecommendation:
    """A design pattern recommendation based on detected code smells."""
    pattern: str
    category: str
    trigger: str
    rationale: str
    example_fix: str
    affected_files: list[str]
    related_violations: list[str]

    def to_dict(self) -> dict[str, object]:
        """Convert to dictionary for serialization."""
        return {
            "pattern": self.pattern,
            "category": self.category,
            "trigger": self.trigger,
            "rationale": self.rationale,
            "example_fix": self.example_fix,
            "affected_files": self.affected_files,
            "related_violations": self.related_violations,
        }


@dataclass(frozen=True)
class FindingScore:
    """
    Transparent priority score for a finding.

    Formula: priority = (reach * impact * confidence) / (effort + 0.1).
    All components are stored so the score is explainable and serializable.
    """
    reach: float   # 0-100: normalized file count (affected / total * 100)
    impact: float  # 1-10: rule-specific weight from registry
    confidence: float  # 0.0-1.0: true positive likelihood
    effort: float  # 1-5: 1=auto-fixable, 5=architectural change
    priority: float  # computed: (reach * impact * confidence) / (effort + 0.1)

    def explain(self) -> str:
        """Human-readable explanation of the score."""
        return (
            f"Priority {self.priority:.1f} = (reach {self.reach:.0f} * impact {self.impact} * confidence {self.confidence}) / (effort {self.effort} + 0.1)"
        )

    @classmethod
    def compute(
        cls,
        reach: float,
        impact: float,
        confidence: float,
        effort: float,
    ) -> "FindingScore":
        """Build a FindingScore with computed priority."""
        priority = (reach * impact * confidence) / (effort + 0.1)
        return cls(reach=reach, impact=impact, confidence=confidence, effort=effort, priority=priority)


def _severity_from_priority(priority: float) -> str:
    """Map priority score to critical|high|medium|low for display."""
    if priority >= 50:
        return "critical"
    if priority >= 20:
        return "high"
    if priority >= 5:
        return "medium"
    return "low"


@dataclass(frozen=True)
class SystemicFinding:
    """A cluster of related violations sharing a root cause."""
    id: str
    title: str
    root_cause: str
    impact: str
    score: FindingScore
    violation_codes: list[str]
    affected_files: list[str]
    violation_count: int
    pattern_recommendation: DesignPatternRecommendation | None
    learn_more: str = ""  # Reference URL or "excelsior plan <code>"
    # One-sentence explanation for ELI5 mode (from registry)
    eli5_description: str = ""

    @property
    def severity_label(self) -> str:
        """Derived severity for display (critical|high|medium|low)."""
        return _severity_from_priority(self.score.priority)

    def to_dict(self) -> dict[str, object]:
        """Convert to dictionary for serialization."""
        out: dict[str, object] = {
            "id": self.id,
            "title": self.title,
            "root_cause": self.root_cause,
            "impact": self.impact,
            "score": {
                "reach": self.score.reach,
                "impact": self.score.impact,
                "confidence": self.score.confidence,
                "effort": self.score.effort,
                "priority": self.score.priority,
            },
            "violation_codes": self.violation_codes,
            "affected_files": self.affected_files,
            "violation_count": self.violation_count,
            "learn_more": self.learn_more,
        }
        if self.pattern_recommendation is not None:
            out["pattern_recommendation"] = self.pattern_recommendation.to_dict()
        return out


@dataclass(frozen=True)
class LayerHealth:
    """Health metrics for a single architectural layer."""
    layer: str
    file_count: int
    violation_count: int
    violation_density: float
    hotspot_files: list[str]
    primary_issues: list[str]

    def to_dict(self) -> dict[str, object]:
        """Convert to dictionary for serialization."""
        return {
            "layer": self.layer,
            "file_count": self.file_count,
            "violation_count": self.violation_count,
            "violation_density": self.violation_density,
            "hotspot_files": self.hotspot_files,
            "primary_issues": self.primary_issues,
        }


@dataclass(frozen=True)
class ArchitecturalHealthReport:
    """Complete systemic analysis of codebase health."""
    overall_score: int
    findings: list[SystemicFinding]
    pattern_recommendations: list[DesignPatternRecommendation]
    layer_health: list[LayerHealth]
    violation_details: list[ViolationWithFixInfo]
    portability_assessment: str
    blocking_gate: str | None

    def to_dict(self) -> dict[str, object]:
        """Convert to dictionary for serialization (e.g. JSON)."""
        return {
            "version": "2.0.0",
            "health_score": self.overall_score,
            "blocking_gate": self.blocking_gate,
            "portability_assessment": self.portability_assessment,
            "systemic_findings": [f.to_dict() for f in self.findings],
            "pattern_recommendations": [p.to_dict() for p in self.pattern_recommendations],
            "layer_health": {lh.layer: lh.to_dict() for lh in self.layer_health},
            "violation_details": [v.to_dict() for v in self.violation_details],
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

    def to_dict(self) -> dict[str, list[ViolationWithFixInfoDictRequired | ViolationWithFixInfoDict]]:
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

    def to_dict(
        self,
    ) -> dict[
        str,
        str
        | dict[str, int]
        | dict[str, list[ViolationWithFixInfoDictRequired | ViolationWithFixInfoDict]],
    ]:
        """Convert to dictionary for serialization."""
        return {
            "version": self.version,
            "timestamp": self.timestamp,
            "summary": self.summary.to_dict(),
            "violations": self.violations.to_dict(),
        }
