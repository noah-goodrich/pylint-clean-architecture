# UX Overhaul Addendum: Commands, Terminal Width, Rename

Extends the Health UX Overhaul plan with: command simplification, terminal width/readability, and project/package rename to Excelsior.

## 1. Command Simplification (init to check to fix to done)

**Goal**: One clear path: init, check, fix, done. No overlapping commands.

**Proposed**:
- Merge **check** and **health**: One command `excelsior check` that runs full pipeline (linters + clustering + scoring). Default output = health-style report. Options: `--view by_code`, `--view by_file`, `--format json`. Artifacts under `.excelsior/check/`.
- Add **verify**: Re-run check and report before/after delta (the "done" step).
- Fold **ai-workflow** into **fix**: e.g. `fix --iterative` or `fix --max-passes 5`.
- Keep: plan-fix, generate-guidance, stub-create. Add from plan: plan, docs, explore.

**Result**: init, check, fix, verify, plan, plan-fix, docs, explore, generate-guidance, stub-create. Each command documents in --help what it produces and where.

## 2. Terminal Output: Width and Readability

**Goal**: Readable on narrow terminals (e.g. half-screen, 80-100 columns). Prefer "good at small width, cap there" over "expand and break on small."

**Design**:
- Assume a max terminal width (e.g. 88). Document it; allow override via env `EXCELSIOR_TERMINAL_WIDTH` or `--width`.
- Truncate or wrap all table cells and banners to that width. In reporters, truncate string fields before passing to tables (paths: last N segments; messages: first N chars + "...").
- Legends and prose: wrap at (width - 2). Full content available via `--format json`.

**Checklist**: Define default width (88), use everywhere; truncate/wrap tables and banners; document in --help and user docs.

## 3. Rename: Project and Package to Excelsior

**Goal**: Product = Excelsior. Repo/package = excelsior. Publish on PyPI as excelsior.

**Scope**: Repo/project name to excelsior; `src/excelsior_architect/` to `src/excelsior/`; all imports to `excelsior`; pyproject name, scripts, package-data, layer_map, importlinter, mypy_path, coverage, pylint load-plugins to excelsior; Pylint `load-plugins = ["excelsior"]` with plugin registerable from excelsior.

**Questions/concerns**:
1. **PyPI**: Check if "excelsior" is taken; if so use excelsior-tool or similar.
2. **Pylint plugin**: Confirm where register(linter) lives and that it is callable as the excelsior module.
3. **Breakage**: Single big rename; document migration (import and config name change).
4. **Order**: Rename can be done before or after UX phases; doing it early means all new work lands in excelsior.
