# Architecture Instructions

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
    *   **No Infrastructure-specific drivers or raw I/O**.
    *   **Dependency Injection**: Infrastructure components MUST be injected via constructor using Domain Protocols.

### 3. Interface Layer (Controllers/CLI)
*   **Purpose**: Handles external input and calls UseCases.

### 4. Infrastructure Layer (Gateways/Repositories)
*   **Purpose**: Implements Domain Protocols to interact with the outside world.

## Design Rules

*   **Justify Bypasses**: If you must disable a linter rule, add a `# JUSTIFICATION: ...` comment.
*   **Law of Demeter**:
    *   Prefer Type Hints for LoD compliance.
    *   Chaining is permitted on methods returning primitives or members of allowed modules (e.g. `pathlib`).
    *   Avoid manual method-name overrides in configuration unless absolutely necessary.
*   **Discovery over Hardcoding**:
    *   **Never manually map method names to types.** Always use AST discovery or type hints to propagate types through a chain.

## Helper Command

To check compliance, run:
`pylint src/`

## External Dependencies (Fleet Kit)

*   This project utilizes shared components from @[stellar-ui-kit].
*   **Read-Only**: Any file with a `# FLEET SYNC` header must be treated as READ-ONLY within this package.
*   **Modifications**: All updates to these components MUST be performed in the kit source, not here.
*   **Coverage**: These files are excluded from local coverage reports to ensure we only measure project-specific health.
