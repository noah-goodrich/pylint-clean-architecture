import os
import re
import subprocess
import sys
from collections import defaultdict

from clean_architecture_linter.domain.config import ConfigurationLoader
from clean_architecture_linter.domain.entities import LinterResult
from clean_architecture_linter.domain.protocols import LinterAdapterProtocol


class ExcelsiorAdapter(LinterAdapterProtocol):
    """Adapter for Pylint Clean Architecture output."""

    def gather_results(self, target_path: str) -> list[LinterResult]:
        """Run pylint with Clean Architecture and gather results."""
        env = os.environ.copy()
        env["PYTHONPATH"] = "src"
        try:
            # Build pylint command
            cmd = [
                    sys.executable,
                    "-m",
                    "pylint",
                    target_path,
                    "--load-plugins=clean_architecture_linter",
                    "--msg-template={path}:{line}: {msg_id}: {msg} ({symbol})",
            ]

            # Exclude deliberate-violation fixtures from the main audit
            exclude = ConfigurationLoader().audit_exclude_paths
            if exclude:
                regex = "|".join([rf".*{re.escape(p)}.*" for p in exclude])
                cmd.append(f"--ignore-paths={regex}")

            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            return self._parse_output(result.stdout)
        except Exception as e:
            # JUSTIFICATION: Error message wrapping requires explicit list creation.
            return [LinterResult("EXCELSIOR_ERROR", str(e), [])]

    def _parse_output(self, output: str) -> list[LinterResult]:
        # Structure: {msg_id: {"message": str, "locations": set}}
        collected: dict[str, dict[str, object]] = defaultdict(
            lambda: {"message": "", "locations": set()})
        # Pattern: path:line: msg_id: msg (symbol)
        pattern = re.compile(r"^(.*?):(\d+): (.*?): (.*)$")

        for line in output.splitlines():
            match = pattern.match(line)
            if match:
                # JUSTIFICATION: Regex match groups access is permitted for standard library utilities.
                file_path, line_num, msg_id, message = match.groups()
                location = f"{file_path}:{line_num}"

                # JUSTIFICATION: Type casting is necessary due to defaultdict(dict) structure.
                entry = collected[msg_id]
                entry["message"] = message
                # JUSTIFICATION: Type-safe access to the locations set.
                locations_set = entry["locations"]
                if isinstance(locations_set, set):
                    locations_set.add(location)

        results = []
        for msg_id, data in collected.items():
            # JUSTIFICATION: Converting set to sorted list for deterministic reporting.
            locations_set = data["locations"]
            sorted_locations = sorted(list(locations_set)) if isinstance(
                locations_set, set) else []
            results.append(LinterResult(msg_id, str(
                data["message"]), sorted_locations))

        return results

    def supports_autofix(self) -> bool:
        """Check if this linter supports automatic fixing."""
        return True  # Via LibCST fixes

    def get_fixable_rules(self) -> list[str]:
        """
        Return list of rule codes that can be auto-fixed (via LibCST transforms).

        Includes both structural fixes and comment-only fixes (governance comments).
        """
        return [
            # Structural auto-fixes
            "clean-arch-immutable",
            "clean-arch-lifecycle",
            "clean-arch-type-integrity",
            "missing-type-hint",  # Partially: lifecycle return, typing imports
            "W9015",
            "domain-immutability-violation",
            "W9601",
            # Comment-only fixes (governance comments)
            "W9006",  # Law of Demeter
            "clean-arch-demeter",
            "W9001",  # Illegal Dependency
            "clean-arch-dependency",
            "W9003",  # Protected Member Access
            "clean-arch-visibility",
            "W9004",  # Forbidden I/O
            "clean-arch-resources",
            "W9005",  # Delegation Anti-Pattern
            "clean-arch-delegation",
            "W9007",  # Naked Return
            "W9009",  # Missing Abstraction
            "W9010",  # God File
            "clean-arch-god-file",
            "W9011",  # Deep Structure
            "clean-arch-layer",
            "W9012",  # Defensive None Check
            "W9013",  # Illegal I/O Operation
            "W9201",  # Contract Integrity
            "contract-integrity-violation",
            "W9301",  # DI Violation
            "clean-arch-di",
            "W9016",  # Banned Any
            "banned-any-usage",
            "W9501",  # Anti-Bypass
            "clean-arch-bypass",
            "W9019",  # Unstable Dependency (create stub)
            "clean-arch-unstable-dep",
        ]

    def is_comment_only_rule(self, rule_code: str) -> bool:
        """
        Check if a rule uses comment-only fixes (governance comments).

        Returns:
            True if the rule injects governance comments rather than structural fixes
        """
        comment_only_rules = {
            "W9006", "clean-arch-demeter",
            "W9001", "clean-arch-dependency",
            "W9003", "clean-arch-visibility",
            "W9004", "clean-arch-resources",
            "W9005", "clean-arch-delegation",
            "W9007", "W9009",
            "W9010", "clean-arch-god-file",
            "W9011", "clean-arch-layer",
            "W9012", "W9013",
            "W9201", "contract-integrity-violation",
            "W9301", "clean-arch-di",
            "W9016", "banned-any-usage",
            "W9501", "clean-arch-bypass",
        }
        return rule_code in comment_only_rules

    def get_manual_fix_instructions(self, rule_code: str) -> str:
        """Readable, step-by-step guidance for juniors and AI. Covers all reported rules."""
        manual_instructions = {
            "clean-arch-resources": (
                "Move I/O (e.g. import astroid, file access) out of Domain/UseCase. "
                "Create a Domain protocol (interface) and implement it in Infrastructure. "
                "Inject the implementation via constructor."
            ),
            "clean-arch-demeter": (
                "Manual architectural change required. Extract this chain into a delegated method "
                "on the immediate dependency to preserve encapsulation. Do not use temporary variables "
                "as a workaround - this is a linter cheat that bypasses the architectural issue."
            ),
            "W9006": (
                "Manual architectural change required. Extract this chain into a delegated method "
                "on the immediate dependency to preserve encapsulation. Do not use temporary variables "
                "as a workaround - this is a linter cheat that bypasses the architectural issue."
            ),
            "contract-integrity-violation": (
                "Class in Infrastructure must implement a Domain protocol. "
                "Define a Protocol in the domain layer, then make the class inherit it."
            ),
            "missing-type-hint": (
                "Add type hints to the reported element. Examples: "
                "def f(x: int) -> str: ...; __init__(self) -> None: ...; "
                "Use typing.List, Dict, Optional etc. where needed."
            ),
            "W9015": (
                "Add explicit type hints to all parameters and return type. "
                "See .agent/instructions.md and RULES.md for examples."
            ),
            "clean-arch-dependency": (
                "Infrastructure must not be imported by Interface (or similar). "
                "Invert: define a Port/Protocol in Domain, implement in Infrastructure, "
                "inject into Interface."
            ),
            "domain-immutability-violation": (
                "Domain entities must be immutable. Use @dataclass(frozen=True) or "
                "namedtuple. Avoid attribute assignment outside __init__."
            ),
            "W9601": (
                "Use @dataclass(frozen=True) or namedtuple for Domain types. "
                "Run 'excelsior fix' for auto-freeze where applicable."
            ),
            "banned-any-usage": (
                "Replace 'Any' with a concrete type (e.g. astroid.nodes.NodeNG, "
                "or a Domain entity). Add proper type hints."
            ),
            "W9016": (
                "Avoid 'Any'. Use specific types from typing or your domain. "
                "See banned-any-usage."
            ),
            "clean-arch-visibility": (
                "Do not access protected members (_name) from outer layers. "
                "Expose a public API (use case or interface) instead."
            ),
            "W9003": (
                "Access to protected member. Use public interface or add a use case."
            ),
            "clean-arch-delegation": (
                "Refactor to Strategy/Handler pattern or use a map lookup. "
                "Avoid deep delegation chains."
            ),
            "W9005": (
                "Delegation anti-pattern. Use Strategy, Handler, or dict-based dispatch."
            ),
            "clean-arch-god-file": (
                "Split the file: extract cohesive parts into separate modules. "
                "Aim for single responsibility per file."
            ),
            "W9010": (
                "God file detected. Split into smaller modules by responsibility."
            ),
            "clean-arch-layer": (
                "Move file to the correct layer directory (domain, use_case, "
                "interface, infrastructure) based on dependencies and responsibility."
            ),
            "clean-arch-import": (
                "Remove the violating import. Domain cannot import Infrastructure. "
                "Use dependency inversion (Protocol in Domain, impl in Infra)."
            ),
            "clean-arch-di": (
                "Use constructor injection. Pass dependencies in __init__; "
                "do not instantiate Infrastructure inside UseCase."
            ),
            "clean-arch-bypass": (
                "Remove bypass comments. Fix the underlying violation instead of suppressing."
            ),
            "clean-arch-protected": (
                "Make the attribute private (_name) or expose via @property."
            ),
            "clean-arch-folder-structure": (
                "Adjust folder layout to match Clean Architecture layers. "
                "See .agent/instructions.md."
            ),
            "F0002": (
                "Pylint/astroid crash. Ensure types passed to inference (e.g. qname) "
                "are strings. Report reproducible cases to the plugin repo."
            ),
            "W9019": (
                "Create stubs/<module>.pyi for the external dependency so the linter "
                "can resolve types. Example: stubs/snowflake/connector.pyi for snowflake.connector."
            ),
            "clean-arch-unstable-dep": (
                "Create stubs/<module>.pyi for the external dependency so the linter "
                "can resolve types. Example: stubs/snowflake/connector.pyi for snowflake.connector."
            ),
        }
        default = (
            "See .agent/instructions.md and RULES.md. "
            "Fix the underlying architectural violation; avoid bypasses."
        )
        return manual_instructions.get(rule_code, default)
