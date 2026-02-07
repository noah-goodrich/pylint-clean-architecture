"""CLI entry points for Excelsior - Thin Controller using Typer."""

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import typer

from excelsior_architect.domain.config import ConfigurationLoader
from excelsior_architect.domain.constants import EXCELSIOR_BANNER
from excelsior_architect.domain.protocols import (
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
from excelsior_architect.domain.rules import BaseRule
from excelsior_architect.interface.reporters import AuditReporter
from excelsior_architect.domain.analysis import (
    DesignPatternDecisionTree,
    HealthScorer,
    ViolationClusterer,
)
from excelsior_architect.use_cases.analyze_health import AnalyzeHealthUseCase
from excelsior_architect.use_cases.apply_fixes import ApplyFixesUseCase
from excelsior_architect.use_cases.check_audit import CheckAuditUseCase
from excelsior_architect.use_cases.init_project import InitProjectUseCase
from excelsior_architect.use_cases.plan_fix import PlanFixUseCase

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
    def resolve_target_path(path: Path | None) -> str:
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
            help="Excelsior: High-Integrity Architectural Governance. Run 'excelsior check' to audit; 'excelsior fix' to apply fixes.",
            add_completion=False,
        )

        def _session_start() -> None:
            """Print banner then handshake. Use at start of each command so banner renders correctly (not in --help)."""
            print(EXCELSIOR_BANNER)
            deps.telemetry.handshake()

        @app.command()
        def check(
            path: Path | None = typer.Argument(None, help="Path to audit (default: current directory, .)"),  # noqa: B008, RUF100
            linter: str = typer.Option("all", help="Specific linter to run"),
            view: str = typer.Option(
                "by_code", help="Table view: by_code (default) or by_file"),
            no_health: bool = typer.Option(
                False, "--no-health", help="Skip architectural health report"),
        ) -> None:
            """Run the gated sequential audit (Ruff → Mypy → Excelsior) and optionally the architectural health report."""
            _session_start()
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
                        "Next: run 'excelsior plan <rule_id>' for each violation type.")
                    print("Rule IDs:", ", ".join(rule_ids))
                else:
                    print(
                        "Next: run 'excelsior plan <rule_id>' (see handover for rule_ids).")
            else:
                print(
                    "Next: run 'excelsior fix' for auto-fixes, or 'excelsior plan <rule_id>' for guided fixes.")
            print("=" * 40 + "\n")

            if not no_health:
                clusterer = ViolationClusterer(deps.guidance_service)
                decision_tree = DesignPatternDecisionTree()
                scorer = HealthScorer()
                analyze_use_case = AnalyzeHealthUseCase(
                    clusterer=clusterer,
                    decision_tree=decision_tree,
                    scorer=scorer,
                    config_loader=deps.config_loader,
                )
                report = analyze_use_case.execute(audit_result)
                deps.audit_trail_service.save_report(report, source="health")
                deps.audit_trail_service.save_ai_handover(report, source="health")
                deps.reporter.render_health_report(
                    report, format="terminal", mode="standard")
                deps.telemetry.step("")
                deps.telemetry.step("Artifacts saved:")
                deps.telemetry.step(
                    "  Health report:  .excelsior/health/last_audit.json")
                deps.telemetry.step(
                    "  AI Handover:    .excelsior/health/ai_handover.json")
                deps.telemetry.step("")
                deps.telemetry.step("Next steps:")
                deps.telemetry.step(
                    "  1. Address HIGH/CRITICAL findings first (see Action Plan above)")
                deps.telemetry.step(
                    "  2. Run 'excelsior plan <rule_id>' for guided fix instructions")
                deps.telemetry.step(
                    "  3. Run 'excelsior fix' for auto-fixes, then 'excelsior check' to re-assess")

            if audit_result.has_violations():
                sys.exit(1)
            sys.exit(0)

        @app.command()
        def fix(
            path: Path | None = typer.Argument(None, help="Path to fix (default: current directory, .)"),  # noqa: B008, RUF100
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
                help="Inject EXCELSIOR governance comment blocks above violation lines (Pass 4). Default: use handover + plan for instructions.",
            ),
            iterative: bool = typer.Option(
                False, "--iterative", help="Iterative fix/check loop (was ai-workflow)"),
            max_iterations: int = typer.Option(
                5, "--max-iterations", help="Max cycles for --iterative"),
            stub: str | None = typer.Option(
                None, "--stub", help="Create .pyi stub for MODULE (e.g. foo.bar)"),
            no_stubgen: bool = typer.Option(
                False, "--no-stubgen", help="Skip mypy stubgen; minimal stub only (with --stub)"),
            overwrite_stub: bool = typer.Option(
                False, "--overwrite-stub", help="Overwrite existing stub (with --stub)"),
        ) -> None:
            """Apply deterministic fixes. Use plan for per-violation instructions; --iterative for fix/check loop; --stub to create .pyi stubs."""
            _session_start()
            target_path = CLIAppFactory.resolve_target_path(path)
            if stub is not None:
                root = str(Path.cwd().resolve())
                ok, msg = deps.stub_creator.create_stub(
                    stub, root, use_stubgen=not no_stubgen, overwrite=overwrite_stub)
                if ok:
                    stub_path = Path(root) / "stubs" / (stub.replace(".", "/") + ".pyi")
                    print(f"Created stub: {stub_path} ({msg})")
                else:
                    print(f"Skipped: {msg}", file=sys.stderr)
                    sys.exit(1)
                return
            if iterative:
                _run_fix_iterative(deps, target_path, max_iterations, skip_tests)
                return
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
            success = d.ruff_adapter.apply_fixes(target_path)
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
            from excelsior_architect.domain.rules.immutability import DomainImmutabilityRule
            from excelsior_architect.domain.rules.type_hints import MissingTypeHintRule

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

        def _run_fix_iterative(
            d: CLIDependencies,
            target_path: str,
            max_iterations: int,
            skip_tests: bool,
        ) -> None:
            """Run iterative fix/check loop (was ai-workflow)."""
            d.telemetry.step("🤖 Starting iterative fix/check loop...")
            d.telemetry.step(f"   Target: {target_path}")
            d.telemetry.step(f"   Max iterations: {max_iterations}")
            check_audit_use_case = CheckAuditUseCase(
                mypy_adapter=d.mypy_adapter,
                excelsior_adapter=d.excelsior_adapter,
                import_linter_adapter=d.import_linter_adapter,
                ruff_adapter=d.ruff_adapter,
                telemetry=d.telemetry,
                config_loader=d.config_loader,
            )
            from excelsior_architect.domain.rules.immutability import DomainImmutabilityRule
            from excelsior_architect.domain.rules.type_hints import MissingTypeHintRule

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
                require_confirmation=False,
                create_backups=True,
                cleanup_backups=False,
                validate_with_tests=not skip_tests,
            )
            iteration = 0
            while iteration < max_iterations:
                iteration += 1
                d.telemetry.step(
                    f"\n🔄 Iteration {iteration}/{max_iterations}")
                d.telemetry.step("   Step 1: Running excelsior fix...")
                modified = use_case.execute_multi_pass(rules, target_path)
                if modified == 0:
                    d.telemetry.step(
                        "   ℹ️  No fixes applied in this iteration.")
                else:
                    d.telemetry.step(f"   ✅ Fixed {modified} file(s)")
                d.telemetry.step("   Step 2: Re-running audit...")
                audit_result = check_audit_use_case.execute(target_path)
                if not audit_result.has_violations():
                    d.telemetry.step("   ✅ No violations remaining!")
                    break
                if audit_result.is_blocked():
                    d.telemetry.step(
                        f"   ⚠️  Blocked by {audit_result.blocked_by}. Cannot proceed until upstream violations are fixed."
                    )
                    break
                total_violations = (
                    len(audit_result.ruff_results)
                    + len(audit_result.mypy_results)
                    + len(audit_result.excelsior_results)
                    + len(audit_result.import_linter_results)
                )
                d.telemetry.step(
                    f"   ℹ️  {total_violations} violation(s) remaining")
            d.telemetry.step("\n📊 Final audit...")
            final_audit_result = check_audit_use_case.execute(target_path)
            d.audit_trail_service.save_audit_trail(
                final_audit_result, source="fix")
            d.telemetry.step("\n🤖 Generating AI handover bundle...")
            handover_path = d.audit_trail_service.save_ai_handover(
                final_audit_result, source="fix")
            d.audit_trail_service.append_audit_history(
                final_audit_result,
                source="fix",
                json_path="fix/last_audit.json",
                txt_path="fix/last_audit.txt",
            )
            print("\n" + "=" * 60)
            print("🤖 EXCELSIOR ITERATIVE FIX COMPLETE")
            print("=" * 60)
            print(f"Iterations completed: {iteration}/{max_iterations}")
            print(f"\n📁 AI Handover: {handover_path}")
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
                print("   1. Run 'excelsior plan <rule_id>' for guided fix instructions")
                print("   2. Run 'excelsior fix' again or fix manually")
                print("   3. Re-run 'excelsior check' to verify")
            else:
                print("   ✅ No violations found! Codebase is clean.")
            print("=" * 60 + "\n")
            if final_audit_result.has_violations():
                sys.exit(1)
            sys.exit(0)

        def _run_generate_guidance(
            output_dir: str = "docs",
            append_cursorrules: bool = False,
        ) -> None:
            """Generate docs/GENERATION_GUIDANCE.md from the rule registry."""
            entries = deps.guidance_service.iter_proactive_guidance()
            lines = [
                "# Generation Guidance: Write Code That Passes Excelsior",
                "",
                "When **writing or editing Python** in this repo, follow these patterns so Excelsior (and ruff, import-linter, mypy, pylint) find fewer violations. This is **proactive** guidance—use it during generation, not only when fixing after a failed check.",
                "",
                "This file is generated by `excelsior init --guidance-only`. The canonical registry is in the package: `infrastructure/resources/rule_registry.yaml` keyed by `{linter}.{rule_code}`.",
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
            current_linter: str | None = None
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
            if append_cursorrules:
                cursorrules = Path(".cursorrules")
                if cursorrules.exists():
                    section = "\n\n## Excelsior proactive guidance\n\nWhen editing Python, follow docs/GENERATION_GUIDANCE.md (or run `excelsior init --guidance-only` to refresh it).\n"
                    with cursorrules.open("a", encoding="utf-8") as f:
                        f.write(section)
                    deps.telemetry.step(
                        "Appended Excelsior section to .cursorrules")
                else:
                    deps.telemetry.step(
                        ".cursorrules not found; skipped (editor-agnostic).")
            print(f"Generated: {out_path}")

        @app.command(name="init")
        def init_clean_arch(
            template: str | None = typer.Option(
                None, "--template", help="Pre-configure for frameworks"),
            check_layers: bool = typer.Option(
                False, "--check-layers", help="Verify active layer configuration"),
            guidance_only: bool = typer.Option(
                False, "--guidance-only", help="Regenerate guidance docs only (no scaffold)"),
            skip_guidance: bool = typer.Option(
                False, "--skip-guidance", help="Skip guidance generation during scaffold"),
            cursorrules: bool = typer.Option(
                False, "--cursorrules", help="Also append to .cursorrules when generating guidance"),
        ) -> None:
            """Initialize configuration and optionally generate preventative guidance docs."""
            _session_start()
            if guidance_only:
                _run_generate_guidance(output_dir="docs", append_cursorrules=cursorrules)
                return
            use_case = InitProjectUseCase(deps.scaffolder, deps.telemetry)
            use_case.execute(template=template, check_layers=check_layers)
            if not skip_guidance:
                _run_generate_guidance(output_dir="docs", append_cursorrules=cursorrules)

        @app.command(name="plan")
        def plan_cmd(
            topic: str | None = typer.Argument(
                None,
                help="Rule code (e.g. W9015, W9004), pattern name (adapter, facade), 'scoring', or omit to list topics."),
            violation_index: int = typer.Option(
                0, "--violation-index", "-n", help="Which occurrence (0-based) for fix plan"),
            source: str = typer.Option(
                "health", "--source", "-s", help="Handover source: health, check, or fix"),
            explain_only: bool = typer.Option(
                False, "--explain", "-e", help="Show explanation only, skip fix plan"),
        ) -> None:
            """Explain a rule/pattern/scoring or generate a fix plan from handover. No topic = list topics."""
            _session_start()
            from excelsior_architect.domain.patterns import PATTERN_GLOSSARY

            if topic is None or topic == "" or not topic.strip():
                deps.telemetry.step(
                    "Topics: rules (e.g. W9004, W9015), patterns (adapter, facade, strategy), scoring")
                deps.telemetry.step(
                    "  excelsior plan W9004   — explain and/or fix plan for Forbidden I/O rule")
                deps.telemetry.step(
                    "  excelsior plan facade  — explain Facade pattern")
                deps.telemetry.step(
                    "  excelsior plan scoring — explain priority score formula")
                handover_key = None
                for candidate in ("check/ai_handover.json", "health/ai_handover.json"):
                    if deps.artifact_storage.exists(candidate):
                        handover_key = candidate
                        break
                if handover_key:
                    content = deps.artifact_storage.read_artifact(handover_key)
                    handover = json.loads(content)
                    rule_ids = handover.get("rule_ids") or []
                    if rule_ids:
                        deps.telemetry.step(
                            "Pass a rule_id to generate a fix plan. Rule IDs from your last run:")
                        deps.telemetry.step("  " + ", ".join(rule_ids[:20]) + (" ..." if len(rule_ids) > 20 else ""))
                        deps.telemetry.step(
                            "  Example: excelsior plan W9004")
                    else:
                        deps.telemetry.step(
                            "Run 'excelsior check' first to generate fix plans for violations.")
                else:
                    deps.telemetry.step(
                        "Run 'excelsior check' first to generate fix plans for violations.")
                return
            key = topic.strip().lower()
            # Pattern glossary
            if key in PATTERN_GLOSSARY:
                p = PATTERN_GLOSSARY[key]
                deps.telemetry.step(f"# {p.name}")
                deps.telemetry.step(f"ELI5: {p.eli5}")
                deps.telemetry.step(f"Description: {p.description}")
                deps.telemetry.step(f"When to use: {p.when_to_use}")
                deps.telemetry.step(f"Before: {p.before_example}")
                deps.telemetry.step(f"After: {p.after_example}")
                deps.telemetry.step(f"References: {', '.join(p.references)}")
                return
            # Scoring
            if key == "scoring":
                deps.telemetry.step(
                    "Priority score = (reach × impact × confidence) / (effort + 0.1)")
                deps.telemetry.step(
                    "  reach: 0–100, % of project files affected")
                deps.telemetry.step(
                    "  impact: 1–10, rule weight from registry")
                deps.telemetry.step(
                    "  confidence: 0–1, true-positive likelihood")
                deps.telemetry.step(
                    "  effort: 1–5, fix effort (1=auto, 5=architectural)")
                deps.telemetry.step("Higher score = fix first.")
                return
            # Rule from registry (strip excelsior. prefix if present)
            rule_code = key.replace("excelsior.", "")
            entry = deps.guidance_service.get_excelsior_entry(rule_code)
            if entry:
                deps.telemetry.step(
                    f"# {entry.get('display_name', rule_code)}")
                if entry.get("short_description"):
                    deps.telemetry.step(
                        f"Summary: {entry['short_description']}")
                if entry.get("eli5_description"):
                    deps.telemetry.step(
                        f"Why it matters: {entry['eli5_description']}")
                if entry.get("manual_instructions"):
                    deps.telemetry.step(
                        f"How to fix: {entry['manual_instructions']}")
                if entry.get("proactive_guidance"):
                    deps.telemetry.step(
                        f"Proactive: {entry['proactive_guidance']}")
                if entry.get("references"):
                    deps.telemetry.step(
                        f"References: {', '.join(entry['references'])}")
                if explain_only:
                    return
                rule_id = rule_code if rule_code.startswith("excelsior.") else f"excelsior.{rule_code}"
                handover_key = f"{source}/ai_handover.json" if source else "ai_handover.json"
                if not deps.artifact_storage.exists(handover_key):
                    deps.telemetry.step(
                        f"No handover at {handover_key}. Run 'excelsior check' first to generate fix plans.")
                    return
                content = deps.artifact_storage.read_artifact(handover_key)
                handover = json.loads(content)
                violations_by_rule = handover.get("violations_by_rule") or {}
                matching = [
                    ent
                    for entries in violations_by_rule.values()
                    for ent in entries
                    if ent.get("rule_id") == rule_id
                ]
                if not matching:
                    deps.telemetry.step(
                        f"No violation for rule_id '{rule_id}' in {handover_key}. Run 'excelsior check' and fix a violation first.")
                    return
                if violation_index < 0 or violation_index >= len(matching):
                    print(
                        f"Error: violation_index {violation_index} out of range (0..{len(matching) - 1}) "
                        f"for rule_id '{rule_id}' ({len(matching)} occurrence(s)).",
                        file=sys.stderr,
                    )
                    sys.exit(1)
                violation = matching[violation_index]
                plan_use_case = PlanFixUseCase(
                    artifact_storage=deps.artifact_storage,
                    guidance_service=deps.guidance_service,
                )
                out_key = plan_use_case.write_fix_plan(
                    rule_id=rule_id, violation=violation)
                deps.telemetry.step(f"Wrote fix plan: {out_key}")
                print(f"Fix plan: .excelsior/{out_key}")
                return
            deps.telemetry.step(
                f"Unknown topic: {topic}. Use 'excelsior plan' to list topics.")

        @app.command()
        def verify(
            path: Path | None = typer.Argument(None, help="Path to verify (default: current directory)"),
            baseline: bool = typer.Option(
                False, "--baseline", help="Save current check+health as baseline to .excelsior/verify/baseline.json",
            ),
        ) -> None:
            """Re-run check and diff against a saved baseline (score and finding counts)."""
            _session_start()
            target_path = CLIAppFactory.resolve_target_path(path)
            check_audit_use_case = CheckAuditUseCase(
                mypy_adapter=deps.mypy_adapter,
                excelsior_adapter=deps.excelsior_adapter,
                import_linter_adapter=deps.import_linter_adapter,
                ruff_adapter=deps.ruff_adapter,
                telemetry=deps.telemetry,
                config_loader=deps.config_loader,
            )
            audit_result = check_audit_use_case.execute(target_path)
            total = (
                len(audit_result.ruff_results)
                + len(audit_result.mypy_results)
                + len(audit_result.excelsior_results)
                + len(audit_result.import_linter_results)
            )
            health_use_case = AnalyzeHealthUseCase(
                config_loader=deps.config_loader,
                clusterer=ViolationClusterer(deps.guidance_service),
                scorer=HealthScorer(),
                decision_tree=DesignPatternDecisionTree(),
            )
            health_report = health_use_case.execute(audit_result)
            score = getattr(health_report, "health_score", None) or getattr(
                health_report, "score", None
            )
            if score is None and hasattr(health_report, "summary"):
                summary = health_report.summary
                score = getattr(summary, "health_score", None) if hasattr(summary, "health_score") else None
            current_blueprint = {
                "total_violations": total,
                "health_score": float(score) if score is not None else None,
                "excelsior_count": len(audit_result.excelsior_results),
                "ruff_count": len(audit_result.ruff_results),
                "mypy_count": len(audit_result.mypy_results),
                "import_linter_count": len(audit_result.import_linter_results),
            }
            verify_dir = Path.cwd() / ".excelsior" / "verify"
            baseline_path = verify_dir / "baseline.json"
            if baseline:
                verify_dir.mkdir(parents=True, exist_ok=True)
                with open(baseline_path, "w") as f:
                    json.dump(current_blueprint, f, indent=2)
                deps.telemetry.step(f"Baseline saved: {baseline_path}")
                print(f"Baseline: {baseline_path} (total_violations={total})")
                sys.exit(0)
            if not baseline_path.exists():
                print(
                    "No baseline found. Run 'excelsior verify --baseline' first.",
                    file=sys.stderr,
                )
                sys.exit(1)
            with open(baseline_path) as f:
                saved = json.load(f)
            prev_total = saved.get("total_violations", 0)
            prev_score = saved.get("health_score")
            delta = total - prev_total
            deps.telemetry.step("Comparing to baseline...")
            print("\n--- Verify (before vs after) ---")
            print(f"  total_violations: {prev_total} -> {total} (delta: {delta:+d})")
            if prev_score is not None and current_blueprint.get("health_score") is not None:
                print(f"  health_score:     {prev_score} -> {current_blueprint['health_score']}")
            print("--------------------------------\n")
            if delta > 0:
                sys.exit(1)
            sys.exit(0)

        return app
