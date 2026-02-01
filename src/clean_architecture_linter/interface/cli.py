"""CLI entry points for Excelsior - Thin Controller using Typer."""

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import typer

from clean_architecture_linter.domain.config import ConfigurationLoader
from clean_architecture_linter.domain.constants import EXCELSIOR_BANNER
from clean_architecture_linter.domain.protocols import (
    AstroidProtocol,
    AuditTrailServiceProtocol,
    FileSystemProtocol,
    FixerGatewayProtocol,
    LinterAdapterProtocol,
    ScaffolderProtocol,
    TelemetryPort,
)
from clean_architecture_linter.interface.reporters import AuditReporter
from clean_architecture_linter.use_cases.apply_fixes import ApplyFixesUseCase
from clean_architecture_linter.use_cases.check_audit import CheckAuditUseCase
from clean_architecture_linter.use_cases.init_project import InitProjectUseCase


def _resolve_target_path(path: Optional[Path]) -> str:
    """Resolve target path: explicit path, else src/ if exists, else '.'."""
    if path and str(path) != ".":
        return str(path)
    cwd = Path.cwd()
    src_dir = cwd / "src"
    if src_dir.exists() and src_dir.is_dir():
        return "src"
    return "."


@dataclass(frozen=True)
class CLIDependencies:
    """Explicit dependencies for the CLI. All dependencies injected at composition root."""

    telemetry: TelemetryPort
    mypy_adapter: LinterAdapterProtocol
    excelsior_adapter: LinterAdapterProtocol
    import_linter_adapter: LinterAdapterProtocol
    ruff_adapter: LinterAdapterProtocol
    reporter: AuditReporter
    audit_trail_service: AuditTrailServiceProtocol
    scaffolder: ScaffolderProtocol
    astroid_gateway: AstroidProtocol
    filesystem: FileSystemProtocol
    fixer_gateway: FixerGatewayProtocol


