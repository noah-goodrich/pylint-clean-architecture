"""CLI entry points for pylint-clean-architecture."""

import argparse
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from clean_architecture_linter.config import ConfigurationLoader
from clean_architecture_linter.di.container import ExcelsiorContainer

if TYPE_CHECKING:
    from clean_architecture_linter.interface.telemetry import TelemetryPort

AGENT_INSTRUCTIONS_TEMPLATE = (
    """# Architecture Instructions

This project adheres to **Clean Architecture** principles enforced by the `pylint-clean-architecture` plugin.

## Layer Boundaries

The project is structured into strict layers.
Inner layers ({domain_layer}, {use_case_layer}) **MUST NOT** import from """
    """Outer layers ({infrastructure_layer}, {interface_layer}).

### 1. {domain_layer} Layer
*   **Purpose**: Contains pure business logic, entities, and protocols (interfaces).
*   **Rules**:
    *   **NO** I/O operations (DB, API, Filesystem).
    *   **NO** direct dependencies on frameworks or libraries (unless they are pure utilities).
    *   **Must be pure Python.**
    *   Use `@dataclass(frozen=True)` for Entities and Value Objects.

### 2. {use_case_layer} Layer (Application Logic)
*   **Purpose**: Orchestrates the flow of data between Domain Objects and Interfaces/Infrastructure.
*   **Rules**:
    *   **No Infrastructure-specific drivers or raw I/O** (e.g. no `requests`, no `sqlalchemy.session`).
    *   **Dependency Injection**: Infrastructure components (Repositories, Clients) """
    """MUST be injected via constructor using Domain Protocols."""
    """
    *   **Law of Demeter**: Objects should not reach through dependencies (e.g. avoid `obj.child.method()`).

### 3. {interface_layer} Layer (Controllers/CLI)
*   **Purpose**: Handles external input (HTTP requests, CLI commands) and calls UseCases.
*   **Rules**:
    *   Convert external data (JSON, Args) into Domain objects before passing to UseCases.

### 4. {infrastructure_layer} Layer (Gateways/Repositories)
*   **Purpose**: Implements Domain Protocols to interact with the outside world (DB, API, Storage).
*   **Rules**:
    *   Must implement a Protocol defined in the Domain layer.
    *   Should handle specific implementation details (SQL, API calls).

## Design Rules

*   **Avoid "Naked Returns"**: Repositories should return Domain Entities, not raw DB cursors or API responses.
*   **No "Stranger" Chains**: Don't chain method calls too deeply.
    *   *Prefer Type Hints for LoD compliance.*
    *   *Chaining is permitted on methods returning primitives or members of allowed_lod_modules.*
    *   *Avoid manual method-name overrides in configuration unless absolutely necessary.*
*   **Justify Bypasses**: If you must disable a linter rule, add a `# JUSTIFICATION: ...` comment.

## Helper Command

To check compliance, run:
`pylint src/`
"""
)


ONBOARDING_TEMPLATE = """# Architecture Onboarding Strategy

This project is moving towards a strict Clean Architecture.
Follow this 3-Phase Refactor Plan to achieve compliance without stopping development.

## Phase 1: Package Organization (Structure)
**Goal**: Eliminate "God Files" and "Root Soup".
- [ ] Fix W9011 (Deep Structure): Move root-level logic files into sub-packages.
- [ ] Fix W9010 (God File): Split files containing multiple heavy components or mixed layers.

## Phase 2: Layer Separation (Boundaries)
**Goal**: Enforce strict dependency rules.
- [ ] Fix W9001-9004: Ensure Domain/use_cases do not import Infrastructure.
- [ ] Introduce Dependency Injection using Protocols.

## Phase 3: Coupling Hardening (Internal Quality)
**Goal**: Reduce complexity and coupling.
- [ ] Fix W9006 (Law of Demeter): Resolve chained calls.
- [ ] Ensure all I/O is isolated in Infrastructure.

---
**Configuration Note**:
This project uses `pylint-clean-architecture` in **Architecture-Only Mode** (style checks disabled)
because other tools (ruff/black/flake8) are detected.
"""

BANNER = r"""
    _______  ________________   _____ ________  ____
   / ____/ |/ / ____/ ____/ /  / ___//  _/ __ \/ __ \
  / __/  |   / /   / __/ / /   \__ \ / // / / / /_/ /
 / /___ /   / /___/ /___/ /______/ // // /_/ / _, _/
/_____//_/|_\____/_____/_____/____/___/\____/_/ |_|
"""


def init_command(telemetry: "TelemetryPort") -> None:
    # Custom help with banner
    parser = argparse.ArgumentParser(
        description=f"{BANNER}\nEXCELSIOR: Clean Architecture Governance.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--template",
        choices=["fastapi", "sqlalchemy"],
        help="Pre-configure for specific frameworks.",
    )
    parser.add_argument(
        "--check-layers",
        action="store_true",
        help="Verify active layer configuration.",
    )

    args = parser.parse_args()

    if args.check_layers:
        _check_layers(telemetry)
        return

    agent_dir = Path(".agent")
    if not agent_dir.exists():
        agent_dir.mkdir()
        telemetry.step(f"Created directory: {agent_dir}")

    # Instructions handling (existing)
    instructions_file = agent_dir / "instructions.md"
    _generate_instructions(telemetry, instructions_file)

    # Onboarding Artifact
    onboarding_file = Path("ARCHITECTURE_ONBOARDING.md")
    if not onboarding_file.exists():
        with onboarding_file.open("w", encoding="utf-8") as f:
            f.write(ONBOARDING_TEMPLATE)
        telemetry.step(f"Generated: {onboarding_file}")

    # Tool Audit & Smart Config
    _perform_tool_audit(telemetry, args.template)

    # AI Handover
    telemetry.step("AI Agent Handover initialized.")
    print("\n" + "=" * 40)
    print("🤖 AI AGENT HANDOVER")
    print("=" * 40)
    print(
        "Please read 'ARCHITECTURE_ONBOARDING.md' and '.agent/instructions.md' "
        "to understand the architectural rules and refactoring plan."
    )
    print("Start with Phase 1 in ARCHITECTURE_ONBOARDING.md to avoid being overwhelmed.")
    print("=" * 40 + "\n")


