"""Use case: generate a single-violation fix plan markdown from the latest handover."""

import json
import re
from datetime import datetime
from typing import Any, TypedDict

from excelsior_architect.domain.protocols import (
    ArtifactStorageProtocol,
    GuidanceServiceProtocol,
)


class HandoverViolation(TypedDict, total=False):
    """Shape of a single violation entry in ai_handover.json."""
    code: str
    message: str
    locations: list[str]
    manual_instructions: str
    prompt_fragment: str


class PlanFixUseCase:
    """Generate a dedicated markdown fix plan for one violation (rule_id + optional index)."""

    def __init__(
        self,
        artifact_storage: ArtifactStorageProtocol,
        guidance_service: GuidanceServiceProtocol,
    ) -> None:
        self.artifact_storage = artifact_storage
        self.guidance_service = guidance_service

    def execute(
        self,
        rule_id: str,
        violation_index: int = 0,
        source: str = "check",
    ) -> str:
        """
        Read the latest handover, select the Nth violation for rule_id, write a fix plan markdown.

        Args:
            rule_id: Registry key (e.g. excelsior.W9015, mypy.no-any-return).
            violation_index: Which occurrence to use (0-based). Default 0.
            source: Handover source ('check', 'fix', 'ai_workflow'). File: ai_handover_{source}.json.

        Returns:
            Logical key of the written fix plan artifact (e.g. fix_plans/mypy_union_attr_20250128.md).

        Raises:
            FileNotFoundError: If the handover artifact does not exist.
            IndexError: If no violation matches rule_id or violation_index is out of range.
        """
        handover_key = f"{source}/ai_handover.json" if source else "ai_handover.json"

        if not self.artifact_storage.exists(handover_key):
            raise FileNotFoundError(
                f"Handover not found: {handover_key}. Run 'excelsior check' (or fix/ai-workflow) first."
            )

        content = self.artifact_storage.read_artifact(handover_key)
        handover = json.loads(content)

        violations_by_rule = handover.get("violations_by_rule") or {}
        matching: list[dict[str, Any]] = []
        for entries in violations_by_rule.values():
            for entry in entries:
                if entry.get("rule_id") == rule_id:
                    matching.append(entry)

        from typing import cast
        violation = cast(HandoverViolation, matching[violation_index])
        return self._write_fix_plan(rule_id, violation)

    def write_fix_plan(self, rule_id: str, violation: HandoverViolation) -> str:
        """
        Write a fix plan markdown for a single violation. Caller must validate
        that the violation exists and is selected (Interface responsibility).
        """
        return self._write_fix_plan(rule_id, violation)

    def _write_fix_plan(self, rule_id: str, violation: HandoverViolation) -> str:
        """Build markdown and write to fix_plans/<rule_id>_<timestamp>.md artifact."""
        safe_rule_id = re.sub(r"[./\\]", "_", rule_id)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        fix_plan_key = f"fix_plans/{safe_rule_id}_{timestamp}.md"

        code = violation.get("code", "")
        message = violation.get("message", "")
        locations = violation.get("locations") or []
        manual_instructions = violation.get(
            "manual_instructions") or "See registry for this rule_id."
        prompt_fragment = violation.get("prompt_fragment") or ""

        locations_bullet = "\n".join(
            f"- {loc}" for loc in locations) if locations else "- N/A"

        commands_bullet = ""
        if locations:
            # Consolidate files to be fixed (list each file once)
            unique_files = sorted({loc.split(":")[0] for loc in locations})
            commands = [
                f"ruff check {f} --fix --unsafe-fixes" for f in unique_files]
            commands_bullet = "\n### Fix Commands\n\n```bash\n" + \
                "\n".join(commands) + "\n```"

        steps_extra = ""
        linter, _, rule_code = rule_id.partition(".")
        if rule_code:
            entry = self.guidance_service.get_entry(linter, rule_code)
            if entry and isinstance(entry, dict):
                short = entry.get("short_description")
                if short:
                    steps_extra = f"\n- **Registry:** {short}"

        parts = [
            f"# Fix plan: {rule_id}",
            "",
            "Use this as a single-task workspace for an AI or developer to fix this violation.",
            "",
            "---",
            "",
            "## Violation",
            "",
            f"- **Rule ID:** `{rule_id}`",
            f"- **Code:** {code}",
            f"- **Message:** {message}",
            "",
            "### Locations",
            "",
            locations_bullet,
            "",
            commands_bullet,
            "",
            "---",
            "",
            "## Manual instructions",
            "",
            manual_instructions,
            "",
            "---",
            "",
            "## Prompt fragment (ready-to-paste)",
            "",
            "```",
            prompt_fragment.strip(),
            "```",
            "",
            "---",
            "",
            "## Steps",
            "",
            "1. Open the file(s) at the location(s) above.",
            "2. Apply the manual instructions to fix the violation.",
            "3. Run `excelsior check` to verify.",
            steps_extra,
            "",
        ]
        text = "\n".join(parts).replace("\n\n\n", "\n\n")
        self.artifact_storage.write_artifact(fix_plan_key, text)
        return fix_plan_key
