# Excelsior Commands

Quick reference for all CLI commands. See [QUICKSTART.md](QUICKSTART.md) for a guided walkthrough.

## Command Summary

| Command | Purpose |
|---------|---------|
| `excelsior init` | Bootstrap project: `.agent/`, `ARCHITECTURE_ONBOARDING.md`, `docs/GENERATION_GUIDANCE.md`, Ruff config, Knowledge Graph. |
| `excelsior check` | Run gated audit (Import-Linter → Ruff → Mypy → Excelsior → Ruff) + health report. |
| `excelsior fix` | Apply auto-fixes. `--iterative` for fix/check loop; `--stub MODULE` for .pyi stubs. |
| `excelsior plan` [topic] | Explain rule/pattern/scoring or generate fix plan. No topic = list topics. |
| `excelsior blueprint` | Strategic refactoring suggestions from Knowledge Graph. Requires `check` first. |
| `excelsior verify` | Diff current state vs baseline. `--baseline` to save baseline. |

---

## init

```bash
excelsior init [--template NAME] [--check-layers] [--guidance-only] [--skip-guidance] [--cursorrules]
```

- **Default**: Full scaffold (agent docs, onboarding, Ruff wizard, guidance, Knowledge Graph).
- `--guidance-only`: Regenerate `docs/GENERATION_GUIDANCE.md` only (no scaffold).
- `--skip-guidance`: Skip guidance generation during scaffold.
- `--cursorrules`: Append Excelsior section to `.cursorrules` when generating guidance.
- `--check-layers`: Verify active layer configuration.
- `--template`: Pre-configure for specific frameworks.

**Note:** There is no standalone `generate-guidance` command; use `excelsior init --guidance-only` to refresh the guidance doc.

---

## check

```bash
excelsior check [path] [--linter all|ruff|mypy|excelsior|import_linter] [--view by_code|by_file] [--no-health]
```

- Runs gated sequential audit. First blocking pass stops later passes.
- Writes `.excelsior/check/last_audit.json`, `.excelsior/check/ai_handover.json`.
- By default, also runs health analysis and writes `.excelsior/health/` (use `--no-health` to skip).
- Exit 1 if violations found.

---

## fix

```bash
excelsior fix [path] [--linter all|...] [--iterative] [--manual-only] [--comments] [--confirm] [--stub MODULE] ...
```

- **Multi-pass fix pipeline**: Ruff → W9015 type hints → architectural → [governance comments] → Ruff.
- `--iterative`: Loop fix → check until clean or max passes (replaces former `ai-workflow`).
- `--manual-only`: Show manual fix suggestions only (no file changes).
- `--comments`: Inject governance comments into files.
- `--stub MODULE`: Create `.pyi` stub for a module (e.g. `--stub foo.bar`).
- `--confirm`: Require confirmation before each fix.

---

## plan

```bash
excelsior plan [topic] [--violation-index N] [--source health|check|fix] [--explain]
```

- **No topic**: List available topics (rules, patterns, scoring).
- **With topic**: Explain the rule/pattern, or generate a fix plan from the latest handover.
  - Examples: `excelsior plan W9015`, `excelsior plan adapter`, `excelsior plan excelsior.W9004`
- `--source`: Which handover to use (default: `health`).
- `--violation-index`: Which occurrence (0-based) for the fix plan.
- `--explain`: Show explanation only, skip fix plan.

**Output:** Fix plans go to `.excelsior/fix_plans/<rule_id>_<timestamp>.md`.

---

## blueprint

```bash
excelsior blueprint [--source check|health]
```

- Diagnoses architectural hotspots using the Knowledge Graph.
- Suggests OO patterns for systemic refactoring.
- **Requires:** Run `excelsior check` first (creates handover at `.excelsior/check/ai_handover.json`).
- **Output:** `.excelsior/BLUEPRINT.md`

---

## verify

```bash
excelsior verify [path] [--baseline]
```

- `--baseline`: Save current check+health state to `.excelsior/verify/baseline.json`.
- No `--baseline`: Re-run check, compare total violations and health score to baseline. Exit 1 if violations increased.

---

## Workflow Summary

1. **install** → `pip install excelsior-architect`
2. **init** → `excelsior init`
3. **check** → `excelsior check`
4. **fix** or **plan** → `excelsior fix` or `excelsior plan <rule_id>`
5. **blueprint** (optional) → `excelsior blueprint`
