# Excelsior Quick Start

A guided step-by-step walkthrough to get Excelsior running on your Python project.

## Prerequisites

- Python 3.9+
- A Python project with a `pyproject.toml` (or Excelsior will scaffold one)

---

## Step 1: Install

```bash
pip install excelsior-architect
```

Verify installation:

```bash
excelsior --help
```

---

## Step 2: Initialize

From your project root:

```bash
excelsior init
```

**What this does:**

- Creates `.agent/instructions.md` and `.agent/pre-flight.md` (AI agent onboarding)
- Creates `ARCHITECTURE_ONBOARDING.md` with a 3-phase refactor plan (if missing)
- Injects a handshake protocol into your `Makefile`
- Runs an interactive Ruff configuration wizard (if you have Ruff and `pyproject.toml`)
- Generates `docs/GENERATION_GUIDANCE.md` (proactive coding guidelines from the rule registry)
- Hydrates the Knowledge Graph with violation and pattern data (enables `blueprint`)

**Options:**

- `--guidance-only` – Regenerate `docs/GENERATION_GUIDANCE.md` only
- `--skip-guidance` – Skip guidance generation
- `--cursorrules` – Append Excelsior section to `.cursorrules` when generating guidance
- `--check-layers` – Verify active layer configuration
- `--template <name>` – Pre-configure for specific frameworks

---

## Step 3: Run the Audit

```bash
excelsior check
```

**What this does:**

Runs a **gated sequential audit** in order. The first pass with violations blocks later passes:

1. **Import-Linter** – Layer/dependency contracts
2. **Ruff** (I, UP, B) – Import order, pyupgrade, bugbear
3. **Mypy** – Type checking
4. **Excelsior** – Clean Architecture rules (Pylint plugin)
5. **Ruff** (E, F, W, C90, …) – Code quality

**Output:**

- `.excelsior/check/last_audit.json` – Full audit result
- `.excelsior/check/ai_handover.json` – Structured handover for AI agents and fix plans
- `.excelsior/health/last_audit.json` – Health report (unless `--no-health`)
- `.excelsior/health/ai_handover.json` – Health handover for `blueprint` and `plan`

If violations exist, the CLI suggests next steps (e.g. `excelsior plan <rule_id>`).

---

## Step 4: Fix Violations

### Option A: Auto-fix

```bash
excelsior fix
```

Applies deterministic fixes across multiple passes (Ruff, type hints, architectural transforms). Use `--iterative` to loop fix → check until clean.

### Option B: Guided fix (per rule)

```bash
excelsior plan W9015
```

Generates a fix plan for a specific rule. Omit the topic to list available topics:

```bash
excelsior plan
```

**Common rules:** `W9015` (type hints), `W9004` (forbidden I/O), `adapter`, `facade`, etc.

---

## Step 5: Strategic Blueprint (Optional)

After running `excelsior check`:

```bash
excelsior blueprint
```

**What this does:**

Uses the Knowledge Graph to diagnose systemic architectural hotspots and suggest OO patterns. Writes `.excelsior/BLUEPRINT.md` with pattern recommendations.

Use `--source health` to use the health handover instead of the check handover (default: `check`).

---

## Verify Against Baseline

Track regression over time:

```bash
# Save current state as baseline
excelsior verify --baseline

# ... make changes ...

# Compare to baseline (exit 1 if violations increased)
excelsior verify
```

---

## Summary Flow

```
install  →  init  →  check  →  fix (or plan)  →  blueprint
   │          │         │            │                  │
   │          │         │            │                  └── Optional: strategic refactoring
   │          │         │            └── Auto-fix or guided per-rule plans
   │          │         └── Gated audit, writes handover artifacts
   │          └── Scaffold config, agent docs, Knowledge Graph
   └── pip install excelsior-architect
```

---

## Next Steps

- **[EXCELSIOR_PASSES_AND_GATES.md](EXCELSIOR_PASSES_AND_GATES.md)** – Pass order, gating behavior, Ruff rule groups
- **[COMMANDS.md](COMMANDS.md)** – Full command reference
- **[RULES.md](../RULES.md)** – Prime Directives catalog and fix examples
