# CLI Refactor Plan: Thin Front Controller

## Manual Review Summary

`cli.py` is **dangerously close to (if not already) a god class**. It acts as the front controller but holds too much responsibility:

- **Parser setup** (`_build_parser`) – acceptable.
- **Check flow**: gather linters, print tables, save audit trail, handover message.
- **Fix flow**: manual-only vs ruff vs excelsior; adapter iteration, telemetry, exit codes.
- **Init flow**: delegates to `Scaffolder` – good.

**Problems:**

1. **Check command**: `check_command` orchestrates gathering, table printing, audit persistence, and handover. Table formatting (`_print_audit_tables`, `_process_results`, `_is_rule_fixable`), audit persistence (`_save_audit_trail`, `_write_violations_section`, `_violations_with_fix_info`), and “has violations” logic all live in the CLI layer.

2. **Fix command**: `_run_fix_*` functions contain adapter iteration, IO (print), and exit handling. Manual-only mode builds adapter lists, gathers results, and prints guidance inline.

3. **Adapter instantiation**: Multiple places create `MypyAdapter()`, `ExcelsiorAdapter()`, etc. (in gather, print, save, fix manual-only). No single place owns adapter lifecycle.

4. **Mixed concerns**: Formatting (e.g. ReportSchema, ColumnDefinition), persistence (`.excelsior/`), and routing are intertwined. Hard to test or reuse.

## Target Architecture: Thin Controller

**Front controller** (`main` + `_build_parser`):

- Parse args.
- Resolve command → **use case** or **handler**.
- Call use case; map result to exit code / output.
- No business logic, no adapter creation, no file I/O.

**Proposed use cases / handlers:**

| Command | Use case / handler | Responsibility |
|--------|---------------------|----------------|
| `check` | `CheckAuditUseCase` | Run linters (via adapters), produce “audit result” (e.g. dataclass: mypy, excelsior, il, ruff, has_violations). |
| `check` output | `AuditReporter` (interface) | Turn audit result into tables + handover message. Implementations: terminal, JSON, etc. |
| `check` persistence | `AuditTrailService` | Write `.excelsior/last_audit.{json,txt}` from audit result. |
| `fix` | `ApplyFixesUseCase` (existing) + `FixCommandHandler` | Handler interprets `--linter`, `--manual-only`, etc.; calls use case or manual-only flow. |
| `fix` manual-only | `ManualFixSuggestionsUseCase` | Gather results from adapters, return structure (fixable vs manual, per rule instructions). CLI only formats and prints. |
| `init` | `InitProjectUseCase` | Wrap `Scaffolder.init_project`; optionally own template/layer checks. |

**Dependency injection:**

- Adapters (Mypy, Excelsior, IL, Ruff) created once (e.g. in container or factory) and injected into use cases.
- `CheckAuditUseCase` receives adapter interfaces, not concretions from within the CLI.

## Refactor Steps (Incremental)

1. **Extract `CheckAuditUseCase`**
   - Input: `target_path`, `linter` filter.
   - Output: audit result (lists of `LinterResult` per tool + `has_violations`).
   - Move `_gather_linter_results` logic into use case (or an orchestration service it uses). Keep CLI free of adapter instantiation.

2. **Extract `AuditReporter`**
   - Input: audit result.
   - Output: formatted tables + handover text (or side-effect print).
   - Move `_print_audit_tables`, `_process_results`, `_is_rule_fixable` into a reporter implementation. CLI only calls `reporter.report(audit_result)`.

3. **Extract `AuditTrailService`**
   - Input: audit result (+ adapters for fixability/instructions).
   - Output: none (writes to `.excelsior/`).
   - Move `_save_audit_trail`, `_write_violations_section`, `_violations_with_fix_info` into this service.

4. **Thin `check` flow**
   - `_run_check` → get telemetry, call `CheckAuditUseCase`, then `AuditReporter`, then `AuditTrailService`, then map `has_violations` to exit code.

5. **Extract `ManualFixSuggestionsUseCase`**
   - Input: `target_path`, `linter` filter.
   - Output: structured list of (rule, fixable, message, locations, manual_instructions).
   - Move `_run_fix_manual_only` logic into this use case. CLI only prints the structure.

6. **Introduce `FixCommandHandler`**
   - Interprets fix args; calls `ApplyFixesUseCase`, `ManualFixSuggestionsUseCase`, or Ruff-specific path.
   - `_run_fix` becomes a thin wrapper over this handler.

7. **Centralize adapter creation**
   - Factory or container provides adapters. Use cases receive them via constructor. CLI never instantiates adapters.

## Principles

- **Thin controller**: CLI parses, routes, calls use cases, maps to exit/output.
- **Single responsibility**: Each use case / service does one thing.
- **Testability**: Use cases and reporters can be unit-tested without subprocess or CLI.
- **Convention over configuration**: Reuse existing DI container (`ExcelsiorContainer`) and follow `docs/ARCHITECTURE_PRINCIPLES.md`.

## Notes

- `stellar_ui_kit` (ReportSchema, TerminalReporter) remains an implementation detail of `AuditReporter`; the use case stays agnostic.
- Fixability and manual instructions belong in the use case / audit result (or a dedicated “fix guidance” service), not buried in CLI helpers.
