# Architecture Instructions

This project adheres to **Clean Architecture** principles enforced by the `excelsior-architect` plugin.

## Layer Boundaries

The project is structured into strict layers.
Inner layers (Domain, UseCase) **MUST NOT** import from Outer layers
(Infrastructure, Interface).

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
    *   **No Infrastructure-specific drivers or raw I/O** (e.g. no `requests`, no `sqlalchemy.session`).
    *   **Dependency Injection**: Infrastructure components (Repositories, Clients)
        MUST be injected via constructor using Domain Protocols.
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
    *   *Prefer Type Hints for LoD compliance.*
    *   *Chaining is permitted on methods returning primitives or members of allowed_lod_modules.*
    *   *Avoid manual method-name overrides in configuration unless absolutely necessary.*
*   **Justify Bypasses**: If you must disable a linter rule, add a `# JUSTIFICATION: ...` comment.

## Helper Command

To check compliance, run: `excelsior check` or `pylint src/`
