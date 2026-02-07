#!/usr/bin/env python3
"""Analyze coverage impact for filesystem-modifying code."""

import json
import sys
from pathlib import Path


def main() -> int:
    """Analyze and display priority test targets for filesystem-modifying code."""
    json_path = Path(".excelsior/coverage_impact.json")
    if not json_path.exists():
        print("❌ No coverage impact JSON found.")
        print("   Run: make coverage-impact")
        return 1

    with json_path.open() as f:
        data = json.load(f)

    # Filter for filesystem-modifying modules
    filesystem_modules = [
        "apply_fixes",
        "scaffolder",
        "filesystem_gateway",
        "libcst_fixer_gateway",
        "audit_trail",
        "transformers",
    ]

    filtered = []
    for func in data.get("functions", []):
        file_path = func.get("file", "")
        if any(module in file_path for module in filesystem_modules):
            filtered.append(func)

    # Sort by priority
    filtered.sort(key=lambda x: x.get("priority", 0), reverse=True)

    print("=" * 100)
    print("PRIORITY TEST TARGETS: Filesystem-Modifying Code")
    print("=" * 100)
    print()
    print(f"Found {len(filtered)} filesystem-modifying functions\n")
    print(
        f"{'Priority':<10} {'Score':<8} {'Coverage':<10} {'Impact':<8} {'Complexity':<12} {'File':<50} {'Function':<30}"
    )
    print("-" * 130)

    for func in filtered[:30]:
        priority = func.get("priority", 0)
        score = func.get("priority_score", 0)
        coverage = func.get("coverage_percentage", 0) * 100
        impact = func.get("impact", 0)
        complexity = func.get("complexity_score", 0)
        file_path = func.get("file", "")
        func_name = (
            func.get("function", "").split("::")[-1]
            if "::" in func.get("function", "")
            else func.get("function", "")
        )

        # Shorten file path
        if "excelsior_architect" in file_path:
            file_path = file_path.split("excelsior_architect/")[-1]

        print(
            f"{priority:<10.2f} {score:<8.2f} {coverage:<10.1f}% {impact:<8.1f} "
            f"{complexity:<12.2f} {file_path:<50} {func_name:<30}"
        )

    print()
    print("=" * 100)
    print("RECOMMENDATION: Focus on functions with:")
    print("  - High Priority Score (> 2.0)")
    print("  - Low Coverage (< 70%)")
    print("  - High Impact (frequently called)")
    print("  - Low-Medium Complexity (< 0.7)")
    print("=" * 100)

    return 0


if __name__ == "__main__":
    sys.exit(main())
