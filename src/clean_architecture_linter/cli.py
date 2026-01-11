"""CLI entry points for pylint-clean-architecture."""

import argparse
from pathlib import Path

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


def init_command() -> None:
    """Implement clean-arch-init command."""
    parser = argparse.ArgumentParser(description="Initialize Clean Architecture guidelines.")
    parser.add_argument(
        "--template",
        choices=["fastapi", "sqlalchemy"],
        help="Pre-configure for specific frameworks.",
    )
    args = parser.parse_args()

    agent_dir = Path(".agent")
    if not agent_dir.exists():
        agent_dir.mkdir()
        print(f"Created directory: {agent_dir}")

    # Instructions handling (existing)
    instructions_file = agent_dir / "instructions.md"
    _generate_instructions(instructions_file)

    # Onboarding Artifact
    onboarding_file = Path("ARCHITECTURE_ONBOARDING.md")
    if not onboarding_file.exists():
        with open(onboarding_file, "w", encoding="utf-8") as f:
            f.write(ONBOARDING_TEMPLATE)
        print(f"Generated: {onboarding_file}")

    # Tool Audit & Smart Config
    _perform_tool_audit(args.template)

    # AI Handover
    print("\n" + "=" * 40)
    print("🤖 AI AGENT HANDOVER")
    print("=" * 40)
    print(
        "Please read 'ARCHITECTURE_ONBOARDING.md' and '.agent/instructions.md' "
        "to understand the architectural rules and refactoring plan."
    )
    print("=" * 40 + "\n")


def _generate_instructions(path: Path) -> None:
    # (Reuse existing logic or improved version)
    # Re-implementing logic to ensure consistency with imports if we move things around
    # JUSTIFICATION: Lazy load to avoid circular import
    from clean_architecture_linter.config import (  # pylint: disable=import-outside-toplevel
        ConfigurationLoader,
    )

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

    with open(path, "w", encoding="utf-8") as f:
        f.write(
            AGENT_INSTRUCTIONS_TEMPLATE.format(
                domain_layer=display_names["Domain"],
                use_case_layer=display_names["UseCase"],
                infrastructure_layer=display_names["Infrastructure"],
                interface_layer=display_names["Interface"],
            )
        )
    print(f"Generated: {path}")


def _perform_tool_audit(template: str = None) -> None:
    """Scan for other tools and configure Mode."""
    # original_sys_path = sys.path.copy() # Unused
    pyproject_path = Path("pyproject.toml")
    if not pyproject_path.exists():
        return

    try:
        # JUSTIFICATION: Optional dependency lazy load
        import tomli  # type: ignore # pylint: disable=import-outside-toplevel

        with open(pyproject_path, "rb") as f:
            data = tomli.load(f)
    except ImportError:
        # Fallback or strict error
        print("Warning: tomli not installed, cannot parse pyproject.toml fully.")
        return
    except (OSError, ValueError) as e:  # Catch specific exceptions
        print(f"Warning: Could not parse pyproject.toml: {e}")
        return

    tool_section = data.get("tool", {})
    style_tools = {"ruff", "black", "flake8"}
    found_tools = style_tools.intersection(tool_section.keys())

    # Detect if we need to update configuration
    updates_needed = False
    new_data = data.copy()

    if "clean-arch" not in new_data["tool"]:
        new_data["tool"]["clean-arch"] = {}
        updates_needed = True

    # Template Logic
    if template:
        updates_needed = True
        if template == "fastapi":
            new_data["tool"]["clean-arch"].setdefault("layer_map", {}).update(
                {"routers": "Interface", "services": "UseCase", "schemas": "Interface"}
            )
        elif template == "sqlalchemy":
            new_data["tool"]["clean-arch"].setdefault("layer_map", {}).update(
                {"models": "Infrastructure", "repositories": "Infrastructure"}
            )
            new_data["tool"]["clean-arch"].setdefault("base_class_map", {}).update(
                {"Base": "Infrastructure", "DeclarativeBase": "Infrastructure"}
            )

    # Architecture-Only Mode
    if found_tools:
        print(f"Detected style tools: {', '.join(found_tools)}. Enabling Architecture-Only Mode.")
        if "pylint" not in new_data["tool"]:
            new_data["tool"]["pylint"] = {}
        if "messages_control" not in new_data["tool"]["pylint"]:
            new_data["tool"]["pylint"]["messages_control"] = {}

        # We will just print instructions for now to avoid destroying user's toml formatting.
        print("\n[RECOMMENDED ACTION] Add this to pyproject.toml to disable conflicting style checks:")
        print(
            """
[tool.pylint.messages_control]
disable = "all"
enable = ["clean-arch-classes", "clean-arch-imports", "clean-arch-layers"] # and other specific checks
        """
        )

    if updates_needed and template:
        # Here we just print because we don't have a reliable TOML writer in standard lib or common deps guaranteed
        # Here we just print because we don't have a reliable TOML writer in standard lib or common deps guaranteed
        print(f"\n[TEMPLATE CONFIG] Add the following to [tool.clean-arch] for {template}:")
        # JUSTIFICATION: Lazy load used only for output formatting
        import json  # pylint: disable=import-outside-toplevel

        print(json.dumps(new_data["tool"]["clean-arch"], indent=2))


def main():
    """Main entry point."""
    init_command()
