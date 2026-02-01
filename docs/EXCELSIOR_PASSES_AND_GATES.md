# Excelsior: Passes and Gates

This document explains how **Excelsior check** and **Excelsior fix** work: the multiple passes, gating behavior, and what blocks vs. what does not.

---

## Raw subprocess logs

When Ruff, Mypy, or Pylint run (during `excelsior check` or fix), their raw stdout/stderr are appended to:

- `.excelsior/logs/raw_ruff.log`
- `.excelsior/logs/raw_mypy.log`
- `.excelsior/logs/raw_pylint.log`

This gives you the **unfiltered tool output** when debugging a failed audit. Each run adds a timestamped section.

---

## Overview

Excelsior runs checks and fixes in a **fixed order**, with **gates** so that later phases only run when earlier ones pass. The idea is:

1. **Layer contracts first** – Import-linter enforces dependency/layer boundaries (who may import whom). Fix structural violations before touching style.
2. **Import & typing** – Ruff (I, UP, B) and Mypy normalize import style and type correctness.
3. **Architectural (Excelsior)** – Clean Architecture rules (Demeter, silent core, etc.). Must pass before we run code-quality checks.
4. **Code quality last** – Ruff (E, F, W, C90, …) for style and complexity. Run only when the dependency graph and architecture are acceptable.

---

## Excelsior Check: Gated Sequential Audit

`excelsior check` runs a **gated sequential audit**. Each pass runs in order; **the first pass that reports violations “blocks”** and later passes are **not run**. The audit result includes whatever was collected up to (and including) the blocking pass.

### Pass order and blocking

| Pass | Name | Source | Blocks? | Description |
|------|------|--------|--------|-------------|
| **1** | Layer contracts | Import-Linter | **Yes** | Dependency/layer contracts (e.g. domain must not import infrastructure). Violations block. |
| **2** | Import & typing | Ruff (I, UP, B) | **Yes** | Import order (I), pyupgrade (UP), bugbear (B). Violations block. |
| **3** | Type integrity | Mypy | **Yes** | Type errors block. |
| **4** | Architectural | Pylint/Excelsior | **Yes** | Clean Architecture rules. Violations block so we don't run code quality on broken architecture. |
| **5** | Code quality | Ruff (E, F, W, C90, …) | **Yes** | Style, complexity, etc. Violations block. |

All five passes are **blocking**. If Pass 1 has violations, the audit stops and returns `blocked_by="import_linter"`. If Pass 4 (Excelsior) has violations, the audit stops and returns `blocked_by="excelsior"`; Pass 5 (Ruff code quality) is not run. Only when all five passes pass do you get `blocked_by=None`.

### Ruff rule sets

- **Pass 2 – Import & typing:** `RUFF_IMPORT_TYPING_SELECT = ["I", "UP", "B"]`  
  (isort, pyupgrade, bugbear.)

- **Pass 5 – Code quality:** `RUFF_CODE_QUALITY_SELECT` includes E, F, W, C90, N, PL, PT, A, C4, SIM, ARG, PTH, RUF.

So “Ruff” can block in two different phases (Pass 2 and Pass 5), each with a different subset of rules.

### When Ruff is disabled

If Ruff is disabled in config (`ruff_enabled = False`), Pass 2 and Pass 5 are skipped. Pass 1 (Import-Linter), Pass 3 (Mypy), and Pass 4 (Excelsior) still run; any of them can block.

### Blocked-by values

`AuditResult.blocked_by` may be: `"import_linter"` (Pass 1), `"ruff"` (Pass 2 or 5), `"mypy"` (Pass 3), `"excelsior"` (Pass 4), or `None` (no blocking).

---

## Excelsior Fix: Multi-Pass Fix Suite

`excelsior fix` runs a **multi-pass fix** pipeline. It applies fixes in a fixed order and uses the **same gated audit** internally for Pass 3 and Pass 4: if the audit is blocked, those passes are **skipped** (no architectural or governance-comment fixes applied).

### Fix pass order

