"""CLI entry points for Excelsior - Thin Controller using Typer."""

import sys
from pathlib import Path
from typing import Optional

import typer

from clean_architecture_linter.domain.config import ConfigurationLoader
from clean_architecture_linter.domain.constants import EXCELSIOR_BANNER
from clean_architecture_linter.infrastructure.di.container import ExcelsiorContainer
from clean_architecture_linter.infrastructure.gateways.libcst_fixer_gateway import (
    LibCSTFixerGateway,
)
from clean_architecture_linter.use_cases.apply_fixes import ApplyFixesUseCase
from clean_architecture_linter.use_cases.check_audit import CheckAuditUseCase
from clean_architecture_linter.use_cases.init_project import InitProjectUseCase

app = typer.Typer(
    name="excelsior",
    help=f"{EXCELSIOR_BANNER}\nExcelsior: High-Integrity Architectural Governance",
    add_completion=False,
)


def _resolve_target_path(path: Optional[Path]) -> str:
    """
    Resolve target path with default logic.

    Resolution order:
    - If an explicit non-dot path is provided, return it as-is.
    - Otherwise, if a local 'src/' directory exists, use 'src'.
    - Otherwise, default to current directory ('.').

    Args:
        path: Optional path from CLI argument

    Returns:
        Resolved path string
    """
    if path and str(path) != ".":
        return str(path)

    # Prefer src/ when present to match typical Python project layout
    cwd = Path.cwd()
    src_dir = cwd / "src"
    if src_dir.exists() and src_dir.is_dir():
        return "src"

    return "."


@app.command()
def check(
    path: Optional[Path] = typer.Argument(None, help="Path to audit (default: current directory, .)"),  # noqa: B008
    linter: str = typer.Option("all", help="Specific linter to run"),
) -> None:
    """Run the gated sequential audit (Ruff → Mypy → Excelsior)."""
    container = ExcelsiorContainer()
    telemetry = container.get("TelemetryPort")
    telemetry.handshake()

    target_path = _resolve_target_path(path)

    # Get adapters from container
    mypy_adapter = container.get("MypyAdapter")
    excelsior_adapter = container.get("ExcelsiorAdapter")
    import_linter_adapter = container.get("ImportLinterAdapter")
    ruff_adapter = container.get("RuffAdapter")
    config_loader = ConfigurationLoader()

    # Create use case
    use_case = CheckAuditUseCase(
        mypy_adapter=mypy_adapter,
        excelsior_adapter=excelsior_adapter,
        import_linter_adapter=import_linter_adapter,
        ruff_adapter=ruff_adapter,
        telemetry=telemetry,
        config_loader=config_loader,
    )

    # Execute audit (gated sequential: Ruff → Mypy → Excelsior)
    audit_result = use_case.execute(target_path)

    # Report results
    reporter = container.get("AuditReporter")
    reporter.report_audit(audit_result)

    # Save audit trail
    audit_trail_service = container.get("AuditTrailService")
    audit_trail_service.save_audit_trail(audit_result)

    # AI Handover message
    telemetry.step("AI Agent Handover initialized.")
    print("\n" + "=" * 40)
    print("🤖 EXCELSIOR v2: AI HANDOVER")
    print("=" * 40)
    print("System Integrity Report completed.")
    print("Audit Log: .excelsior/last_audit.json")
    print("Run 'excelsior fix' to resolve common issues.")
    print("=" * 40 + "\n")

    # Exit with error code if violations found
    if audit_result.has_violations():
        sys.exit(1)
    sys.exit(0)