def create_app(deps: CLIDependencies) -> typer.Typer:
    """Create the Typer app with explicitly injected dependencies. No Service Locator."""
    app = typer.Typer(
        name="excelsior",
        help=f"{EXCELSIOR_BANNER}\nExcelsior: High-Integrity Architectural Governance",
        add_completion=False,
    )

    @app.command()
    def check(
        path: Optional[Path] = typer.Argument(None, help="Path to audit (default: current directory, .)"),  # noqa: B008, RUF100
        linter: str = typer.Option("all", help="Specific linter to run"),
    ) -> None:
        """Run the gated sequential audit (Ruff → Mypy → Excelsior)."""
        deps.telemetry.handshake()
        target_path = _resolve_target_path(path)
        config_loader = ConfigurationLoader()
        use_case = CheckAuditUseCase(
            mypy_adapter=deps.mypy_adapter,
            excelsior_adapter=deps.excelsior_adapter,
            import_linter_adapter=deps.import_linter_adapter,
            ruff_adapter=deps.ruff_adapter,
            telemetry=deps.telemetry,
            config_loader=config_loader,
        )
        audit_result = use_case.execute(target_path)
        deps.reporter.report_audit(audit_result)
        deps.audit_trail_service.save_audit_trail(audit_result, source="check")
        deps.audit_trail_service.save_ai_handover(audit_result, source="check")
        deps.audit_trail_service.append_audit_history(
            audit_result,
            source="check",
            json_path=".excelsior/last_audit_check.json",
            txt_path=".excelsior/last_audit_check.txt",
        )
        deps.telemetry.step("AI Agent Handover initialized.")
        print("\n" + "=" * 40)
        print("🤖 EXCELSIOR v2: AI HANDOVER")
        print("=" * 40)
        print("System Integrity Report completed.")
        print("Audit (check): .excelsior/last_audit_check.json")
        print("AI Handover (check): .excelsior/ai_handover_check.json")
        print("History (append): .excelsior/audit_history.jsonl")
        print("Run 'excelsior fix' to resolve common issues.")
        print("=" * 40 + "\n")
        if audit_result.has_violations():
            sys.exit(1)
        sys.exit(0)

    @app.command()
    def fix(
        path: Optional[Path] = typer.Argument(None, help="Path to fix (default: current directory, .)"),  # noqa: B008, RUF100
        linter: str = typer.Option("all", help="Which linter to fix violations for"),
        confirm: bool = typer.Option(False, "--confirm", help="Require confirmation before each fix"),
        no_backup: bool = typer.Option(False, "--no-backup", help="Skip creating .bak backup files"),
        skip_tests: bool = typer.Option(False, "--skip-tests", help="Skip pytest validation"),
        cleanup_backups: bool = typer.Option(False, "--cleanup-backups", help="Remove .bak files after successful fixes"),
        manual_only: bool = typer.Option(False, "--manual-only", help="Show manual fix suggestions only"),
    ) -> None:
        """Apply deterministic fixes and inject architectural commentary."""
        deps.telemetry.handshake()
        target_path = _resolve_target_path(path)
        if manual_only:
            _run_fix_manual_only(deps, target_path, linter)
            return
        if linter == "ruff":
            _run_fix_ruff(deps, target_path)
            return
        _run_fix_excelsior(deps, target_path, confirm, no_backup, skip_tests, cleanup_backups)

    def _run_fix_manual_only(
        d: CLIDependencies,
        target_path: str,
        linter: str,
    ) -> None:
        """Show manual fix suggestions only."""
        all_adapters = [
            ("Ruff", d.ruff_adapter, "ruff"),
            ("Mypy", d.mypy_adapter, "excelsior"),
            ("Excelsior", d.excelsior_adapter, "excelsior"),
            ("Import-Linter", d.import_linter_adapter, "excelsior"),
        ]
        if linter == "all":
            adapters = [(n, a) for n, a, _ in all_adapters]
            d.telemetry.step("📋 Gathering manual fix suggestions from all linters...")
        elif linter == "ruff":
            adapters = [(n, a) for n, a, lt in all_adapters if lt == "ruff"]
            d.telemetry.step("📋 Gathering manual fix suggestions from Ruff...")
        else:
            adapters = [(n, a) for n, a, lt in all_adapters if lt == "excelsior"]
            d.telemetry.step("📋 Gathering manual fix suggestions from Excelsior suite...")
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

    def _run_fix_ruff(d: CLIDependencies, target_path: str) -> None:
        """Apply Ruff fixes only."""
        d.telemetry.step("🔧 Applying Ruff fixes...")
        success = d.ruff_adapter.apply_fixes(Path(target_path))
        d.telemetry.step(
            "✅ Ruff fixes complete. Run 'excelsior check' to verify." if success else "❌ Ruff fixing failed"
        )
        sys.exit(0 if success else 1)

    def _run_fix_excelsior(
        d: CLIDependencies,
        target_path: str,
        confirm: bool,
        no_backup: bool,
        skip_tests: bool,
        cleanup_backups: bool,
    ) -> None:
        """Run multi-pass fixer: Ruff → W9015 → Re-audit + Architecture."""
        config_loader = ConfigurationLoader()
        check_audit_use_case = CheckAuditUseCase(
            mypy_adapter=d.mypy_adapter,
            excelsior_adapter=d.excelsior_adapter,
            import_linter_adapter=d.import_linter_adapter,
            ruff_adapter=d.ruff_adapter,
            telemetry=d.telemetry,
            config_loader=config_loader,
        )
        from clean_architecture_linter.domain.rules.immutability import DomainImmutabilityRule
        from clean_architecture_linter.domain.rules.type_hints import MissingTypeHintRule

        w9015_rule = MissingTypeHintRule(d.astroid_gateway)
        w9601_rule = DomainImmutabilityRule()
        rules = [w9015_rule, w9601_rule]
        use_case = ApplyFixesUseCase(
            d.fixer_gateway,
            filesystem=d.filesystem,
            telemetry=d.telemetry,
            require_confirmation=confirm,
            create_backups=not no_backup,
            cleanup_backups=cleanup_backups,
            validate_with_tests=not skip_tests,
            astroid_gateway=d.astroid_gateway,
            ruff_adapter=d.ruff_adapter,
            check_audit_use_case=check_audit_use_case,
            config_loader=config_loader,
            excelsior_adapter=d.excelsior_adapter,
        )
        modified = use_case.execute_multi_pass(rules, target_path)
        d.telemetry.step(
            f"✅ Successfully fixed {modified} file(s)" if modified > 0 else "ℹ️  No fixes applied"
        )
        post_fix_audit = check_audit_use_case.execute(target_path)
        d.audit_trail_service.save_audit_trail(post_fix_audit, source="fix")
        d.audit_trail_service.save_ai_handover(post_fix_audit, source="fix")
        d.audit_trail_service.append_audit_history(
            post_fix_audit,
            source="fix",
            json_path=".excelsior/last_audit_fix.json",
            txt_path=".excelsior/last_audit_fix.txt",
        )
        sys.exit(0)

    @app.command()
    def ai_workflow(
        path: Optional[Path] = typer.Argument(None, help="Path to audit (default: current directory, .)"),  # noqa: B008, RUF100
        max_iterations: int = typer.Option(5, "--max-iterations", help="Maximum fix/check cycles before stopping"),
        skip_tests: bool = typer.Option(False, "--skip-tests", help="Skip pytest validation during fixes"),
    ) -> None:
        """Unified AI workflow: auto-fix → inject comments → provide structured handover."""
        deps.telemetry.handshake()
        target_path = _resolve_target_path(path)
        deps.telemetry.step("🤖 Starting AI Workflow...")
        deps.telemetry.step(f"   Target: {target_path}")
        deps.telemetry.step(f"   Max iterations: {max_iterations}")
        config_loader = ConfigurationLoader()
        check_audit_use_case = CheckAuditUseCase(
            mypy_adapter=deps.mypy_adapter,
            excelsior_adapter=deps.excelsior_adapter,
            import_linter_adapter=deps.import_linter_adapter,
            ruff_adapter=deps.ruff_adapter,
            telemetry=deps.telemetry,
            config_loader=config_loader,
        )
        from clean_architecture_linter.domain.rules.immutability import DomainImmutabilityRule
        from clean_architecture_linter.domain.rules.type_hints import MissingTypeHintRule

        w9015_rule = MissingTypeHintRule(deps.astroid_gateway)
        w9601_rule = DomainImmutabilityRule()
        rules = [w9015_rule, w9601_rule]
        use_case = ApplyFixesUseCase(
            deps.fixer_gateway,
            filesystem=deps.filesystem,
            telemetry=deps.telemetry,
            require_confirmation=False,
            create_backups=True,
            cleanup_backups=False,
            validate_with_tests=not skip_tests,
            astroid_gateway=deps.astroid_gateway,
            ruff_adapter=deps.ruff_adapter,
            check_audit_use_case=check_audit_use_case,
            config_loader=config_loader,
            excelsior_adapter=deps.excelsior_adapter,
        )
        iteration = 0
        while iteration < max_iterations:
            iteration += 1
            deps.telemetry.step(f"\n🔄 Iteration {iteration}/{max_iterations}")
            deps.telemetry.step("   Step 1: Running excelsior fix...")
            modified = use_case.execute_multi_pass(rules, target_path)
            if modified == 0:
                deps.telemetry.step("   ℹ️  No fixes applied in this iteration.")
            else:
                deps.telemetry.step(f"   ✅ Fixed {modified} file(s)")
            deps.telemetry.step("   Step 2: Re-running audit...")
            audit_result = check_audit_use_case.execute(target_path)
            if not audit_result.has_violations():
                deps.telemetry.step("   ✅ No violations remaining!")
                break
            if audit_result.is_blocked():
                deps.telemetry.step(
                    f"   ⚠️  Blocked by {audit_result.blocked_by}. "
                    "Cannot proceed until upstream violations are fixed."
                )
                break
            total_violations = (
                len(audit_result.ruff_results)
                + len(audit_result.mypy_results)
                + len(audit_result.excelsior_results)
                + len(audit_result.import_linter_results)
            )
            deps.telemetry.step(f"   ℹ️  {total_violations} violation(s) remaining")
        deps.telemetry.step("\n📊 Final audit...")
        final_audit_result = check_audit_use_case.execute(target_path)
        deps.audit_trail_service.save_audit_trail(final_audit_result, source="ai_workflow")
        deps.telemetry.step("\n🤖 Generating AI handover bundle...")
        handover_path = deps.audit_trail_service.save_ai_handover(final_audit_result, source="ai_workflow")
        deps.audit_trail_service.append_audit_history(
            final_audit_result,
            source="ai_workflow",
            json_path=".excelsior/last_audit_ai_workflow.json",
            txt_path=".excelsior/last_audit_ai_workflow.txt",
        )
        print("\n" + "=" * 60)
        print("🤖 EXCELSIOR AI WORKFLOW COMPLETE")
        print("=" * 60)
        print(f"Iterations completed: {iteration}/{max_iterations}")
        print(f"\n📁 AI Handover Bundle: {handover_path}")
        print("   History (append): .excelsior/audit_history.jsonl")
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
            print("   1. Review ai_handover_ai_workflow.json for structured violation data")
            print("   2. Search for 'EXCELSIOR' comments in source files")
            print("   3. Fix violations guided by governance comments")
            print("   4. Re-run 'excelsior check' to verify fixes")
        else:
            print("   ✅ No violations found! Codebase is clean.")
        print("=" * 60 + "\n")
        if final_audit_result.has_violations():
            sys.exit(1)
        sys.exit(0)

    @app.command(name="init")
    def init_clean_arch(
        template: Optional[str] = typer.Option(None, "--template", help="Pre-configure for frameworks"),
        check_layers: bool = typer.Option(False, "--check-layers", help="Verify active layer configuration"),
    ) -> None:
        """Initialize configuration."""
        deps.telemetry.handshake()
        use_case = InitProjectUseCase(deps.scaffolder, deps.telemetry)
        use_case.execute(template=template, check_layers=check_layers)

    return app
