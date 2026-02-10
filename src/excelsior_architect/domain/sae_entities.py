from dataclasses import dataclass, field
from typing import List, Optional, TypedDict


class CodeSnippetDict(TypedDict, total=False):
    """Shape of a code snippet for blueprint display."""

    file_path: str
    symbol_or_line: str
    source: str


class RecommendedStrategy(TypedDict):
    """Graph gateway return type: pattern recommendation with affected files and score."""

    pattern: str
    rationale: str
    affected_files: List[str]
    violations: List[str]
    score: int


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
    current_snippets: List[CodeSnippetDict] = field(default_factory=list)

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

        if self.current_snippets:
            lines.extend(["", "## Current State (code to refactor)"])
            seen: set[tuple[str, str]] = set()
            for snip in self.current_snippets:
                fp = snip.get("file_path", "")
                sym = snip.get("symbol_or_line", "")
                key = (fp, sym)
                if key in seen:
                    continue
                seen.add(key)
                src = snip.get("source", "")
                display_path = fp.split("/")[-1] if "/" in fp else fp
                lines.append(f"\n**`{display_path}`** — `{sym}`")
                lines.append("```python")
                lines.append(src)
                lines.append("```")

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
