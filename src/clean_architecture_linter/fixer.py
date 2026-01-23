"""Auto-fixers for Excelsior violations."""

import re
import os
from pathlib import Path
from typing import TYPE_CHECKING, List, Dict, Optional, Any, Set
import json

if TYPE_CHECKING:
    from stellar_ui_kit import TelemetryPort

def excelsior_fix(telemetry: "TelemetryPort", target_path: str) -> None:
    """Run auto-fixers on the target path."""
    telemetry.step(f"🔧 Starting Excelsior Auto-Fix Suite: {target_path}")

    path = Path(target_path).resolve()
    cwd = Path.cwd()

    # 0. Load Audit Trail if exists to guide Stage 3
    audit_data = _load_audit_trail()
    ambiguous_violations = []

    # 1. Structural Fixes (py.typed, __init__.py)
    _fix_structural_integrity(telemetry, path, cwd)

    # 2. Source Code Fixes
    files = list(path.glob("**/*.py")) if path.is_dir() else [path]
    modified_files: int = 0

    for file_path in files:
        if file_path.suffix != ".py":
            continue

        with open(file_path, "r", encoding = "utf-8") as f:
            content = f.read()

        new_content = content

        # Apply fixers
        new_content = _fix_init_return_type(new_content)
        new_content = _fix_deterministic_type_hints(new_content)
        new_content = _fix_domain_immutability(file_path, new_content)
        new_content = _fix_type_integrity(new_content)
        new_content = _fix_no_redef(new_content)

        if new_content != content:
            with open(file_path, "w", encoding = "utf-8") as f:
                f.write(new_content)
            try:
                rel_path = file_path.relative_to(cwd)
            except ValueError:
                rel_path = file_path
            telemetry.step(f"✅ Auto-repaired: {rel_path}")
            modified_files += 1

    # 3. Generate Fix Manifest (Stage 3)
    _generate_fix_manifest(telemetry, audit_data)

    telemetry.step(f"🛠️ Fix Suite complete. Files repaired: {modified_files}")

def _fix_structural_integrity(telemetry: "TelemetryPort", path: Path, cwd: Path) -> None:
    """Ensure py.typed and __init__.py exist where needed."""
    if not path.is_dir():
        return

    # Check for py.typed in the main package
    package_root = _find_package_root(path)
    if package_root:
        py_typed = package_root / "py.typed"
        if not py_typed.exists():
            py_typed.touch()
            try:
                rel_path = py_typed.relative_to(cwd)
            except ValueError:
                rel_path = py_typed
            telemetry.step(f"🎁 Generated missing type marker: {rel_path}")

    # Check for missing __init__.py in subdirectories (Deep Structure / W9011)
    for root, dirs, _ in os.walk(path):
        root_path = Path(root)
        if any(p.startswith(".") for p in root_path.parts):
            continue

        # If it has .py files, it should probably be a package
        if any(f.suffix == ".py" for f in root_path.iterdir()):
            init_file = root_path / "__init__.py"
            if not init_file.exists():
                init_file.touch()
                try:
                    rel_path = init_file.relative_to(cwd)
                except ValueError:
                    rel_path = init_file
                telemetry.step(f"📦 Initialized missing package: {rel_path}")

def _find_package_root(path: Path) -> Optional[Path]:
    """Find the top-most directory containing an __init__.py."""
    if (path / "__init__.py").exists():
        return path
    for child in path.iterdir():
        if child.is_dir() and (child / "__init__.py").exists():
            return child
    return None

def _fix_init_return_type(content: str) -> str:
    """Add '-> None' to __init__ methods missing it."""
    # Matches: def __init__(self, ...) -> None: but not def __init__(self, ...) -> None:
    # Use a negative lookahead to avoid double-adding
    pattern = r"def __init__\(([^)]*)\)(?!\s*->\s*[^:]+):"
    replacement = r"def __init__(\1) -> None:"
    return re.sub(pattern, replacement, content)

def _fix_domain_immutability(file_path: Path, content: str) -> str:
    """Enforce frozen: bool = True on dataclasses in the domain layer."""
    if "domain" not in str(file_path).lower():
        return content

    # Matches @dataclass but not @dataclass(frozen=True)
    pattern = r"@dataclass(\s*\(.*?\))?"

    def replace_dataclass(match: re.Match[str]) -> str:
        args = match.group(1)
        if not args:
            return "@dataclass(frozen=True)"
        if "frozen" in args:
            return match.group(0) # Already handled

        # Insert frozen: bool = True into existing args
        if "(" in args and ")" in args:
            inner = args.strip().strip("()")
            if inner:
                return f"@dataclass({inner}, frozen=True)"
            return "@dataclass(frozen=True)"
        return "@dataclass(frozen=True)"

    return re.sub(pattern, replace_dataclass, content)

