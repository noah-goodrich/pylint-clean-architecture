"""CLI entry points for Excelsior."""

import argparse
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional

from stellar_ui_kit import ColumnDefinition, ReportSchema, TerminalReporter

from clean_architecture_linter.config import ConfigurationLoader
from clean_architecture_linter.constants import EXCELSIOR_BANNER
from clean_architecture_linter.di.container import ExcelsiorContainer
from clean_architecture_linter.infrastructure.adapters.linter_adapters import (
    ExcelsiorAdapter,
    ImportLinterAdapter,
    MypyAdapter,
)
from clean_architecture_linter.infrastructure.adapters.ruff_adapter import RuffAdapter
from clean_architecture_linter.infrastructure.gateways.libcst_fixer_gateway import LibCSTFixerGateway
from clean_architecture_linter.infrastructure.services.scaffolder import Scaffolder
from clean_architecture_linter.use_cases.apply_fixes import ApplyFixesUseCase

if TYPE_CHECKING:
    from stellar_ui_kit import TelemetryPort

    from clean_architecture_linter.domain.entities import LinterResult


def _gather_linter_results(
    telemetry: "TelemetryPort", target_path: str, linter: str
) -> tuple[List["LinterResult"], List["LinterResult"], List["LinterResult"], List["LinterResult"]]:
    """Run requested linters and return (mypy, excelsior, il, ruff) result lists."""
    mypy_results: List["LinterResult"] = []
    excelsior_results: List["LinterResult"] = []
    il_results: List["LinterResult"] = []
    ruff_results: List["LinterResult"] = []

    if linter in ["all", "mypy"]:
        telemetry.step("Gathering Type Integrity violations (Source: Mypy)...")
        mypy_results = MypyAdapter().gather_results(target_path)
    if linter in ["all", "excelsior"]:
        telemetry.step("Gathering Architectural violations (Source: Pylint/Excelsior)...")
        excelsior_results = ExcelsiorAdapter().gather_results(target_path)
    if linter in ["all", "import-linter"]:
        telemetry.step("Verifying Package Contracts (Source: Import-Linter)...")
        il_results = ImportLinterAdapter().gather_results(target_path)

    config_loader = ConfigurationLoader()
    if linter in ["all", "ruff"] and config_loader.ruff_enabled:
        telemetry.step("Running Code Quality Checks (Source: Ruff)...")
        ruff_results = RuffAdapter(telemetry=telemetry).gather_results(target_path)

    return (mypy_results, excelsior_results, il_results, ruff_results)


def _is_rule_fixable(adapter: object, code: str) -> bool:
    """True if the adapter can auto-fix this rule code. Ruff uses prefix match."""
    if not hasattr(adapter, "supports_autofix") or not adapter.supports_autofix():
        return False
    fixable = getattr(adapter, "get_fixable_rules", lambda: [])()
    if adapter.__class__.__name__ == "RuffAdapter":
        return any(code.startswith(r) for r in fixable)
    return code in fixable


def _process_results(
    results: List["LinterResult"],
    adapter: object,
) -> List[Dict[str, object]]:
    """Build table rows with count and fixability."""
    out = []
    for r in results:
        d: Dict[str, object] = dict(r.to_dict())
        d["count"] = len(r.locations) if r.locations else 1
        d["fix"] = "✅ Auto" if _is_rule_fixable(adapter, r.code) else "⚠️ Manual"
        out.append(d)
    return sorted(
        out,
        key=lambda x: int(x["count"]) if isinstance(x["count"], int) else 0,
        reverse=True,
    )


