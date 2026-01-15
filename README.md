<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/hero-dark.png">
  <source media="(prefers-color-scheme: light)" srcset="assets/hero-light.png">
  <img alt="Stellar Engineering Command Banner" src="assets/hero-light.png" width="100%">
</picture>

![PyPI](https://img.shields.io/pypi/v/pylint-clean-architecture?color=C41E3A&labelColor=333333)
![Build Status](https://img.shields.io/github/actions/workflow/status/noah-goodrich/pylint-clean-architecture/ci.yml?branch=main&color=007BFF&labelColor=333333&label=Build%20Status)
![Python Versions](https://img.shields.io/pypi/pyversions/pylint-clean-architecture?color=F9A602&labelColor=333333)
![License](https://img.shields.io/github/license/noah-goodrich/pylint-clean-architecture?color=F9A602&labelColor=333333)

![PyPI](https://img.shields.io/pypi/v/pylint-clean-architecture?color=C41E3A&labelColor=333333)
![Build Status](https://img.shields.io/github/actions/workflow/status/noah-goodrich/pylint-clean-architecture/ci.yml?branch=main&color=007BFF&labelColor=333333&label=Build%20Status)
![Python Versions](https://img.shields.io/pypi/pyversions/pylint-clean-architecture?color=F9A602&labelColor=333333)
![License](https://img.shields.io/github/license/noah-goodrich/pylint-clean-architecture?color=F9A602&labelColor=333333)

Captain's Log: High-authority Pylint module for enforcing **Prime Directives** (Clean Architecture) and preventing **Hull Integrity Breaches** (Technical Debt) in Python projects.

Enforcing architectural boundaries, dependency rules, and design patterns to ensure the fleet remains operational and modular.

## Features

*   **Layer Boundary Enforcement**: Ensures Prime Directives are maintained between Domain, UseCase, and Infrastructure.
*   **Dependency Injection Checks**: Forbids unauthorized instantiation of infrastructure modules within UseCases.
*   **Design Pattern Enforcement**: Detects "naked returns" and other architectural anomalies.
*   **Law of Demeter**: Prevents tight coupling through deep method chains.
*   **Contract Integrity**: Verifies that Infrastructure implements Domain Protocols correctly.
*   **Anti-Bypass Guard**: Prevents "lazy" disabling of Prime Directives without high-level authorization (Justification).

## Docking Procedures

```bash
pip install pylint-clean-architecture
```

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

### AI Coding Assistant Support

The `clean-arch-init` command generates architectural instructions for AI agents (like Cursor or GitHub Copilot) to prevent "Split Brain" issues by teaching the AI your project's rules before it writes code.

Usage:

```bash
clean-arch-init
```

Outcome: This creates a customized `.agent/instructions.md` file based on the layer names defined in the project's `Console Calibration`.


## Console Calibration

The module is calibrated via `[tool.clean-arch]` in `pyproject.toml`.

```toml
[tool.clean-arch]
# 1. Project Type Presets (generic, cli_app, fastapi_sqlalchemy)
project_type = "generic"

# 2. Strict Visibility Enforcement
visibility_enforcement = true

# 3. Custom Layer Mapping (Map directory regex patterns to layers)
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
