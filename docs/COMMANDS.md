# Excelsior Commands

## plan vs plan-fix vs generate-guidance

- **plan** (future): A planned command that will generate a full **PLAN.md** from the health report (Phase E of the UX overhaul). Not yet implemented.

- **plan-fix**: Generates a **single-rule fix plan** markdown from the latest AI handover. Example: `excelsior plan-fix excelsior.W9015` reads `.excelsior/health/ai_handover.json`, filters to that rule, and writes a fix plan under `.excelsior/fix_plans/`. Use this to get a focused, actionable plan for one rule before applying fixes.

- **generate-guidance**: Produces **proactive guidance** from the rule registry (e.g. `docs/GENERATION_GUIDANCE.md`) and can append a summary to `.cursorrules`. It iterates over rules’ proactive guidance and reference docs so humans and AI can follow best practices without re-reading every rule. Run after adding or changing rules to refresh the guidance doc.

## Quick reference

| Command             | Purpose |
|---------------------|--------|
| `excelsior init`    | Bootstrap project (config, gates, .cursorrules). |
| `excelsior check`   | Run full gated audit (Ruff → Mypy → Excelsior); tables + audit trail. |
| `excelsior health`  | Run audit + health analysis; score, findings, action plan; writes `.excelsior/health/`. |
| `excelsior fix`     | Apply fixes from last audit (optionally filtered). |
| `excelsior plan --rule <code>` | Single-rule fix plan from last handover. |
| `excelsior docs [topic]` | Explain rule (W9004), pattern (adapter, facade), or scoring. |
| `excelsior generate-guidance` | Regenerate GENERATION_GUIDANCE.md (and optional .cursorrules append). |
| `excelsior stub-create` | Create stub files for missing modules (e.g. W9019). |