def _check_layers(telemetry: "TelemetryPort") -> None:
    """Verify and print active layers."""

    config = ConfigurationLoader().config
    layer_map = config.get("layer_map", {})

    telemetry.step("Active Layer Configuration:")
    if not layer_map:
        telemetry.error("No layer_map found in pyproject.toml [tool.clean-arch].")
        return

    for pattern, layer in layer_map.items():
        telemetry.step(f"  {pattern} -> {layer}")


def _generate_instructions(telemetry: "TelemetryPort", path: Path) -> None:
    # (Reuse existing logic or improved version)
    # Re-implementing logic to ensure consistency with imports if we move things around

    config = ConfigurationLoader().config
    layer_map = config.get("layer_map", {})

    display_names = {
        "Domain": "Domain",
        "UseCase": "UseCase",
        "Infrastructure": "Infrastructure",
        "Interface": "Interface",
    }

    for directory, layer in layer_map.items():
        if layer in display_names and directory.replace("_", "").isalnum():
            # Capitalize for display (e.g. services -> Services)
            display_names[layer] = f"{directory.capitalize()} ({layer})"

    with path.open("w", encoding="utf-8") as f:
        f.write(
            AGENT_INSTRUCTIONS_TEMPLATE.format(
                domain_layer=display_names["Domain"],
                use_case_layer=display_names["UseCase"],
                infrastructure_layer=display_names["Infrastructure"],
                interface_layer=display_names["Interface"],
            )
        )
    telemetry.step(f"Generated: {path}")


def _perform_tool_audit(telemetry: "TelemetryPort", template: str | None = None) -> None:
    """Scan for other tools and configure Mode."""
    pyproject_path = Path("pyproject.toml")
    if not pyproject_path.exists():
        return

    data = _load_pyproject(pyproject_path)
    if not data:
        return

    tool_section = data.get("tool", {})
    style_tools = {"ruff", "black", "flake8"}
    found_tools = style_tools.intersection(tool_section.keys())

    # Detect if we need to update configuration
    new_data = data.copy()
    if "clean-arch" not in new_data.get("tool", {}):
        new_data.setdefault("tool", {})["clean-arch"] = {}

    # Template Logic
    if template:
        _apply_template_updates(new_data, template)
        telemetry.step(f"Applied template updates for: {template}")

    # Architecture-Only Mode
    if found_tools:
        _print_architecture_only_mode_advice(telemetry, found_tools)

    if template:
        print(f"\n[TEMPLATE CONFIG] Add the following to [tool.clean-arch] for {template}:")
        print(json.dumps(new_data["tool"]["clean-arch"], indent=2))


def _load_pyproject(path: Path) -> dict[str, object] | None:
    """Load and parse pyproject.toml."""
    try:
        # JUSTIFICATION: Optional dependency lazy load
        import tomli  # noqa: PLC0415

        with path.open("rb") as f:
            return tomli.load(f)
    except ImportError:
        print("Warning: tomli not installed, cannot parse pyproject.toml fully.")
    except (OSError, ValueError) as e:
        print(f"Warning: Could not parse pyproject.toml: {e}")
    return None


def _apply_template_updates(data: dict[str, object], template: str) -> None:
    """Apply template-specific updates to the config dict."""
    clean_arch = data["tool"]["clean-arch"]
    if template == "fastapi":
        clean_arch.setdefault("layer_map", {}).update(
            {"routers": "Interface", "services": "UseCase", "schemas": "Interface"}
        )
    elif template == "sqlalchemy":
        clean_arch.setdefault("layer_map", {}).update({"models": "Infrastructure", "repositories": "Infrastructure"})
        clean_arch.setdefault("base_class_map", {}).update(
            {"Base": "Infrastructure", "DeclarativeBase": "Infrastructure"}
        )


def _print_architecture_only_mode_advice(telemetry: "TelemetryPort", found_tools: set[str]) -> None:
    """Print advice for Architecture-Only Mode."""
    telemetry.step(f"Detected style tools: {', '.join(found_tools)}. Enabling Architecture-Only Mode.")
    print("\n[RECOMMENDED ACTION] Add this to pyproject.toml to disable conflicting style checks:")
    print(
        """
[tool.pylint.messages_control]
disable = "all"
enable = ["clean-arch-classes", "clean-arch-imports", "clean-arch-layers"] # and other specific checks
        """
    )


def main():
    """Main entry point."""

    container = ExcelsiorContainer()
    telemetry = container.get("TelemetryPort")

    if "-h" not in sys.argv and "--help" not in sys.argv:
        telemetry.handshake()

    init_command(telemetry)


if __name__ == "__main__":
    main()
