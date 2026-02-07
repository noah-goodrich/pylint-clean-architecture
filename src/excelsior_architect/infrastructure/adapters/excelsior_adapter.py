import os
import re
import subprocess
import sys
from collections import defaultdict
from typing import TYPE_CHECKING

from excelsior_architect.domain.config import ConfigurationLoader
from excelsior_architect.domain.entities import LinterResult
from excelsior_architect.domain.protocols import LinterAdapterProtocol
from excelsior_architect.infrastructure.services.guidance_service import (
    GuidanceService,
)

if TYPE_CHECKING:
    from excelsior_architect.domain.protocols import RawLogPort


class ExcelsiorAdapter(LinterAdapterProtocol):
    """Adapter for Pylint Clean Architecture output."""

    LINTER = "excelsior"

    def __init__(
        self,
        config_loader: ConfigurationLoader,
        raw_log_port: "RawLogPort",
        guidance_service: GuidanceService,
    ) -> None:
        self._config_loader = config_loader
        self._raw_log_port = raw_log_port
        self._guidance = guidance_service

    def gather_results(
        self,
        target_path: str,
        select_only: list[str] | None = None,
    ) -> list[LinterResult]:
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
                "--load-plugins=excelsior_architect",
                "--msg-template={path}:{line}: {msg_id}: {msg} ({symbol})",
            ]

            # Exclude deliberate-violation fixtures from the main audit
            exclude = self._config_loader.audit_exclude_paths
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
            self._raw_log_port.log_raw(
                "pylint",
                result.stdout or "",
                result.stderr or "",
            )
            return self._parse_output(result.stdout)
        except Exception as e:
            # JUSTIFICATION: Error message wrapping requires explicit list creation.
            return [LinterResult("EXCELSIOR_ERROR", str(e), [])]

    def _parse_output(self, output: str) -> list[LinterResult]:
        # Pattern: path:line: msg_id: msg (symbol)
        pattern = re.compile(r"^(.*?):(\d+): (.*?): (.*)$")
        # R0801 continuation: ==module.name:[start:end] (actual duplicate locations)
        r0801_continuation = re.compile(r"^==([^:]+):\[(\d+):(\d+)\]")

        lines = output.splitlines()
        collected: dict[str, dict[str, object]] = defaultdict(
            lambda: {"message": "", "locations": set()})
        r0801_results: list[LinterResult] = []
        i = 0

        while i < len(lines):
            line = lines[i]
            match = pattern.match(line)
            if match:
                file_path, line_num, msg_id, message = match.groups()
                location = f"{file_path}:{line_num}"

                if msg_id == "R0801":
                    # R0801 is multi-line: next lines are ==module:[start:end].
                    # Emit one LinterResult per block with real duplicate locations.
                    locations_list: list[str] = []
                    j = i + 1
                    while j < len(lines):
                        cont = r0801_continuation.match(lines[j])
                        if cont:
                            module_name, start, _end = cont.groups()
                            path = self._module_to_path(module_name)
                            locations_list.append(f"{path}:{start}")
                            j += 1
                        elif pattern.match(lines[j]):
                            break
                        else:
                            # Skip code snippets or other non-matching lines within the R0801 block
                            j += 1
                    msg_clean = self._strip_ansi(str(message))
                    r0801_results.append(
                        LinterResult(
                            "R0801",
                            msg_clean,
                            sorted(locations_list) if locations_list else [
                                location],
                        )
                    )
                    i = j
                    continue

                entry = collected[msg_id]
                entry["message"] = message
                locations_set = entry["locations"]
                if isinstance(locations_set, set):
                    locations_set.add(location)
            i += 1

        results = list(r0801_results)
        for msg_id, data in collected.items():
            # Skip R0801 in collected to avoid duplicates (it was handled separately above)
            if msg_id == "R0801":
                continue
            locations_set = data["locations"]
            sorted_locations = sorted(locations_set) if isinstance(
                locations_set, set) else []
            results.append(LinterResult(msg_id, str(
                data["message"]), sorted_locations))

        return results

    @staticmethod
    def _module_to_path(module_name: str) -> str:
        """Convert pylint module name to src-relative file path (e.g. a.b.c -> src/a/b/c.py)."""
        return "src/" + module_name.replace(".", "/") + ".py"

    @staticmethod
    def _strip_ansi(text: str) -> str:
        """Remove common ANSI escape sequences from pylint message."""
        return re.sub(r"\033\[[0-9;]*m", "", text).strip()

    def supports_autofix(self) -> bool:
        """Check if this linter supports automatic fixing."""
        return True  # Via LibCST fixes

    def get_fixable_rules(self) -> list[str]:
        """
        Return list of rule codes that can be auto-fixed (via LibCST transforms).

        Includes both structural fixes and comment-only fixes (governance comments).
        Source: rule_registry.yaml (fixable: true). Fallback to registry load if no guidance injected.
        """
        codes = self._guidance.get_fixable_codes()
        # Rules not yet in YAML with fixable: true but used by ApplyFixesUseCase (structural/legacy)
        extra = {"clean-arch-immutable",
                 "clean-arch-lifecycle", "clean-arch-type-integrity"}
        return sorted(set(codes) | extra)

    def apply_fixes(
        self,
        target_path: str,
        select_only: list[str] | None = None,
    ) -> bool:
        """Excelsior fixes are applied via ApplyFixesUseCase, not this adapter."""
        return False

    def is_comment_only_rule(self, rule_code: str) -> bool:
        """
        Check if a rule uses comment-only fixes (governance comments).

        Returns:
            True if the rule injects governance comments rather than structural fixes.
        Source: rule_registry.yaml (comment_only: true).
        """
        return rule_code in self._guidance.get_comment_only_codes()

    def get_manual_fix_instructions(self, rule_code: str) -> str:
        """Readable, step-by-step guidance for juniors and AI (from rule_registry.yaml when available)."""
        instructions = self._guidance.get_manual_instructions(
            self.LINTER, rule_code)
        if instructions and instructions.strip():
            return instructions
        return (
            "See .agent/instructions.md and RULES.md. "
            "Fix the underlying architectural violation; avoid bypasses."
        )

    def get_display_name(self, rule_code: str) -> str:
        """Return display name for the rule (from rule_registry.yaml). Used by governance comments."""
        return self._guidance.get_display_name(rule_code)