def _print_audit_tables(
    mypy_results: List["LinterResult"],
    excelsior_results: List["LinterResult"],
    il_results: List["LinterResult"],
    ruff_results: List["LinterResult"],
    ruff_enabled: bool,
) -> None:
    """Print Mypy, Excelsior, Import-Linter, and Ruff report tables."""
    mypy_adapter = MypyAdapter()
    excelsior_adapter = ExcelsiorAdapter()
    ruff_adapter = RuffAdapter(telemetry=None) if ruff_enabled else None

    reporter = TerminalReporter()

    mypy_schema = ReportSchema(
        title="[MYPY] Type Integrity Audit",
        columns=[
            ColumnDefinition(header="Error Code", key="code", style="#00EEFF"),
            ColumnDefinition(header="Count", key="count", style="bold #007BFF"),
            ColumnDefinition(header="Fix?", key="fix"),
            ColumnDefinition(header="Message", key="message"),
        ],
        header_style="bold #007BFF",
    )
    if mypy_results:
        reporter.generate_report(_process_results(mypy_results, mypy_adapter), mypy_schema)
    else:
        print("\n✅ No Type Integrity violations detected.")

    excelsior_schema = ReportSchema(
        title="[EXCELSIOR] Architectural Governance Audit",
        columns=[
            ColumnDefinition(header="Rule ID", key="code", style="#C41E3A"),
            ColumnDefinition(header="Count", key="count", style="bold #007BFF"),
            ColumnDefinition(header="Fix?", key="fix"),
            ColumnDefinition(header="Violation Description", key="message"),
        ],
        header_style="bold #F9A602",
    )
    if excelsior_results:
        reporter.generate_report(
            _process_results(excelsior_results, excelsior_adapter),
            excelsior_schema,
        )
    else:
        print("\n✅ No Architectural violations detected.")

    il_schema = ReportSchema(
        title="[IMPORT-LINTER] Package Boundary Audit",
        columns=[
            ColumnDefinition(header="Rule ID", key="code", style="#7B68EE"),
            ColumnDefinition(header="Fix?", key="fix"),
            ColumnDefinition(header="Contract Violation", key="message"),
        ],
        header_style="bold #7B68EE",
    )
    if il_results:
        il_rows = []
        for r in il_results:
            d = dict(r.to_dict())
            d["fix"] = "⚠️ Manual"  # Import-Linter has no autofix
            il_rows.append(d)
        reporter.generate_report(il_rows, il_schema)

    if ruff_enabled and ruff_adapter:
        ruff_schema = ReportSchema(
            title="[RUFF] Code Quality Audit",
            columns=[
                ColumnDefinition(header="Rule ID", key="code", style="#FFA500"),
                ColumnDefinition(header="Count", key="count", style="bold #007BFF"),
                ColumnDefinition(header="Fix?", key="fix"),
                ColumnDefinition(header="Issue", key="message"),
            ],
            header_style="bold #FFA500",
        )
        if ruff_results:
            reporter.generate_report(
                _process_results(ruff_results, ruff_adapter),
                ruff_schema,
            )
        else:
            print("\n✅ No Code Quality violations detected.")


def check_command(telemetry: "TelemetryPort", target_path: str, linter: str = "all") -> bool:
    """Run standardized linter audit with grouped counts and desc sorting."""
    telemetry.step(f"Starting Excelsior Audit for: {target_path} (linter={linter})")

    mypy_results, excelsior_results, il_results, ruff_results = _gather_linter_results(
        telemetry, target_path, linter
    )
    config_loader = ConfigurationLoader()
    _print_audit_tables(
        mypy_results,
        excelsior_results,
        il_results,
        ruff_results,
        ruff_enabled=config_loader.ruff_enabled,
    )
    _save_audit_trail(telemetry, mypy_results, excelsior_results, il_results, ruff_results)

    telemetry.step("AI Agent Handover initialized.")
    print("\n" + "=" * 40)
    print("🤖 EXCELSIOR v2: AI HANDOVER")
    print("=" * 40)
    print("System Integrity Report completed.")
    print("Audit Log: .excelsior/last_audit.json")
    print("Run 'excelsior fix' to resolve common issues.")
    print("=" * 40 + "\n")

    has_violations = bool(
        mypy_results or excelsior_results or il_results or ruff_results
    )
    return not has_violations


def _write_violations_section(
    f,
    title: str,
    results: List["LinterResult"],
    adapter: object,
    include_locations: bool = True,
) -> None:
    """Write a violations section to an audit txt file. Adds fixability and manual fix guidance."""
    f.write(f"\n--- {title} ---\n")
    for r in results:
        fixable = _is_rule_fixable(adapter, r.code)
        f.write(f"[{r.code}] {'✅ Auto-fixable' if fixable else '⚠️ Manual fix required'}\n")
        f.write(f"  {r.message}\n")
        if include_locations and r.locations:
            for loc in r.locations:
                f.write(f"  - {loc}\n")
        if not fixable and adapter and hasattr(adapter, "get_manual_fix_instructions"):
            instr = adapter.get_manual_fix_instructions(r.code)
            f.write(f"  How to fix (juniors & AI): {instr}\n")