@app.command()
def fix(
    path: Optional[Path] = typer.Argument(None, help="Path to fix (default: current directory, .)"),  # noqa: B008
    linter: str = typer.Option(
        "all", help="Which linter to fix violations for"),
    confirm: bool = typer.Option(
        False, "--confirm", help="Require confirmation before each fix"),
    no_backup: bool = typer.Option(
        False, "--no-backup", help="Skip creating .bak backup files"),
    skip_tests: bool = typer.Option(
        False, "--skip-tests", help="Skip pytest validation"),
    cleanup_backups: bool = typer.Option(
        False, "--cleanup-backups", help="Remove .bak files after successful fixes"),
    manual_only: bool = typer.Option(
        False, "--manual-only", help="Show manual fix suggestions only"),
) -> None:
    """Apply deterministic fixes and inject architectural commentary."""
    container = ExcelsiorContainer()
    telemetry = container.get("TelemetryPort")
    telemetry.handshake()

    target_path = _resolve_target_path(path)

    if manual_only:
        _run_fix_manual_only(telemetry, target_path, linter)
        return

    if linter == "ruff":
        _run_fix_ruff(telemetry, target_path)
        return

    _run_fix_excelsior(telemetry, target_path, confirm,
                       no_backup, skip_tests, cleanup_backups)


def _run_fix_manual_only(telemetry, target_path: str, linter: str) -> None:
    """Show manual fix suggestions only."""
    container = ExcelsiorContainer()

    all_adapters = [
        ("Ruff", container.get("RuffAdapter"), "ruff"),
        ("Mypy", container.get("MypyAdapter"), "excelsior"),
        ("Excelsior", container.get("ExcelsiorAdapter"), "excelsior"),
        ("Import-Linter", container.get("ImportLinterAdapter"), "excelsior"),
    ]
    if linter == "all":
        adapters = [(n, a) for n, a, _ in all_adapters]
        telemetry.step(
            "📋 Gathering manual fix suggestions from all linters...")
    elif linter == "ruff":
        adapters = [(n, a) for n, a, lt in all_adapters if lt == "ruff"]
        telemetry.step("📋 Gathering manual fix suggestions from Ruff...")
    else:
        adapters = [(n, a) for n, a, lt in all_adapters if lt == "excelsior"]
        telemetry.step(
            "📋 Gathering manual fix suggestions from Excelsior suite...")

    for linter_name, adapter in adapters:
        results = adapter.gather_results(target_path)
        if not results:
            continue
        print(f"\n{'='*60}\n{linter_name} - {len(results)} violation(s)\n{'='*60}")
        for result in results:
            fixable = (
                "✅ AUTO-FIXABLE"
                if adapter.supports_autofix() and result.code in adapter.get_fixable_rules()
                else "⚠️  MANUAL FIX REQUIRED"
            )
            print(f"\n[{result.code}] {fixable}")
            print(f"  Message: {result.message}")
            if result.locations:
                print(f"  Locations ({len(result.locations)}):")
                for loc in result.locations[:5]:
                    print(f"    - {loc}")
                if len(result.locations) > 5:
                    print(f"    ... and {len(result.locations) - 5} more")
            if not (adapter.supports_autofix() and result.code in adapter.get_fixable_rules()):
                instructions = adapter.get_manual_fix_instructions(result.code)
                print(f"  💡 How to fix: {instructions}")


def _run_fix_ruff(telemetry, target_path: str) -> None:
    """Apply Ruff fixes only."""
    container = ExcelsiorContainer()
    telemetry.step("🔧 Applying Ruff fixes...")
    ruff_adapter = container.get("RuffAdapter")
    success = ruff_adapter.apply_fixes(Path(target_path))
    telemetry.step(
        "✅ Ruff fixes complete. Run 'excelsior check' to verify." if success else "❌ Ruff fixing failed"
    )
    sys.exit(0 if success else 1)


