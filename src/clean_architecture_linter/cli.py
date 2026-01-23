"""CLI entry points for Excelsior."""

import argparse
import sys
import json
from pathlib import Path
from typing import TYPE_CHECKING, List, Dict, Any, Optional, cast

# JUSTIFICATION: CLI is the Composition Root and must wire up Infrastructure to Interface.
from clean_architecture_linter.di.container import ExcelsiorContainer
# JUSTIFICATION: CLI is the Composition Root and must wire up Infrastructure to Interface.
from clean_architecture_linter.infrastructure.adapters.linter_adapters import (
    ExcelsiorAdapter,
    MypyAdapter,
    ImportLinterAdapter,
)
from stellar_ui_kit import ColumnDefinition, ReportSchema, TerminalReporter
from clean_architecture_linter.config import ConfigurationLoader

if TYPE_CHECKING:
    from stellar_ui_kit import TelemetryPort
    from clean_architecture_linter.domain.entities import LinterResult

BANNER = r"""
    _______  ________________   _____ ________  ____
   / ____/ |/ / ____/ ____/ /  / ___//  _/ __ \/ __ \   [ v2 ]
  / __/  |   / /   / __/ / /   \__ \ / // / / / /_/ /   Architectural Autopilot
 / /___ /   / /___/ /___/ /______/ // // /_/ / _, _/
/_____//_/|_\____/_____/_____/____/___/\____/_/ |_|
"""

AGENT_INSTRUCTIONS_TEMPLATE = """# Architecture Instructions

This project adheres to **Clean Architecture** principles enforced by the `pylint-clean-architecture` plugin.

## Layer Boundaries

The project is structured into strict layers.
Inner layers ({domain_layer}, {use_case_layer}) **MUST NOT** import from Outer layers ({infrastructure_layer}, {interface_layer}).

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
    *   **Dependency Injection**: Infrastructure components (Repositories, Clients) MUST be injected via constructor using Domain Protocols.
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

PRE_FLIGHT_WORKFLOW_TEMPLATE = """# Stellar Pre-Flight Checklist
You MUST complete this checklist for EVERY file changed before proceeding.

1.  **Handshake**: `make handshake` (Confirming compliance).
2.  **Audit**: `make verify-file FILE=<file_path>`.
3.  **Complexity**: Ruff C901 score must be <= 11.
4.  **Coverage**: Minimum 85% coverage on new logic.
5.  **Integrity**: Mypy --strict must return 0 errors.
6.  **Self-Audit**: Pylint score MUST be 10.0/10.
"""

HANDSHAKE_SNIPPET = """
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