| Pass | Name | What it does | Gated? |
|------|------|--------------|--------|
| **1** | Ruff import & typing | `ruff check --fix` with I, UP, B only. | No – always runs (if Ruff enabled). |
| **2** | Type hints (W9015) | Injects missing type hints (MissingTypeHintRule). | No – always runs. |
| *(cache clear)* | Astroid cache | Clears inference cache after Pass 1–2 so Pass 3 sees updated code. | — |
| **3** | Architectural code | Applies Excelsior **code** fixes (e.g. immutability, signatures), **excluding** W9015 and W9006. | **Yes** – runs full gated audit; if blocked, Pass 3 is skipped. |
| **4** | Governance comments | Applies **comment-only** fixes (e.g. W9006). | **Yes** – same audit; if blocked, Pass 4 is skipped. |
| **5** | Ruff code quality | `ruff check --fix` with E, F, W, C90, … only. | No – always runs (if Ruff enabled). |

So:

- **Not gated:** Pass 1 (Ruff I/UP/B), Pass 2 (W9015), Pass 5 (Ruff code quality). They always run (subject to config).
- **Gated:** Pass 3 and Pass 4. Each runs `check_audit_use_case.execute(target_path)`. If `audit_result.is_blocked()` is true (e.g. import_linter, ruff, mypy, or excelsior), that pass is skipped and the corresponding fixes are not applied.

### Why Pass 3 and Pass 4 are gated

- **Pass 3 (architectural code):** We only apply architectural code fixes when the gated audit has passed (layer contracts, import/typing, Mypy, and Excelsior). That way we are not fixing architecture on a codebase that still has contract or type violations.
- **Pass 4 (governance comments):** Same idea: we only add governance comments when the codebase has passed the same gates, so we’re not commenting on a broken or inconsistent state.

If the audit is blocked (e.g. by Import-Linter, Ruff, Mypy, or Excelsior), you will see messages like:

- `⚠️  Pass 3 skipped: Audit blocked by import_linter`
- `⚠️  Pass 4 skipped: Audit blocked by excelsior`

and governance/architectural fixes will not be applied until you clear the blocking violations (e.g. with `excelsior fix` repeatedly, or by fixing import-linter/Ruff/Mypy/Excelsior manually).

### Summary: what blocks vs what doesn’t

**During `excelsior check`:**

- **Block:** Import-Linter (Pass 1), Ruff import/typing (Pass 2), Mypy (Pass 3), Excelsior (Pass 4), Ruff code quality (Pass 5). First failure sets `blocked_by` and stops later passes.

**During `excelsior fix`:**

- **Gated (skipped when audit is blocked):** Pass 3 (architectural code), Pass 4 (governance comments). Blocking can be from import_linter, ruff, mypy, or excelsior.
- **Not gated:** Pass 1 (Ruff I/UP/B), Pass 2 (W9015), Pass 5 (Ruff code quality). They run regardless of audit result.

---

## Recommended workflow

1. Run **`excelsior check`** to see the current state and which gate is blocking (if any).
2. Run **`excelsior fix`** to auto-fix what can be fixed (Ruff passes 1 and 5, W9015, and when unblocked, Pass 3 and 4).
3. Re-run **`excelsior check`**. If still blocked (e.g. on Import-Linter, Mypy, Excelsior, or Ruff code quality), fix remaining issues manually or by iterating fix/check until the gate passes.
4. Once the audit is not blocked, Pass 3 and Pass 4 of fix will run on the next `excelsior fix`, applying architectural and governance-comment fixes.

---

## Reference: Ruff rule groups

Defined in `clean_architecture_linter.infrastructure.adapters.ruff_adapter`:

- **RUFF_IMPORT_TYPING_SELECT** = `["I", "UP", "B"]`  
  Used in check Pass 2 and fix Pass 1.

- **RUFF_CODE_QUALITY_SELECT** = `["E", "F", "W", "C90", "N", "PL", "PT", "A", "C4", "SIM", "ARG", "PTH", "RUF"]`  
  Used in check Pass 5 and fix Pass 5.

See [Ruff rule codes](https://docs.astral.sh/ruff/rules/) for the full list.
