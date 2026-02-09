from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class RefactoringStep:
    phase: int
    action: str
    target: str
    description: str


@dataclass(frozen=True)
class StrategicBlueprint:
    strategy_id: str
    pattern_name: str
    rationale: str
    affected_files: List[str]
    steps: List[RefactoringStep] = field(default_factory=list)

    def to_markdown(self) -> str:
        lines = [
            f"# Blueprint: {self.pattern_name}",
            f"**ID:** {self.strategy_id}",
            f"**Rationale:** {self.rationale}",
            "",
            "## Affected Files",
        ]
        for f in self.affected_files:
            lines.append(f"- `{f}`")

        lines.extend(["", "## Implementation Plan"])
        current_phase = -1
        for step in self.steps:
            if step.phase != current_phase:
                lines.append(
                    f"\n### Phase {step.phase}: {self._phase_name(step.phase)}")
                current_phase = step.phase
            lines.append(
                f"- [ ] **{step.action}** ({step.target}): {step.description}")

        return "\n".join(lines)

    def _phase_name(self, phase: int) -> str:
        names = {0: "Discovery", 1: "Structural Refactor",
                 2: "Integration", 3: "Verification"}
        return names.get(phase, "Execution")