def check_command(telemetry: "TelemetryPort", target_path: str) -> None:
    """Run standardized linter audit with grouped counts and desc sorting."""

    telemetry.step(f"Starting Excelsior Audit for: {target_path}")

    # 1. Run Mypy
    telemetry.step("Gathering Type Integrity violations (Source: Mypy)...")
    mypy_adapter = MypyAdapter()
    mypy_results = mypy_adapter.gather_results(target_path)

    # 2. Run Excelsior
    telemetry.step("Gathering Architectural violations (Source: Pylint/Excelsior)...")
    excelsior_adapter = ExcelsiorAdapter()
    excelsior_results = excelsior_adapter.gather_results(target_path)

    # 3. Run Import Linter
    telemetry.step("Verifying Package Contracts (Source: Import-Linter)...")
    il_adapter = ImportLinterAdapter()
    il_results = il_adapter.gather_results(target_path)

    reporter = TerminalReporter()

    def process_results(results: List["LinterResult"]) -> List[Dict[str, object]]:
        processed = []
        for r in results:
            d: Dict[str, object] = dict(r.to_dict())
            d["count"] = len(r.locations) if r.locations else 1
            processed.append(d)
        return sorted(processed, key=lambda x: int(x["count"]) if isinstance(x["count"], int) else 0, reverse=True)

    # Table 1: Type Integrity
    mypy_schema = ReportSchema(
        title="[MYPY] Type Integrity Audit",
        columns=[
            ColumnDefinition(header="Error Code", key="code", style="#00EEFF"),
            ColumnDefinition(header="Count", key="count", style="bold #007BFF"),
            ColumnDefinition(header="Message", key="message"),
        ],
        header_style="bold #007BFF",
    )
    if mypy_results:
        reporter.generate_report(process_results(mypy_results), mypy_schema)
    else:
        print("\n✅ No Type Integrity violations detected.")

    # Table 2: Architectural Governance
    excelsior_schema = ReportSchema(
        title="[EXCELSIOR] Architectural Governance Audit",
        columns=[
            ColumnDefinition(header="Rule ID", key="code", style="#C41E3A"),
            ColumnDefinition(header="Count", key="count", style="bold #007BFF"),
            ColumnDefinition(header="Violation Description", key="message"),
        ],
        header_style="bold #F9A602",
    )
    if excelsior_results:
        reporter.generate_report(process_results(excelsior_results), excelsior_schema)
    else:
        print("\n✅ No Architectural violations detected.")

    # Table 3: Package Contracts
    il_schema = ReportSchema(
        title="[IMPORT-LINTER] Package Boundary Audit",
        columns=[
            ColumnDefinition(header="Rule ID", key="code", style="#7B68EE"),
            ColumnDefinition(header="Contract Violation", key="message"),
        ],
        header_style="bold #7B68EE",
    )
    if il_results:
        reporter.generate_report([r.to_dict() for r in il_results], il_schema)

    # 4. Save Audit Trail
    _save_audit_trail(telemetry, mypy_results, excelsior_results, il_results)

    # AI Handover
    telemetry.step("AI Agent Handover initialized.")
    print("\n" + "=" * 40)
    print("🤖 EXCELSIOR v2: AI HANDOVER")
    print("=" * 40)
    print("System Integrity Report completed.")
    print("Audit Log: .excelsior/last_audit.json")
    print("Run 'excelsior fix' to resolve common issues.")
    print("=" * 40 + "\n")

def _save_audit_trail(telemetry: "TelemetryPort", mypy: List["LinterResult"], excelsior: List["LinterResult"], il: List["LinterResult"]) -> None:
    """Save results to .excelsior directory for human/AI review."""
    excelsior_dir = Path(".excelsior")
    excelsior_dir.mkdir(exist_ok=True)

    audit_data = {
        "version": "2.0.0",
        "timestamp": str(Path(".excelsior").stat().st_mtime), # rough timestamp
        "summary": {
            "type_integrity": len(mypy),
            "architectural": len(excelsior),
            "contracts": len(il)
        },
        "violations": {
            "type_integrity": [r.to_dict() for r in mypy],
            "architectural": [r.to_dict() for r in excelsior],
            "contracts": [r.to_dict() for r in il]
        }
    }

    json_path = excelsior_dir / "last_audit.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(audit_data, f, indent=2)

    # Human readable summary
    txt_path = excelsior_dir / "last_audit.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("=== EXCELSIOR v2 AUDIT LOG ===\n")
        f.write(f"Summary: {len(excelsior)} Architectural, {len(mypy)} Type Integrity, {len(il)} Contracts\n\n")
        f.write("--- ARCHITECTURAL VIOLATIONS ---\n")
        for r in excelsior:
            f.write(f"[{r.code}] {r.message}\n")
            if r.locations:
                for loc in r.locations:
                    f.write(f"  - {loc}\n")
        f.write("\n--- TYPE INTEGRITY VIOLATIONS ---\n")
        for r in mypy:
            f.write(f"[{r.code}] {r.message}\n")
            if r.locations:
                for loc in r.locations:
                    f.write(f"  - {loc}\n")

    telemetry.step(f"💾 Audit Trail persisted to: {json_path} and {txt_path}")