def _violations_with_fix_info(
    results: List["LinterResult"],
    adapter: object,
) -> List[Dict[str, object]]:
    """Enrich violation dicts with fixable and manual_instructions for JSON audit."""
    out = []
    for r in results:
        d = dict(r.to_dict())
        fixable = _is_rule_fixable(adapter, r.code)
        d["fixable"] = fixable
        if not fixable and hasattr(adapter, "get_manual_fix_instructions"):
            d["manual_instructions"] = adapter.get_manual_fix_instructions(r.code)
        else:
            d["manual_instructions"] = None
        out.append(d)
    return out


def _save_audit_trail(
    telemetry: "TelemetryPort",
    mypy: List["LinterResult"],
    excelsior: List["LinterResult"],
    il: List["LinterResult"],
    ruff: Optional[List["LinterResult"]] = None,
) -> None:
    """Save results to .excelsior directory for human/AI review."""
    ruff = ruff or []
    excelsior_dir = Path(".excelsior")
    excelsior_dir.mkdir(exist_ok=True)

    mypy_adapter = MypyAdapter()
    excelsior_adapter = ExcelsiorAdapter()
    il_adapter = ImportLinterAdapter()
    ruff_adapter = RuffAdapter(telemetry=None) if ruff else None

    audit_data = {
        "version": "2.0.0",
        "timestamp": str(excelsior_dir.stat().st_mtime),
        "summary": {
            "type_integrity": len(mypy),
            "architectural": len(excelsior),
            "contracts": len(il),
            "code_quality": len(ruff),
        },
        "violations": {
            "type_integrity": _violations_with_fix_info(mypy, mypy_adapter),
            "architectural": _violations_with_fix_info(excelsior, excelsior_adapter),
            "contracts": _violations_with_fix_info(il, il_adapter),
            "code_quality": _violations_with_fix_info(ruff, ruff_adapter) if ruff_adapter else [],
        },
    }

    json_path = excelsior_dir / "last_audit.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(audit_data, f, indent=2)

    txt_path = excelsior_dir / "last_audit.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("=== EXCELSIOR v2 AUDIT LOG ===\n")
        f.write(
            f"Summary: {len(excelsior)} Architectural, {len(mypy)} Type Integrity, "
            f"{len(il)} Contracts, {len(ruff)} Code Quality\n"
        )
        _write_violations_section(f, "ARCHITECTURAL VIOLATIONS", excelsior, excelsior_adapter)
        _write_violations_section(f, "TYPE INTEGRITY VIOLATIONS", mypy, mypy_adapter)
        _write_violations_section(
            f, "CONTRACT VIOLATIONS", il, il_adapter, include_locations=False
        )
        if ruff_adapter:
            _write_violations_section(
                f, "CODE QUALITY VIOLATIONS (RUFF)", ruff, ruff_adapter
            )

    telemetry.step(f"💾 Audit Trail persisted to: {json_path} and {txt_path}")


def _build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description=f"{EXCELSIOR_BANNER}\nEXCELSIOR v2: Architectural Autopilot for Clean Architecture.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    check_parser = subparsers.add_parser("check", help="Run multi-tool audit")
    check_parser.add_argument("path", nargs="?", default=".", help="Target path to audit")
    check_parser.add_argument(
        "--linter",
        choices=["ruff", "mypy", "excelsior", "import-linter", "all"],
        default="all",
        help="Which linter to run (default: all)",
    )

    fix_parser = subparsers.add_parser("fix", help="Auto-fix common violations")
    fix_parser.add_argument("path", nargs="?", default=".", help="Target path to fix")
    fix_parser.add_argument(
        "--linter", choices=["ruff", "excelsior", "all"], default="all",
        help="Which linter to fix violations for (default: all)"
    )
    fix_parser.add_argument("--confirm", action="store_true", help="Require confirmation before each fix")
    fix_parser.add_argument("--no-backup", action="store_true", help="Skip creating .bak backup files")
    fix_parser.add_argument("--skip-tests", action="store_true", help="Skip pytest validation (faster but riskier)")
    fix_parser.add_argument("--cleanup-backups", action="store_true", help="Remove .bak files after successful fixes")
    fix_parser.add_argument("--manual-only", action="store_true", help="Show manual fix suggestions only")

    init_parser = subparsers.add_parser("init", help="Initialize configuration")
    init_parser.add_argument("--template", choices=["fastapi", "sqlalchemy"], help="Pre-configure for frameworks")
    init_parser.add_argument("--check-layers", action="store_true", help="Verify active layer configuration")

    return parser