def _run_fix_excelsior(
    telemetry,
    target_path: str,
    confirm: bool,
    no_backup: bool,
    skip_tests: bool,
    cleanup_backups: bool,
) -> None:
    """Run multi-pass fixer: Ruff → W9015 → Re-audit + Architecture."""
    container = ExcelsiorContainer()
    config_loader = ConfigurationLoader()

    # Get dependencies for multi-pass fixer
    astroid_gateway = container.get("AstroidGateway")
    ruff_adapter = container.get("RuffAdapter")
    filesystem = container.get("FileSystemGateway")

    # Create CheckAuditUseCase for Pass 3 re-audit
    mypy_adapter = container.get("MypyAdapter")
    excelsior_adapter = container.get("ExcelsiorAdapter")
    import_linter_adapter = container.get("ImportLinterAdapter")
    check_audit_use_case = CheckAuditUseCase(
        mypy_adapter=mypy_adapter,
        excelsior_adapter=excelsior_adapter,
        import_linter_adapter=import_linter_adapter,
        ruff_adapter=ruff_adapter,
        telemetry=telemetry,
        config_loader=config_loader,
    )

    # Create rules for auto-fixable violations
    from clean_architecture_linter.domain.rules.immutability import DomainImmutabilityRule
    from clean_architecture_linter.domain.rules.type_hints import MissingTypeHintRule

    w9015_rule = MissingTypeHintRule(astroid_gateway)
    w9601_rule = DomainImmutabilityRule()

    # Get all Excelsior rules that support auto-fix
    rules = [w9015_rule, w9601_rule]

    use_case = ApplyFixesUseCase(
        LibCSTFixerGateway(),
        filesystem=filesystem,
        telemetry=telemetry,
        require_confirmation=confirm,
        create_backups=not no_backup,
        cleanup_backups=cleanup_backups,
        validate_with_tests=not skip_tests,
        astroid_gateway=astroid_gateway,
        ruff_adapter=ruff_adapter,
        check_audit_use_case=check_audit_use_case,
        config_loader=config_loader,
    )
    modified = use_case.execute_multi_pass(rules, target_path)
    telemetry.step(
        f"✅ Successfully fixed {modified} file(s)" if modified > 0 else "ℹ️  No fixes applied"
    )
    sys.exit(0)


