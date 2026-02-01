"""
Stellar Engineering Command: Visual Telemetry Constants
"""

# EXCELSIOR: ANSI Red (\033[31m)
_RED: str = "\033[31m"
_RESET: str = "\033[0m"
_EXCELSIOR_ART: str = r"""
    _______  ________________   _____ ________  ____
   / ____/ |/ / ____/ ____/ /  / ___//  _/ __ \/ __ \   [ v2 ]
  / __/  |   / /   / __/ / /   \__ \ / // / / / /_/ /   Architectural Autopilot
 / /___ /   / /___/ /___/ /______/ // // /_/ / _, _/
/_____//_/|_\____/_____/_____/____/___/\____/_/ |_|
"""
EXCELSIOR_BANNER = _RED + _EXCELSIOR_ART + _RESET


DEFAULT_INTERNAL_MODULES: frozenset[str] = frozenset(
    {
        "domain",
        "dto",
        "use_cases",
        "protocols",
        "models",
        "telemetry",
        "results",
        "entities",
        "policies",
        "interfaces",
        "exceptions",
        "types",
        "layer_registry",
        "config",
        "gateways",
    }
)

# Ruff rule selectors for gated audit (used by CheckAuditUseCase)
RUFF_IMPORT_TYPING_SELECT: list[str] = ["I", "UP", "B"]  # isort, pyupgrade, bugbear
RUFF_CODE_QUALITY_SELECT: list[str] = [
    "E", "F", "W", "C90", "N", "PL", "PT", "A", "C4", "SIM", "ARG", "PTH", "RUF",
]

BUILTIN_TYPE_MAP: dict[str, str] = {
    "str": "builtins.str",
    "int": "builtins.int",
    "float": "builtins.float",
    "bool": "builtins.bool",
    "bytes": "builtins.bytes",
    "list": "builtins.list",
    "dict": "builtins.dict",
    "tuple": "builtins.tuple",
    "set": "builtins.set",
    "Optional": "builtins.Optional",
    "Union": "builtins.Union",
    "List": "builtins.list",
    "Dict": "builtins.dict",
    "Set": "builtins.set",
}

AGENT_INSTRUCTIONS_TEMPLATE: str = """# Architecture Instructions

This project adheres to **Clean Architecture** principles enforced by the `pylint-clean-architecture` plugin.

## Layer Boundaries

The project is structured into strict layers.
Inner layers ({domain_layer}, {use_case_layer}) **MUST NOT** import from Outer layers
({infrastructure_layer}, {interface_layer}).

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
    *   **Dependency Injection**: Infrastructure components (Repositories, Clients)
        MUST be injected via constructor using Domain Protocols.
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
"""

ONBOARDING_TEMPLATE: str = """# Architecture Onboarding Strategy

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

PRE_FLIGHT_WORKFLOW_TEMPLATE: str = """# Stellar Pre-Flight Checklist
You MUST complete this checklist for EVERY file changed before proceeding.

1.  **Handshake**: `make handshake` (Confirming compliance).
2.  **Audit**: `make verify-file FILE=<file_path>`.
3.  **Complexity**: Ruff C901 score must be <= 11.
4.  **Coverage**: Minimum 85% coverage on new logic.
5.  **Integrity**: Mypy --strict must return 0 errors.
6.  **Self-Audit**: Pylint score MUST be 10.0/10.
"""

HANDSHAKE_SNIPPET: str = """
# --- Agent Handshake Protocol ---
.PHONY: handshake
handshake:
	@echo "=== STELLAR PROTOCOL HANDSHAKE ==="
	@echo "1. READING REQUIREMENTS..."
	@ls .agent/*.md | grep -v "_" || (echo "ERROR: Files in .agent/ must use dashes, not underscores!" && exit 1)
	@echo "   [OK] .agent/ files verified."
	@echo ""
	@echo "2. ARCHITECTURAL BOUNDARIES:"
	@echo "   - Complexity Limit: 11 (Ruff C901)"
	@echo "   - Typing Policy: Strict (W9016 - Banned Any)"
	@echo "   - Helpers: BANNED. Use Infrastructure Gateways."
	@echo "   - UI Kit: stellar-ui-kit is IMMUTABLE."
	@echo ""
	@echo "3. TDD MANDATE (MUST FOLLOW IN ORDER):"
	@echo "   A. Identify target files and logic."
	@echo "   B. Create STUBS for new logic."
	@echo "   C. Draft Acceptance Criteria & Tests in tests/benchmarks/lod-samples.py."
	@echo "   D. STOP: Wait for User Approval of the Blueprint."
	@echo ""
	@echo "4. VERIFICATION GATE:"
	@echo "   - After approval: Write Tests -> Verify Failure -> Implementation -> 'make verify-file'"
	@echo "   - Requirement: 85% coverage + 10.0/10 Lint + 0 Mypy errors."
	@echo "=================================="

.PHONY: verify-file
verify-file:
	@echo "Auditing $(FILE)..."
	ruff check $(FILE) --select C901 --max-complexity 11
	mypy $(FILE) --strict
	PYTHONPATH=src pylint $(FILE) --fail-under=10.0
	pytest --cov=src --cov-report=term-missing | grep $(FILE)
"""