def _fix_type_integrity(content: str) -> str:
    """Auto-import common missing typing utilities."""
    # This is a simple opportunistic fixer.
    # If Any/Optional is used in hints but not imported from typing.
    # Matches : Type or -> Type
    hints_found = set(re.findall(r"(?:->|:)\s*(Optional|Any|List|Dict|Union|Iterable|Callable)", content))
    if not hints_found:
        return content

    typing_import_match = re.search(r"from typing import (.*)", content)
    if typing_import_match:
        current_imports = set(i.strip() for i in typing_import_match.group(1).split(","))
        missing = hints_found - current_imports
        if missing:
            new_imports = sorted(list(current_imports | missing))
            return content.replace(typing_import_match.group(0), f"from typing import {', '.join(new_imports)}")
    else:
        # Insert after docstring if it exists, otherwise at top
        docstring_match = re.match(r'(""".*?""")\s*', content, re.DOTALL)
        typing_line = f"from typing import {', '.join(sorted(list(hints_found)))}\n"
        if docstring_match:
            return docstring_match.group(0) + "\n" + typing_line + content[docstring_match.end():]
        return typing_line + "\n" + content

    return content

def _fix_no_redef(content: str) -> str:
    """Remove redundant type annotations that cause no-redef errors."""
    return content.replace("normalized_path: str = ", "normalized_path = ")

def _fix_deterministic_type_hints(content: str) -> str:
    """Stage 1: Auto-fix deterministic type hints (literals)."""
    # Stage 1: Var assignments (anchored to start of line or indentation)
    content = re.sub(r'(?m)^(\s*)(\w+)\s*=\s*"([^"]*)"(?!\s*:)', r'\1\2: str = "\3"', content)
    content = re.sub(r"(?m)^(\s*)(\w+)\s*=\s*'([^']*)'(?!\s*:)", r"\1\2: str = '\3'", content)
    content = re.sub(r"(?m)^(\s*)(\w+)\s*=\s*(\d+)(?!\s*:)", r"\1\2: int = \3", content)
    content = re.sub(r"(?m)^(\s*)(\w+)\s*=\s*(True|False)(?!\s*:)", r"\1\2: bool = \3", content)

    # Stage 1: Function parameters with defaults
    # Matches: def name(..., param=literal, ...)
    def fix_fn_params(match: re.Match[str]) -> str:
        prefix = match.group(1) # def func
        params = match.group(2) # name: str = "bob", age = 30
        suffix = match.group(3) # ): or ) -> None:

        new_params = []
        for p in params.split(","):
            p_strip = p.strip()
            if "=" in p_strip and ":" not in p_strip:
                name_val = p_strip.split("=", 1)
                name = name_val[0].strip()
                val = name_val[1].strip()
                if val.startswith(('"', "'")):
                    new_params.append(f"{name}: str = {val}")
                elif val.isdigit():
                    new_params.append(f"{name}: int = {val}")
                elif val in ("True", "False"):
                    new_params.append(f"{name}: bool = {val}")
                else:
                    new_params.append(p_strip)
            else:
                new_params.append(p_strip)
        return f"{prefix}({', '.join(new_params)}){suffix}"

    # Match def function_name(params)[: \n]
    content = re.sub(r"(def\s+\w+\s*)\((.*?)\)(\s*[:\-])", fix_fn_params, content, flags=re.DOTALL)

    return content

def _generate_fix_manifest(telemetry: "TelemetryPort", audit_data: Optional[Dict[str, Any]]) -> None:
    """Stage 3: Record ambiguous violations in a fix manifest."""
    if not audit_data:
        return

    manifest_path = Path(".excelsior/fix_manifest.md")
    lines = ["# 🛡️ Excelsior Fix Manifest", "", "The following violations require manual review or AI-assisted resolution.", ""]

    def strip_ansi(text: str) -> str:
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_escape.sub('', text)

    found_ambiguous: bool = False
    for category, violations in audit_data.get("violations", {}).items():
        if not violations:
            continue

        lines.append(f"## {category.replace('_', ' ').title()}")
        for v in violations:
            found_ambiguous: bool = True
            lines.append(f"### ❓ {strip_ansi(v['code'])}")
            lines.append(f"- **Message**: {strip_ansi(v['message'])}")

            locations = v.get("locations", [])
            if not locations and "location" in v and v["location"] != "N/A":
                # Fallback to string-based parsing if list is missing
                locations = [loc.strip() for loc in v["location"].split(",") if loc.strip()]

            if locations:
                lines.append("- **Locations**:")
                for loc in locations:
                    lines.append(f"  - `{strip_ansi(loc)}`")
            lines.append("")

    if not found_ambiguous:
        return

    with open(manifest_path, "w", encoding = "utf-8") as f:
        f.write("\n".join(lines))

    telemetry.step(f"📝 Fix Manifest generated: {manifest_path}")

def _load_audit_trail() -> Optional[Dict[str, Any]]:
    """Load the latest audit trail from .excelsior/last_audit.json."""
    path = Path(".excelsior/last_audit.json")
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding = "utf-8") as f:
            return json.load(f)
    except Exception:
        return None
