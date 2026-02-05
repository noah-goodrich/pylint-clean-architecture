"""CLI entry points for Excelsior - Thin Controller using Typer."""

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, cast

import typer

from clean_architecture_linter.domain.config import ConfigurationLoader
from clean_architecture_linter.domain.constants import EXCELSIOR_BANNER
from clean_architecture_linter.domain.protocols import (
    ArtifactStorageProtocol,
    AstroidProtocol,
    AuditTrailServiceProtocol,
    FileSystemProtocol,
    FixerGatewayProtocol,
    GuidanceServiceProtocol,
    LinterAdapterProtocol,
    ScaffolderProtocol,
    StubCreatorProtocol,
    TelemetryPort,
    ViolationBridgeProtocol,
)
from clean_architecture_linter.domain.rules import BaseRule
from clean_architecture_linter.interface.reporters import AuditReporter
from clean_architecture_linter.use_cases.apply_fixes import ApplyFixesUseCase
from clean_architecture_linter.use_cases.check_audit import CheckAuditUseCase
from clean_architecture_linter.use_cases.init_project import InitProjectUseCase
from clean_architecture_linter.use_cases.plan_fix import PlanFixUseCase

# B008: avoid function call in default; use module-level singleton for Typer Option
_STUB_CREATE_PROJECT_ROOT = typer.Option(
    None, "--project-root", "-C", help="Project root (default: current directory)")


@dataclass(frozen=True)
class CLIDependencies:
    """Explicit dependencies for the CLI. All dependencies injected at composition root."""

    config_loader: ConfigurationLoader
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
    artifact_storage: ArtifactStorageProtocol
    fixer_gateway: FixerGatewayProtocol
    guidance_service: GuidanceServiceProtocol
    stub_creator: StubCreatorProtocol
    violation_bridge: ViolationBridgeProtocol