def init_command(telemetry: "TelemetryPort") -> None:
    """Initialize Excelsior configuration."""
    # Custom help with banner
    parser = argparse.ArgumentParser(
        description=f"{BANNER}\nEXCELSIOR: Clean Architecture Governance.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    # JUSTIFICATION: Simple argparse configuration.
    parser.add_argument(
        "--template",
        choices=["fastapi", "sqlalchemy"],
        help="Pre-configure for specific frameworks.",
    )
    # JUSTIFICATION: Simple argparse configuration.
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

    # Pre-Flight Workflow
    pre_flight_file = agent_dir / "pre-flight.md"
    with pre_flight_file.open("w", encoding="utf-8") as f:
        f.write(PRE_FLIGHT_WORKFLOW_TEMPLATE)
    telemetry.step(f"Generated: {pre_flight_file}")

    # Makefile Handshake Injection
    _update_makefile(telemetry)

    # Onboarding Artifact
    onboarding_file = Path("ARCHITECTURE_ONBOARDING.md")
    if not onboarding_file.exists():
        # JUSTIFICATION: Simple file write for onboarding documentation.
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

def _update_makefile(telemetry: "TelemetryPort") -> None:
    """Inject Stellar Handshake targets into Makefile."""
    makefile_path = Path("Makefile")
    content = ""
    if makefile_path.exists():
        # JUSTIFICATION: Simple file read for Makefile check.
        with makefile_path.open("r", encoding="utf-8") as f:
            content = f.read()

    if "handshake:" in content:
        telemetry.step("Makefile already contains handshake protocol.")
        return

    # JUSTIFICATION: Simple file append for Makefile injection.
    with makefile_path.open("a", encoding="utf-8") as f:
        f.write(HANDSHAKE_SNIPPET)
    telemetry.step("Injected Stellar Handshake Protocol into Makefile.")

def _check_layers(telemetry: "TelemetryPort") -> None:
    """Verify and print active layers."""
    config = ConfigurationLoader().config
    layer_map = config.get("layer_map", {})

    telemetry.step("Active Layer Configuration:")
    if not isinstance(layer_map, dict) or not layer_map:
        telemetry.error("No layer_map found in pyproject.toml [tool.clean-arch].")
        return

    # JUSTIFICATION: Simple dictionary iteration for display mapping.
    for pattern, layer in layer_map.items():
        telemetry.step(f"  {pattern} -> {layer}")

def _generate_instructions(telemetry: "TelemetryPort", path: Path) -> None:
    config = ConfigurationLoader().config
    layer_map = config.get("layer_map", {})

    display_names = {
        "Domain": "Domain",
        "UseCase": "UseCase",
        "Infrastructure": "Infrastructure",
        "Interface": "Interface",
    }

    if isinstance(layer_map, dict):
        # JUSTIFICATION: Simple dictionary iteration for display mapping.
        for directory, layer in layer_map.items():
            if not isinstance(layer, str) or not isinstance(directory, str):
                continue
            # JUSTIFICATION: Simple string check for valid directory names.
            cleaned_directory: str = directory.replace("_", "")
            if layer in display_names and cleaned_directory.isalnum():
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
    if not data or not isinstance(data, dict):
        return

    # JUSTIFICATION: Simple dictionary access for tool section.
    tool_section = data.get("tool", {})
    if not isinstance(tool_section, dict):
        return

    style_tools = {"ruff", "black", "flake8"}
    # JUSTIFICATION: Simple dictionary keys access.
    found_tools = style_tools.intersection(tool_section.keys())

    # Detect if we need to update configuration
    # JUSTIFICATION: Dictionary copy for manipulation.
    new_data = data.copy()
    # JUSTIFICATION: Scaffolding requires direct dictionary manipulation.
    new_tool = cast(dict[str, object], new_data.setdefault("tool", {}))
    if "clean-arch" not in new_tool:
        new_tool["clean-arch"] = {}

    # Template Logic
    if template:
        _apply_template_updates(new_data, template)
        telemetry.step(f"Applied template updates for: {template}")

    # Architecture-Only Mode
    if found_tools:
        _print_architecture_only_mode_advice(telemetry, found_tools)

    if template:
        print(f"\n[TEMPLATE CONFIG] Add the following to [tool.clean-arch] for {template}:")
        # JUSTIFICATION: Simple dictionary access for template config display.
        clean_arch_section_raw = cast(dict[str, object], new_data["tool"]).get("clean-arch")
        clean_arch_section = cast(dict[str, object], clean_arch_section_raw)
        print(json.dumps(clean_arch_section, indent=2))

def _load_pyproject(path: Path) -> dict[str, object] | None:
    """Load and parse pyproject.toml."""
    try:
        # JUSTIFICATION: Optional dependency lazy load
        if sys.version_info >= (3, 11):
            import tomllib as toml_lib
        else:
            try:
                import tomli as toml_lib  # type: ignore[import-not-found]
            except ImportError:
                return None

        with path.open("rb") as f:
            return cast(dict[str, object], toml_lib.load(f))
    except (OSError, ValueError) as e:
        print(f"Warning: Could not parse pyproject.toml: {e}")
    return None

def _apply_template_updates(data: dict[str, object], template: str) -> None:
    """Apply template-specific updates to the config dict."""
    # JUSTIFICATION: Scaffolding requires direct dictionary manipulation.
    tool_section = data.get("tool", {})
    if not isinstance(tool_section, dict):
        return
    # JUSTIFICATION: Scaffolding requires direct dictionary manipulation.
    clean_arch = tool_section.get("clean-arch")
    if not isinstance(clean_arch, dict):
        return

    if template == "fastapi":
        # JUSTIFICATION: Nested configuration access is permitted in CLI scaffolding.
        layer_map = cast(dict[str, str], clean_arch.setdefault("layer_map", {}))
        # JUSTIFICATION: Simple dictionary update in CLI config.
        layer_map.update({"routers": "Interface", "services": "UseCase", "schemas": "Interface"})
    elif template == "sqlalchemy":
        # JUSTIFICATION: Nested configuration access is permitted in CLI scaffolding.
        layer_map = cast(dict[str, str], clean_arch.setdefault("layer_map", {}))
        # JUSTIFICATION: Simple dictionary update in CLI config.
        layer_map.update({"models": "Infrastructure", "repositories": "Infrastructure"})
        # JUSTIFICATION: CLI configuration updates are inherently procedural.
        base_class_map = cast(dict[str, str], clean_arch.setdefault("base_class_map", {}))
        # JUSTIFICATION: Simple dictionary update in CLI config.
        base_class_map.update({"Base": "Infrastructure", "DeclarativeBase": "Infrastructure"})

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

def main() -> None:
    """Main entry point."""
    container = ExcelsiorContainer()
    # JUSTIFICATION: Bootstrapping the DI container requires direct access.
    # casting to Any to avoid circular import at runtime, relying on TYPE_CHECKING
    telemetry: "TelemetryPort" = container.get("TelemetryPort")

    parser = argparse.ArgumentParser(
        description=f"{BANNER}\nEXCELSIOR v2: Architectural Autopilot for Clean Architecture.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Check
    check_parser = subparsers.add_parser("check", help="Run multi-tool audit")
    check_parser.add_argument("path", nargs="?", default=".", help="Target path to audit")

    # Fix
    fix_parser = subparsers.add_parser("fix", help="Auto-fix common violations")
    fix_parser.add_argument("path", nargs="?", default=".", help="Target path to fix")

    # Init
    subparsers.add_parser("init", help="Initialize configuration")

    args = parser.parse_args()

    if args.command == "check":
        if "-h" not in sys.argv and "--help" not in sys.argv:
            telemetry.handshake()
        check_command(telemetry, args.path)
    elif args.command == "fix":
        from clean_architecture_linter.fixer import excelsior_fix
        if "-h" not in sys.argv and "--help" not in sys.argv:
            telemetry.handshake()
        excelsior_fix(telemetry, args.path)
    elif args.command == "init":
        if "-h" not in sys.argv and "--help" not in sys.argv:
            telemetry.handshake()
        init_command(telemetry)
    elif args.command is None:
        parser.print_help()

if __name__ == "__main__":
    main()
