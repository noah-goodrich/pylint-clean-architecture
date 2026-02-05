<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/noah-goodrich/pylint-clean-architecture/main/assets/hero-dark.png">
  <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/noah-goodrich/pylint-clean-architecture/main/assets/hero-light.png">
  <img alt="Stellar Engineering Command Banner" src="https://raw.githubusercontent.com/noah-goodrich/pylint-clean-architecture/main/assets/hero-light.png" width="100%">
</picture>

![PyPI](https://img.shields.io/pypi/v/pylint-clean-architecture?color=C41E3A&labelColor=333333)
![Build Status](https://img.shields.io/github/actions/workflow/status/noah-goodrich/pylint-clean-architecture/ci.yml?branch=main&color=007BFF&labelColor=333333&label=Build%20Status)
![Python Versions](https://img.shields.io/pypi/pyversions/pylint-clean-architecture?color=F9A602&labelColor=333333)
![License](https://img.shields.io/github/license/noah-goodrich/pylint-clean-architecture?color=F9A602&labelColor=333333)

# 🛡️ Excelsior v2: Architectural Autopilot

Captain's Log: High-authority Pylint module for enforcing **Prime Directives** (Clean Architecture) and preventing **Hull Integrity Breaches** (Technical Debt) in Python projects.

Enforcing architectural boundaries, dependency rules, and design patterns to ensure the fleet remains operational and modular.

## Features

*   **Layer Boundary Enforcement**: Ensures Prime Directives are maintained between Domain, UseCase, and Infrastructure.
*   **The Silent Core Rule (W9013)**: Guarantees that Domain/UseCase layers remain free of `print`, `logging`, and console I/O, forcing delegation to Interfaces/Adapters.
*   **Dependency Injection Checks**: Forbids unauthorized instantiation of infrastructure modules within UseCases.
*   **Design Pattern Enforcement**: Detects "naked returns" and other architectural anomalies.
*   **Law of Demeter**: Prevents tight coupling through deep method chains.
*   **Contract Integrity**: Verifies that Infrastructure implements Domain Protocols correctly.
*   **Anti-Bypass Guard**: Prevents "lazy" disabling of Prime Directives without high-level authorization (Justification).

## Docking Procedures

```bash
pip install pylint-clean-architecture
```

## Flight Manual

Add the plugin to your `pyproject.toml` or Pylint configuration:

```toml
[tool.pylint.main]
load-plugins = ["clean_architecture_linter"]
```

Run Pylint as usual:

```bash
pylint src/
```

### Excelsior Check and Fix: Passes and Gates

Excelsior runs a **gated sequential audit** (check) and a **multi-pass fix** pipeline (fix). Layers first, then style/typing, then code quality.

- **Check:** Pass 1 (Import-Linter layer contracts) → Pass 2 (Ruff I/UP/B) → Pass 3 (Mypy) → Pass 4 (Excelsior architectural) → Pass 5 (Ruff code quality). All passes are blocking; the first with violations stops the pipeline.
- **Fix:** Pass 1 (Ruff I/UP/B) → Pass 2 (W9015 type hints) → cache clear → Pass 3 (architectural code) → Pass 4 (governance comments) → Pass 5 (Ruff code quality). Pass 3 and Pass 4 are **gated**: they run only when the full audit passes (no import_linter/ruff/mypy/excelsior block). Pass 1, 2, and 5 always run when enabled.

See **[docs/EXCELSIOR_PASSES_AND_GATES.md](docs/EXCELSIOR_PASSES_AND_GATES.md)** for full details: pass order, blocked-by values, Ruff rule groups, and recommended workflow.

### Excelsior CLI Commands

| Command | Description |
|--------|-------------|
| `excelsior check` [path] | Run the gated audit (import-linter → Ruff → Mypy → Excelsior → Ruff). Writes `.excelsior/last_audit_check.json`, `.excelsior/ai_handover_check.json`. |
| `excelsior fix` [path] [--comments] | Multi-pass auto-fix (Ruff → W9015 → architecture → [governance comments if `--comments`] → Ruff). Default: no in-file comments; use handover + plan-fix for instructions. Writes `.excelsior/last_audit_fix.json`, `.excelsior/ai_handover_*.json`. |
| `excelsior init` [--template …] [--check-layers] | Initialize project: creates `.agent/instructions.md`, `.agent/pre-flight.md`, `ARCHITECTURE_ONBOARDING.md` (if missing), appends handshake to Makefile; optionally runs Ruff wizard to add `[tool.excelsior.ruff]` to `pyproject.toml`. |
| `excelsior generate-guidance` [--output-dir docs] | Generate `docs/GENERATION_GUIDANCE.md` from the rule registry; optionally append to `.cursorrules` if present. |
| `excelsior plan-fix` \<rule_id\> [--violation-index N] [--source check\|fix\|ai_workflow] | Generate a single-violation fix plan markdown from the latest handover (`.excelsior/fix_plans/<rule_id>_<timestamp>.md`). |
| `excelsior ai-workflow` [path] | Run fix then check; exit 1 if violations remain. Writes `.excelsior/last_audit_ai_workflow.json`. |

### Excelsior Auto-Fix Suite

Excelsior can automatically repair several common architectural and stylistic violations.

Usage:
```bash
excelsior fix
```

Available Fixers:
*   **Structural Integrity**: Generates missing `__init__.py` and `py.typed` markers.
*   **Signature Correction**: Automatically adds `-> None` to `__init__` methods.
*   **Domain Immutability**: Enforces `frozen=True` on dataclasses within the Domain layer.
*   **Type Integrity**: Opportunistically auto-imports `Optional`, `Any`, `List`, `Dict`, etc., when used in type hints but not imported.
*   **Redundancy Removal**: Cleans up duplicate annotations that trigger `no-redef` errors.

### AI Coding Assistant Support


## Console Calibration

The module is calibrated via `[tool.clean-arch]` in `pyproject.toml`.

```toml
[tool.clean-arch]
# 1. Project Type Presets (generic, cli_app, fastapi_sqlalchemy)
project_type = "generic"

# 2. Strict Visibility Enforcement
visibility_enforcement = true

# 3. Silent Core Calibration
silent_layers = ["Domain", "UseCase"]
allowed_io_interfaces = ["TelemetryPort", "LoggerPort"]

# 4. Shared Kernel (Allow cross-cutting concerns anywhere)
shared_kernel_modules = ["logging_utils", "clean_architecture_linter.interface.telemetry"]

# 5. Custom Layer Mapping (Map directory regex patterns to layers)
[tool.clean-arch.layer_map]
"services" = "UseCase"
"infrastructure/clients" = "Infrastructure"
"domain/models" = "Domain"
```

## Prime Directives

See [RULES.md](RULES.md) for a complete catalog of enforced Prime Directives and "Clean Fix" examples.

## Mission Log

- **[CHANGELOG.md](CHANGELOG.md)** - Mission history and architectural updates

## Contributing

1.  Fork the repo.
2.  Install dependencies: `make install`.
3.  Run tests: `make test`.
4.  Submit a PR.