def _run_check(telemetry: "TelemetryPort", args) -> None:
    if "-h" not in sys.argv and "--help" not in sys.argv:
        telemetry.handshake()
    ok = check_command(telemetry, args.path, args.linter)
    sys.exit(0 if ok else 1)


def _run_fix(telemetry: "TelemetryPort", args) -> None:
    if "-h" not in sys.argv and "--help" not in sys.argv:
        telemetry.handshake()
    if args.manual_only:
        _run_fix_manual_only(telemetry, args)
        return
    if args.linter == "ruff":
        _run_fix_ruff(telemetry, args)
        return
    _run_fix_excelsior(telemetry, args)


def _run_fix_manual_only(telemetry: "TelemetryPort", args) -> None:
    from clean_architecture_linter.infrastructure.adapters.linter_adapters import (
        ExcelsiorAdapter,
        ImportLinterAdapter,
        MypyAdapter,
    )
    from clean_architecture_linter.infrastructure.adapters.ruff_adapter import RuffAdapter

    all_adapters = [
        ("Ruff", RuffAdapter(telemetry), "ruff"),
        ("Mypy", MypyAdapter(), "excelsior"),
        ("Excelsior", ExcelsiorAdapter(), "excelsior"),
        ("Import-Linter", ImportLinterAdapter(), "excelsior"),
    ]
    if args.linter == "all":
        adapters = [(n, a) for n, a, _ in all_adapters]
        telemetry.step("📋 Gathering manual fix suggestions from all linters...")
    elif args.linter == "ruff":
        adapters = [(n, a) for n, a, lt in all_adapters if lt == "ruff"]
        telemetry.step("📋 Gathering manual fix suggestions from Ruff...")
    else:
        adapters = [(n, a) for n, a, lt in all_adapters if lt == "excelsior"]
        telemetry.step("📋 Gathering manual fix suggestions from Excelsior suite...")

    for linter_name, adapter in adapters:
        results = adapter.gather_results(args.path)
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
    sys.exit(0)


def _run_fix_ruff(telemetry: "TelemetryPort", args) -> None:
    from clean_architecture_linter.infrastructure.adapters.ruff_adapter import RuffAdapter

    telemetry.step("🔧 Applying Ruff fixes...")
    success = RuffAdapter(telemetry).apply_fixes(Path(args.path))
    telemetry.step("✅ Ruff fixes complete. Run 'excelsior check' to verify." if success else "❌ Ruff fixing failed")
    sys.exit(0 if success else 1)


def _run_fix_excelsior(telemetry: "TelemetryPort", args) -> None:
    telemetry.step(f"🔧 Applying Excelsior fixes (--linter {args.linter})...")
    use_case = ApplyFixesUseCase(
        LibCSTFixerGateway(),
        telemetry=telemetry,
        require_confirmation=args.confirm,
        create_backups=not args.no_backup,
        cleanup_backups=args.cleanup_backups,
        validate_with_tests=not args.skip_tests,
    )
    modified = use_case.execute([], args.path)
    telemetry.step(f"✅ Successfully fixed {modified} file(s)" if modified > 0 else "ℹ️  No fixes applied")
    sys.exit(0)


def _run_init(telemetry: "TelemetryPort", args) -> None:
    if "-h" not in sys.argv and "--help" not in sys.argv:
        telemetry.handshake()
    Scaffolder(telemetry).init_project(args.template, args.check_layers)


def main() -> None:
    """Main entry point."""
    container = ExcelsiorContainer()
    telemetry: "TelemetryPort" = container.get("TelemetryPort")
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "check":
        _run_check(telemetry, args)
    elif args.command == "fix":
        _run_fix(telemetry, args)
    elif args.command == "init":
        _run_init(telemetry, args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
