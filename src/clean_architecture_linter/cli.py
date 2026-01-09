"""CLI entry points for pylint-clean-architecture."""

import argparse
import sys
from pathlib import Path


AGENT_INSTRUCTIONS_TEMPLATE = """# Architecture Instructions

This project adheres to **Clean Architecture** principles enforced by the `pylint-clean-architecture` plugin.

## Layer Boundaries

The project is structured into strict layers.
Inner layers (Domain, UseCase) **MUST NOT** import from Outer layers (Infrastructure, Interface).

### 1. Domain Layer
*   **Purpose**: Contains pure business logic, entities, and protocols (interfaces).
*   **Rules**:
    *   **NO** I/O operations (DB, API, Filesystem).
    *   **NO** direct dependencies on frameworks or libraries (unless they are pure utilities).
    *   **Must be pure Python.**
    *   Use `@dataclass(frozen=True)` for Entities and Value Objects.

### 2. UseCase Layer (Application Logic)
*   **Purpose**: Orchestrates the flow of data between Domain Objects and Interfaces/Infrastructure.
*   **Rules**:
    *   **No Infrastructure-specific drivers or raw I/O** (e.g. no `requests`, no `sqlalchemy.session`, no `snowflake.connector`).
    *   **Dependency Injection**: Infrastructure components (Repositories, Clients) MUST be injected via constructor using Domain Protocols.
    *   **Law of Demeter**: Objects should not reach through dependencies (e.g. avoid `obj.child.method()`).

### 3. Interface Layer (Controllers/CLI)
*   **Purpose**: Handles external input (HTTP requests, CLI commands) and calls UseCases.
*   **Rules**:
    *   Convert external data (JSON, Args) into Domain objects before passing to UseCases.

### 4. Infrastructure Layer (Gateways/Repositories)
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


def init_command() -> None:
    """Implement clean-arch-init command."""
    parser = argparse.ArgumentParser(
        description="Initialize Clean Architecture guidelines."
    )
    parser.parse_args()

    agent_dir = Path(".agent")
    if not agent_dir.exists():
        agent_dir.mkdir()
        print(f"Created directory: {agent_dir}")

    instructions_file = agent_dir / "instructions.md"

    # We could theoretically inject project specific config into the template here
    # checking config loader, but the template is quite generic as requested.
    # config = ConfigurationLoader().config

    # Write the instructions
    with open(instructions_file, "w", encoding="utf-8") as f:
        f.write(AGENT_INSTRUCTIONS_TEMPLATE)

    print(f"Generated: {instructions_file}")
    print("Add this file to your AI coding assistant's context for better compliance.")


def main():
    """Main entry point."""
    if len(sys.argv) > 1 and sys.argv[1] == "init":
        # Hacky dispatch for now, or just register clean-arch-init directly
        init_command()
    else:
        print("Usage: clean-arch-init")