@app.command()
def ai_workflow(
    path: Optional[Path] = typer.Argument(None, help="Path to audit (default: current directory, .)"),  # noqa: B008
    max_iterations: int = typer.Option(
        5, "--max-iterations", help="Maximum fix/check cycles before stopping"
    ),
    skip_tests: bool = typer.Option(
        False, "--skip-tests", help="Skip pytest validation during fixes"
    ),
) -> None:
    """
    Unified AI workflow: auto-fix → inject comments → provide structured handover.

    This command:
    1. Runs excelsior fix (auto-fixes + governance comment injection)
    2. Re-runs excelsior check to get current state
    3. Outputs structured JSON (.excelsior/ai_handover.json) with:
       - Remaining violations grouped by rule
       - File locations with EXCELSIOR comment anchors
       - Fixability status and instructions
       - Next steps guidance
    4. Provides clear summary for AI to continue fixing

    Use this when you want to hand off to an AI agent for autonomous fixing.
    """
    container = ExcelsiorContainer()
    telemetry = container.get("TelemetryPort")
    telemetry.handshake()

    target_path = _resolve_target_path(path)

    telemetry.step("🤖 Starting AI Workflow...")
    telemetry.step(f"   Target: {target_path}")
    telemetry.step(f"   Max iterations: {max_iterations}")

    # Get dependencies
    config_loader = ConfigurationLoader()
    astroid_gateway = container.get("AstroidGateway")
    ruff_adapter = container.get("RuffAdapter")
    filesystem = container.get("FileSystemGateway")
    mypy_adapter = container.get("MypyAdapter")
    excelsior_adapter = container.get("ExcelsiorAdapter")
    import_linter_adapter = container.get("ImportLinterAdapter")

    # Create CheckAuditUseCase for re-auditing
    check_audit_use_case = CheckAuditUseCase(
        mypy_adapter=mypy_adapter,
        excelsior_adapter=excelsior_adapter,
        import_linter_adapter=import_linter_adapter,
        ruff_adapter=ruff_adapter,
        telemetry=telemetry,
        config_loader=config_loader,
    )

    # Create rules for auto-fixable violations
    from clean_architecture_linter.domain.rules.immutability import DomainImmutabilityRule
    from clean_architecture_linter.domain.rules.type_hints import MissingTypeHintRule

    w9015_rule = MissingTypeHintRule(astroid_gateway)
    w9601_rule = DomainImmutabilityRule()
    rules = [w9015_rule, w9601_rule]

    # Create ApplyFixesUseCase
    use_case = ApplyFixesUseCase(
        LibCSTFixerGateway(),
        filesystem=filesystem,
        telemetry=telemetry,
        require_confirmation=False,
        create_backups=True,
        cleanup_backups=False,
        validate_with_tests=not skip_tests,
        astroid_gateway=astroid_gateway,
        ruff_adapter=ruff_adapter,
        check_audit_use_case=check_audit_use_case,
        config_loader=config_loader,
    )

    # Iterative fix/check cycle
    iteration = 0
    while iteration < max_iterations:
        iteration += 1
        telemetry.step(f"\n🔄 Iteration {iteration}/{max_iterations}")

        # Step 1: Run fixes
        telemetry.step("   Step 1: Running excelsior fix...")
        modified = use_case.execute_multi_pass(rules, target_path)
        if modified == 0:
            telemetry.step("   ℹ️  No fixes applied in this iteration.")
        else:
            telemetry.step(f"   ✅ Fixed {modified} file(s)")

        # Step 2: Re-audit to get current state
        telemetry.step("   Step 2: Re-running audit...")
        audit_result = check_audit_use_case.execute(target_path)

        # Step 3: Check if we're done
        if not audit_result.has_violations():
            telemetry.step("   ✅ No violations remaining!")
            break

        if audit_result.is_blocked():
            telemetry.step(
                f"   ⚠️  Blocked by {audit_result.blocked_by}. "
                "Cannot proceed until upstream violations are fixed."
            )
            break

        # Continue to next iteration if violations remain
        total_violations = (
            len(audit_result.ruff_results)
            + len(audit_result.mypy_results)
            + len(audit_result.excelsior_results)
            + len(audit_result.import_linter_results)
        )
        telemetry.step(f"   ℹ️  {total_violations} violation(s) remaining")

    # Final audit
    telemetry.step("\n📊 Final audit...")
    final_audit_result = check_audit_use_case.execute(target_path)

    # Save standard audit trail
    audit_trail_service = container.get("AuditTrailService")
    audit_trail_service.save_audit_trail(final_audit_result)

    # Generate AI handover bundle
    telemetry.step("\n🤖 Generating AI handover bundle...")
    handover_path = audit_trail_service.save_ai_handover(final_audit_result)

    # Print summary
    print("\n" + "=" * 60)
    print("🤖 EXCELSIOR AI WORKFLOW COMPLETE")
    print("=" * 60)
    print(f"Iterations completed: {iteration}/{max_iterations}")
    print(f"\n📁 AI Handover Bundle: {handover_path}")
    print("\n📋 Summary:")
    if final_audit_result.has_violations():
        total = (
            len(final_audit_result.ruff_results)
            + len(final_audit_result.mypy_results)
            + len(final_audit_result.excelsior_results)
            + len(final_audit_result.import_linter_results)
        )
        print(f"   ⚠️  {total} violation(s) remaining")
        print("\n💡 Next Steps:")
        print("   1. Review ai_handover.json for structured violation data")
        print("   2. Search for 'EXCELSIOR' comments in source files")
        print("   3. Fix violations guided by governance comments")
        print("   4. Re-run 'excelsior check' to verify fixes")
    else:
        print("   ✅ No violations found! Codebase is clean.")
    print("=" * 60 + "\n")

    # Exit with error code if violations found
    if final_audit_result.has_violations():
        sys.exit(1)
    sys.exit(0)


@app.command(name="init")
def init_clean_arch(
    template: Optional[str] = typer.Option(
        None, "--template", help="Pre-configure for frameworks"),
    check_layers: bool = typer.Option(
        False, "--check-layers", help="Verify active layer configuration"),
) -> None:
    """Initialize configuration."""
    container = ExcelsiorContainer()
    telemetry = container.get("TelemetryPort")
    telemetry.handshake()

    scaffolder = container.get("Scaffolder")
    use_case = InitProjectUseCase(scaffolder, telemetry)
    use_case.execute(template=template, check_layers=check_layers)


def main() -> None:
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
