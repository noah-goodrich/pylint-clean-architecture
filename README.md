# pylint-clean-architecture

A powerful, highly-opinionated Pylint plugin for enforcing **Clean Architecture** (The Onion Architecture) principles in Python projects.

This linter acts as a "GPS" for your codebase, preventing technical debt by strictly enforcing architectural boundaries, dependency rules, and design patterns.

## Features

*   **Layer Boundary Enforcement**: Prevents inner layers (Domain, UseCase) from importing outer layers (Infrastructure, Interface).
*   **Dependency Injection Checks**: Forbids direct instantiation of infrastructure classes in UseCases.
*   **Design Pattern Enforcement**: Detects "naked returns" from repositories, delegation anti-patterns, and more.
*   **Law of Demeter**: Enforces loose coupling by flagging deep method chains.
*   **Contract Integrity**: Ensures Infrastructure classes correctly implement Domain Protocols.
*   **Anti-Bypass Guard**: Prevents "lazy" disabling of linter rules without justification.
*   **Snowflake Governance (Optional)**: Specific checks for Snowflake pipeline governance (gold layer rules, select star violations).

## Installation

```bash
pip install pylint-clean-architecture
```

### Optional Extras

To enable Snowflake-specific checks:

```bash
pip install "pylint-clean-architecture[snowflake]"
```

## Usage

Add the plugin to your `pyproject.toml` or Pylint configuration:

```toml
[tool.pylint.main]
load-plugins = ["clean_architecture_linter"]
```

Run Pylint as usual:

```bash
pylint src/
```

## Configuration

The linter is configured via `[tool.clean-arch]` in `pyproject.toml`.

```toml
[tool.clean-arch]
# 1. Project Type Presets (generic, cli_app, fastapi_sqlalchemy)
project_type = "generic"

# 2. Strict Visibility Enforcement
visibility_enforcement = true

# 3. Enabled Extensions
enabled_extensions = ["snowflake"]

# 4. Custom Layer Mapping (Map directory regex patterns to layers)
[tool.clean-arch.layer_map]
"services" = "UseCase"
"infrastructure/clients" = "Infrastructure"
"domain/models" = "Domain"

# 5. Snowflake Governance Config (if enabled)
governance_module_prefixes = ["my_project.infrastructure.warehouse"]
```

## Rules

See [RULES.md](RULES.md) for a complete catalog of enforced rules and "Clean Fix" examples.

## Contributing

1.  Fork the repo.
2.  Install dependencies: `make install`.
3.  Run tests: `make test`.
4.  Submit a PR.