class CLIAppFactory:
    """Creates the Typer app. No top-level functions (W9018)."""

    @staticmethod
    def resolve_target_path(path: Optional[Path]) -> str:
        """Resolve target path: explicit path, else src/ if exists, else '.' (public API)."""
        if path and str(path) != ".":
            return str(path)
        cwd = Path.cwd()
        src_dir = cwd / "src"
        if src_dir.exists() and src_dir.is_dir():
            return "src"
        return "."

    @staticmethod
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
            view: str = typer.Option(
                "by_code", help="Table view: by_code (default) or by_file"),
            interactive: bool = typer.Option(
                None,
                "--interactive/--no-interactive",
                help="Prompt to create stubs for W9019 (uninferable dependency). Default: True when TTY.",
            ),
        ) -> None:
            """Run the gated sequential audit (Ruff → Mypy → Excelsior)."""
            deps.telemetry.handshake()
            target_path = CLIAppFactory.resolve_target_path(path)
            use_case = CheckAuditUseCase(
                mypy_adapter=deps.mypy_adapter,
                excelsior_adapter=deps.excelsior_adapter,
                import_linter_adapter=deps.import_linter_adapter,
                ruff_adapter=deps.ruff_adapter,
                telemetry=deps.telemetry,
                config_loader=deps.config_loader,
            )
            audit_result = use_case.execute(target_path)
            deps.reporter.report_audit(audit_result, view=view)
            deps.audit_trail_service.save_audit_trail(
                audit_result, source="check")
            handover_key = deps.audit_trail_service.save_ai_handover(
                audit_result, source="check")
            deps.audit_trail_service.append_audit_history(
                audit_result,
                source="check",
                json_path="check/last_audit.json",
                txt_path="check/last_audit.txt",
            )
            deps.telemetry.step("AI Agent Handover initialized.")
            print("\n" + "=" * 40)
            print("🤖 EXCELSIOR v2: AI HANDOVER")
            print("=" * 40)
            print("System Integrity Report completed.")
            print("Audit (check): .excelsior/check/last_audit.json")
            print("AI Handover (check): .excelsior/check/ai_handover.json")
            print("History (append): .excelsior/audit_history.jsonl")
            if audit_result.has_violations():
                content = deps.artifact_storage.read_artifact(handover_key)
                handover = json.loads(content)
                rule_ids = handover.get("rule_ids") or []
                if rule_ids:
                    print(
                        "Next: run 'excelsior plan-fix <rule_id>' for each violation type.")
                    print("Rule IDs:", ", ".join(rule_ids))
                else:
                    print(
                        "Next: run 'excelsior plan-fix <rule_id>' (see handover for rule_ids).")
            else:
                print(
                    "Next: run 'excelsior fix' for auto-fixes, or 'excelsior plan-fix <rule_id>' for guided fixes.")
            print("=" * 40 + "\n")

            # Option C: interactive stub creation for W9019
            do_interactive = interactive if interactive is not None else sys.stdin.isatty()
            if do_interactive and audit_result.excelsior_results:
                w9019_modules = deps.stub_creator.extract_w9019_modules(
                    audit_result.excelsior_results)
                project_root = str(Path.cwd())
                for mod in sorted(w9019_modules):
                    filename = f"{mod.replace('.', '/')}.pyi"
                    stub_path = Path(project_root) / "stubs" / filename
                    try:
                        resp = input(
                            f"Create stub for {mod}? (y/n) [n]: ").strip().lower() or "n"
                    except (EOFError, KeyboardInterrupt):
                        break
                    if resp != "y":
                        continue
                    overwrite = False
                    if stub_path.exists():
                        try:
                            ow = input(
                                f"  {stub_path} exists. Overwrite? (y/n) [n]: ").strip().lower() or "n"
                            overwrite = ow == "y"
                        except (EOFError, KeyboardInterrupt):
                            continue
                    ok, msg = deps.stub_creator.create_stub(
                        mod, project_root, use_stubgen=True, overwrite=overwrite)
                    if ok:
                        print(f"  Created stub: {stub_path} ({msg})")
                    else:
                        print(f"  Skipped: {msg}")

            if audit_result.has_violations():
                sys.exit(1)
            sys.exit(0)

        @app.command()
        def fix(
            path: Optional[Path] = typer.Argument(None, help="Path to fix (default: current directory, .)"),  # noqa: B008, RUF100
            linter: str = typer.Option(
                "all", help="Which linter to fix violations for"),
            confirm: bool = typer.Option(
                False, "--confirm", help="Require confirmation before each fix"),
            no_backup: bool = typer.Option(
                False, "--no-backup", help="Skip creating .bak backup files"),
            skip_tests: bool = typer.Option(
                False, "--skip-tests", help="Skip pytest validation"),
            cleanup_backups: bool = typer.Option(
                False, "--cleanup-backups", help="Remove .bak files after successful fixes"
            ),
            manual_only: bool = typer.Option(
                False, "--manual-only", help="Show manual fix suggestions only"),
            comments: bool = typer.Option(
                False,
                "--comments",
                help="Inject EXCELSIOR governance comment blocks above violation lines (Pass 4). Default: use handover + plan-fix for instructions.",
            ),
        ) -> None:
            """Apply deterministic fixes. Use plan-fix for per-violation instructions; pass --comments to inject in-file governance comments."""
            deps.telemetry.handshake()
            target_path = CLIAppFactory.resolve_target_path(path)
            if manual_only:
                _run_fix_manual_only(deps, target_path, linter)
                return
            if linter == "ruff":
                _run_fix_ruff(deps, target_path)
                return
            _run_fix_excelsior(deps, target_path, confirm, no_backup,
                               skip_tests, cleanup_backups, comments)

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
                d.telemetry.step(
                    "📋 Gathering manual fix suggestions from all linters...")
            elif linter == "ruff":
                adapters = [(n, a)
                            for n, a, lt in all_adapters if lt == "ruff"]
                d.telemetry.step(
                    "📋 Gathering manual fix suggestions from Ruff...")
            else:
                adapters = [(n, a)
                            for n, a, lt in all_adapters if lt == "excelsior"]
                d.telemetry.step(
                    "📋 Gathering manual fix suggestions from Excelsior suite...")
            for linter_name, adapter in adapters:
                results = adapter.gather_results(target_path)
                if not results:
                    continue
                print(
                    f"\n{'=' * 60}\n{linter_name} - {len(results)} violation(s)\n{'=' * 60}")
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
                            print(
                                f"    ... and {len(result.locations) - 5} more")
                    if not (adapter.supports_autofix() and result.code in adapter.get_fixable_rules()):
                        instructions = adapter.get_manual_fix_instructions(
                            result.code)
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
            inject_governance_comments: bool = False,
        ) -> None:
            """Run multi-pass fixer: Ruff → W9015 → Re-audit + Architecture. Pass 4 (governance comments) only when inject_governance_comments is True."""
            check_audit_use_case = CheckAuditUseCase(
                mypy_adapter=d.mypy_adapter,
                excelsior_adapter=d.excelsior_adapter,
                import_linter_adapter=d.import_linter_adapter,
                ruff_adapter=d.ruff_adapter,
                telemetry=d.telemetry,
                config_loader=d.config_loader,
            )
            from clean_architecture_linter.domain.rules.immutability import DomainImmutabilityRule
            from clean_architecture_linter.domain.rules.type_hints import MissingTypeHintRule

            w9015_rule = MissingTypeHintRule(d.astroid_gateway)
            w9601_rule = DomainImmutabilityRule()
            rules = cast(list[BaseRule], [w9015_rule, w9601_rule])
            use_case = ApplyFixesUseCase(
                d.fixer_gateway,
                d.filesystem,
                linter_adapter=d.excelsior_adapter,
                telemetry=d.telemetry,
                astroid_gateway=d.astroid_gateway,
                ruff_adapter=d.ruff_adapter,
                check_audit_use_case=check_audit_use_case,
                config_loader=d.config_loader,
                excelsior_adapter=d.excelsior_adapter,
                violation_bridge=d.violation_bridge,
                require_confirmation=confirm,
                create_backups=not no_backup,
                cleanup_backups=cleanup_backups,
                validate_with_tests=not skip_tests,
            )
            modified = use_case.execute_multi_pass(
                rules, target_path, inject_governance_comments=inject_governance_comments
            )
            d.telemetry.step(
                f"✅ Successfully fixed {modified} file(s)" if modified > 0 else "ℹ️  No fixes applied")
            post_fix_audit = check_audit_use_case.execute(target_path)
            d.audit_trail_service.save_audit_trail(
                post_fix_audit, source="fix")
            d.audit_trail_service.save_ai_handover(
                post_fix_audit, source="fix")
            d.audit_trail_service.append_audit_history(
                post_fix_audit,
                source="fix",
                json_path="fix/last_audit.json",
                txt_path="fix/last_audit.txt",
            )
            sys.exit(0)

        @app.command()
        def ai_workflow(
            path: Optional[Path] = typer.Argument(None, help="Path to audit (default: current directory, .)"),  # noqa: B008, RUF100
            max_iterations: int = typer.Option(
                5, "--max-iterations", help="Maximum fix/check cycles before stopping"),
            skip_tests: bool = typer.Option(
                False, "--skip-tests", help="Skip pytest validation during fixes"),
        ) -> None:
            """Unified AI workflow: auto-fix → inject comments → provide structured handover."""
            deps.telemetry.handshake()
            target_path = CLIAppFactory.resolve_target_path(path)
            deps.telemetry.step("🤖 Starting AI Workflow...")
            deps.telemetry.step(f"   Target: {target_path}")
            deps.telemetry.step(f"   Max iterations: {max_iterations}")
            check_audit_use_case = CheckAuditUseCase(
                mypy_adapter=deps.mypy_adapter,
                excelsior_adapter=deps.excelsior_adapter,
                import_linter_adapter=deps.import_linter_adapter,
                ruff_adapter=deps.ruff_adapter,
                telemetry=deps.telemetry,
                config_loader=deps.config_loader,
            )
            from clean_architecture_linter.domain.rules.immutability import DomainImmutabilityRule
            from clean_architecture_linter.domain.rules.type_hints import MissingTypeHintRule

            w9015_rule = MissingTypeHintRule(deps.astroid_gateway)
            w9601_rule = DomainImmutabilityRule()
            rules = cast(list[BaseRule], [w9015_rule, w9601_rule])
            use_case = ApplyFixesUseCase(
                deps.fixer_gateway,
                deps.filesystem,
                linter_adapter=deps.excelsior_adapter,
                telemetry=deps.telemetry,
                astroid_gateway=deps.astroid_gateway,
                ruff_adapter=deps.ruff_adapter,
                check_audit_use_case=check_audit_use_case,
                config_loader=deps.config_loader,
                excelsior_adapter=deps.excelsior_adapter,
                violation_bridge=deps.violation_bridge,
                require_confirmation=False,
                create_backups=True,
                cleanup_backups=False,
                validate_with_tests=not skip_tests,
            )
            iteration = 0
            while iteration < max_iterations:
                iteration += 1
                deps.telemetry.step(
                    f"\n🔄 Iteration {iteration}/{max_iterations}")
                deps.telemetry.step("   Step 1: Running excelsior fix...")
                modified = use_case.execute_multi_pass(rules, target_path)
                if modified == 0:
                    deps.telemetry.step(
                        "   ℹ️  No fixes applied in this iteration.")
                else:
                    deps.telemetry.step(f"   ✅ Fixed {modified} file(s)")
                deps.telemetry.step("   Step 2: Re-running audit...")
                audit_result = check_audit_use_case.execute(target_path)
                if not audit_result.has_violations():
                    deps.telemetry.step("   ✅ No violations remaining!")
                    break
                if audit_result.is_blocked():
                    deps.telemetry.step(
                        f"   ⚠️  Blocked by {audit_result.blocked_by}. Cannot proceed until upstream violations are fixed."
                    )
                    break
                total_violations = (
                    len(audit_result.ruff_results)
                    + len(audit_result.mypy_results)
                    + len(audit_result.excelsior_results)
                    + len(audit_result.import_linter_results)
                )
                deps.telemetry.step(
                    f"   ℹ️  {total_violations} violation(s) remaining")
            deps.telemetry.step("\n📊 Final audit...")
            final_audit_result = check_audit_use_case.execute(target_path)
            deps.audit_trail_service.save_audit_trail(
                final_audit_result, source="ai_workflow")
            deps.telemetry.step("\n🤖 Generating AI handover bundle...")
            handover_path = deps.audit_trail_service.save_ai_handover(
                final_audit_result, source="ai_workflow")
            deps.audit_trail_service.append_audit_history(
                final_audit_result,
                source="ai_workflow",
                json_path="ai_workflow/last_audit.json",
                txt_path="ai_workflow/last_audit.txt",
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
                print(
                    "   1. Review ai_workflow/ai_handover.json for structured violation data")
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
            template: Optional[str] = typer.Option(
                None, "--template", help="Pre-configure for frameworks"),
            check_layers: bool = typer.Option(
                False, "--check-layers", help="Verify active layer configuration"),
        ) -> None:
            """Initialize configuration."""
            deps.telemetry.handshake()
            use_case = InitProjectUseCase(deps.scaffolder, deps.telemetry)
            use_case.execute(template=template, check_layers=check_layers)

        @app.command(name="generate-guidance")
        def generate_guidance(
            output_dir: str = typer.Option(
                "docs", "--output-dir", help="Directory for GENERATION_GUIDANCE.md"),
            update_cursorrules: bool = typer.Option(
                True, "--cursorrules/--no-cursorrules", help="Append to .cursorrules if present"
            ),
        ) -> None:
            """Generate docs/GENERATION_GUIDANCE.md from the rule registry (editor-agnostic). Optionally append to .cursorrules if it exists."""
            deps.telemetry.handshake()
            entries = deps.guidance_service.iter_proactive_guidance()
            lines = [
                "# Generation Guidance: Write Code That Passes Excelsior",
                "",
                "When **writing or editing Python** in this repo, follow these patterns so Excelsior (and ruff, import-linter, mypy, pylint) find fewer violations. This is **proactive** guidance—use it during generation, not only when fixing after a failed check.",
                "",
                "This file is generated by `excelsior generate-guidance`. The canonical registry is in the package: `infrastructure/resources/rule_registry.yaml` keyed by `{linter}.{rule_code}`.",
                "",
                "---",
                "",
                "## Rule of the First Prompt",
                "",
                'Never ask an AI to "implement X" without first asking it to **"Draft a Dependency Plan for X."** Define which **Layer** the code belongs in, which **Protocols** it will implement, and what **Infrastructure** it will touch—*before* writing logic.',
                "",
                "## Negative Constraint List",
                "",
                "- No direct imports of `libcst` in Domain. No top-level functions in UseCases. No use of `Any`.",
                "- Domain has no I/O. UseCase receives dependencies via constructor injection.",
                "",
                "## Protocol-First",
                "",
                "When adding new behavior, define the Domain Protocol first, then implement in Infrastructure.",
                "",
                "---",
                "",
                "## Proactive guidance by rule",
                "",
            ]
            current_linter: Optional[str] = None
            for rule_id, short_desc, guidance in entries:
                linter = rule_id.split(".", 1)[0] if "." in rule_id else ""
                if linter and linter != current_linter:
                    current_linter = linter
                    lines.append(f"### {linter}")
                    lines.append("")
                lines.append(f"- **{rule_id}** ({short_desc})")
                lines.append(f"  {guidance}")
                lines.append("")
            lines.append("---")
            lines.append("")
            lines.append(
                "For the **exact prompt for a specific rule** when fixing a violation, use the registry key `{linter}.{rule_code}` (e.g. `mypy.type-arg`, `excelsior.W9006`)."
            )
            content = "\n".join(lines)
            out_path = Path(output_dir) / "GENERATION_GUIDANCE.md"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(content, encoding="utf-8")
            deps.telemetry.step(f"Wrote {out_path}")
            if update_cursorrules:
                cursorrules = Path(".cursorrules")
                if cursorrules.exists():
                    section = "\n\n## Excelsior proactive guidance\n\nWhen editing Python, follow docs/GENERATION_GUIDANCE.md (or run `excelsior generate-guidance` to refresh it).\n"
                    with cursorrules.open("a", encoding="utf-8") as f:
                        f.write(section)
                    deps.telemetry.step(
                        "Appended Excelsior section to .cursorrules")
                else:
                    deps.telemetry.step(
                        ".cursorrules not found; skipped (editor-agnostic).")
            print(f"Generated: {out_path}")

        @app.command(name="plan-fix")
        def plan_fix(
            rule_id: str = typer.Argument(
                ..., help="Registry rule ID (e.g. excelsior.W9015, mypy.no-any-return)"),
            violation_index: int = typer.Option(
                0, "--violation-index", "-n", help="Which occurrence (0-based)"),
            source: str = typer.Option(
                "check", "--source", "-s", help="Handover source: check, fix, or ai_workflow"),
        ) -> None:
            """Generate a single-violation fix plan markdown from the latest handover."""
            deps.telemetry.handshake()
            handover_key = f"{source}/ai_handover.json" if source else "ai_handover.json"
            if not deps.artifact_storage.exists(handover_key):
                print(
                    f"Error: Handover not found: {handover_key}. Run 'excelsior check' (or fix/ai-workflow) first.",
                    file=sys.stderr,
                )
                sys.exit(1)
            content = deps.artifact_storage.read_artifact(handover_key)
            handover = json.loads(content)
            violations_by_rule = handover.get("violations_by_rule") or {}
            matching = [
                entry
                for entries in violations_by_rule.values()
                for entry in entries
                if entry.get("rule_id") == rule_id
            ]
            if not matching:
                print(
                    f"Error: No violation found for rule_id '{rule_id}' in {handover_key}. "
                    "Run 'excelsior check' and ensure there is at least one violation for this rule.",
                    file=sys.stderr,
                )
                sys.exit(1)
            if violation_index < 0 or violation_index >= len(matching):
                print(
                    f"Error: violation_index {violation_index} out of range (0..{len(matching) - 1}) "
                    f"for rule_id '{rule_id}' ({len(matching)} occurrence(s)).",
                    file=sys.stderr,
                )
                sys.exit(1)
            violation = matching[violation_index]
            use_case = PlanFixUseCase(
                artifact_storage=deps.artifact_storage,
                guidance_service=deps.guidance_service,
            )
            out_key = use_case.write_fix_plan(
                rule_id=rule_id, violation=violation)
            deps.telemetry.step(f"Wrote fix plan: {out_key}")
            print(f"Fix plan: .excelsior/{out_key}")

        @app.command(name="stub-create")
        def stub_create(
            module: str = typer.Argument(...,
                                         help="Module name (e.g. foo.bar) to create stub for"),
            project_root: Optional[Path] = _STUB_CREATE_PROJECT_ROOT,
            no_stubgen: bool = typer.Option(
                False, "--no-stubgen", help="Skip mypy stubgen; write minimal stub only"),
            overwrite: bool = typer.Option(
                False, "--overwrite", help="Overwrite existing stub file"),
        ) -> None:
            """Create a .pyi stub for a module (stubgen or minimal) and add stubs to mypy_path."""
            deps.telemetry.handshake()
            root = str((project_root or Path.cwd()).resolve())
            ok, msg = deps.stub_creator.create_stub(
                module, root, use_stubgen=not no_stubgen, overwrite=overwrite)
            if ok:
                stub_path = Path(root) / "stubs" / \
                    (module.replace(".", "/") + ".pyi")
                print(f"Created stub: {stub_path} ({msg})")
            else:
                print(f"Skipped: {msg}", file=sys.stderr)
                sys.exit(1)

        return app
