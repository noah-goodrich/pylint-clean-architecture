"""Ruff adapter for code quality checks."""

import json
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from clean_architecture_linter.domain.entities import LinterResult

if TYPE_CHECKING:
    from stellar_ui_kit import TelemetryPort


class RuffAdapter:
    """Adapter for running Ruff and parsing results."""

    def __init__(self, telemetry: Optional["TelemetryPort"] = None) -> None:
        self.telemetry = telemetry

    @staticmethod
    def get_default_config() -> Dict[str, Any]:
        """Return Excelsior's opinionated Ruff defaults.

        Based on snowarch's strictest configuration.
        """
        return {
            "line-length": 120,
            "target-version": "py310",
            "lint": {
                "select": [
                    "E",    # pycodestyle errors
                    "F",    # Pyflakes
                    "W",    # pycodestyle warnings
                    "C90",  # mccabe complexity
                    "I",    # isort
                    "N",    # pep8-naming
                    "UP",   # pyupgrade
                    "PL",   # Pylint
                    "PT",   # flake8-pytest-style
                    "B",    # flake8-bugbear
                    "A",    # flake8-builtins
                    "C4",   # flake8-comprehensions
                    "SIM",  # flake8-simplify
                    "ARG",  # flake8-unused-arguments
                    "PTH",  # flake8-use-pathlib
                    "RUF",  # Ruff-specific rules
                ],
                "ignore": [
                    "E501",     # Line length (formatter handles this)
                    "PLR0913",  # Too many arguments (let complexity handle it)
                ],
                "mccabe": {
                    "max-complexity": 10
                }
            }
        }

    def _merge_configs(
        self,
        project_config: Dict[str, Any],
        excelsior_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge Ruff configs with project settings taking precedence.

        Strategy (Option C from user request):
        - Excelsior provides comprehensive defaults
        - Project-specific settings override defaults
        """
        # Start with Excelsior defaults
        merged = self.get_default_config().copy()

        # Apply excelsior.ruff overrides
        for key, value in excelsior_config.items():
            if isinstance(value, dict) and key in merged and isinstance(merged[key], dict):
                merged[key].update(value)
            else:
                merged[key] = value

        # Apply project.ruff overrides (wins over excelsior)
        for key, value in project_config.items():
            if isinstance(value, dict) and key in merged and isinstance(merged[key], dict):
                # For nested dicts like lint.select, project fully overrides
                if key == "lint":
                    # Deep merge lint config
                    for lint_key, lint_value in value.items():
                        if lint_key in ["select", "ignore"]:
                            # Project wins completely for select/ignore
                            merged[key][lint_key] = lint_value
                        elif isinstance(lint_value, dict):
                            if lint_key not in merged[key]:
                                merged[key][lint_key] = {}
                            merged[key][lint_key].update(lint_value)
                        else:
                            merged[key][lint_key] = lint_value
                else:
                    merged[key].update(value)
            else:
                merged[key] = value

        return merged

    def run(
        self,
        target_path: Path,
        config: Optional[Dict[str, Any]] = None
    ) -> List[LinterResult]:
        """Run Ruff on target path and return violations.

        Args:
            target_path: Path to check
            config: Optional Ruff configuration dict

        Returns:
            List of LinterResult objects
        """
        if self.telemetry:
            self.telemetry.step(f"Running Ruff on {target_path}...")

        try:
            # Build ruff command
            cmd = ["ruff", "check", str(target_path), "--output-format=json"]

            # Run ruff
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            return self._parse_ruff_output(result.stdout, result.returncode)

        except FileNotFoundError:
            error_result = LinterResult(
                code="RUFF_ERROR",
                message="Ruff not found. Install with: pip install ruff",
                locations=["system"]
            )
            return [error_result]
        except subprocess.TimeoutExpired:
            error_result = LinterResult(
                code="RUFF_ERROR",
                message="Ruff timed out after 5 minutes",
                locations=["system"]
            )
            return [error_result]
        except Exception as e:
            error_result = LinterResult(
                code="RUFF_ERROR",
                message=f"Ruff execution error: {str(e)}",
                locations=["system"]
            )
            return [error_result]

    def _parse_ruff_output(self, stdout: str, returncode: int) -> List[LinterResult]:
        """Parse Ruff JSON output into LinterResult objects.

        Groups violations by code and aggregates locations, matching the pattern
        used by MypyAdapter and ExcelsiorAdapter.

        Args:
            stdout: Ruff JSON output
            returncode: Process return code

        Returns:
            List of LinterResult objects grouped by violation code
        """
        if not stdout.strip():
            return []

        try:
            from collections import defaultdict

            # Ruff outputs an array of violation objects
            violations = json.loads(stdout)

            # Group by code: {code: {"message": str, "locations": set}}
            collected: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"message": "", "locations": set()})

            for violation in violations:
                # Ruff JSON format:
                # {
                #   "code": "E501",
                #   "message": "Line too long (120 > 88 characters)",
                #   "location": {"row": 10, "column": 1},
                #   "filename": "src/example.py",
                #   ...
                # }

                code = violation.get("code", "UNKNOWN")
                message = violation.get("message", "")
                filename = violation.get("filename", "")
                location_data = violation.get("location", {})
                row = location_data.get("row", 0)

                location = f"{filename}:{row}" if filename and row else filename or "unknown"

                # Store first message for this code
                entry = collected[code]
                if not entry["message"]:
                    entry["message"] = message

                # Add location to set
                locations_set = entry["locations"]
                if isinstance(locations_set, set):
                    locations_set.add(location)

            # Convert to LinterResult objects
            results = []
            for code, data in collected.items():
                locations_set = data["locations"]
                sorted_locations = sorted(list(locations_set)) if isinstance(locations_set, set) else []
                results.append(LinterResult(code, str(data["message"]), sorted_locations))

            return results

        except json.JSONDecodeError as e:
            # If JSON parsing fails, return a parse error
            parse_error = LinterResult(
                code="RUFF_PARSE_ERROR",
                message=f"Failed to parse Ruff output: {str(e)}",
                locations=["system"]
            )
            return [parse_error]

    def gather_results(self, target_path: str) -> List[LinterResult]:
        """Compatibility method for existing adapter interface.

        This method matches the interface used by MypyAdapter and ExcelsiorAdapter.
        """
        return self.run(Path(target_path))

    def supports_autofix(self) -> bool:
        """Check if this linter supports automatic fixing."""
        return True

    def get_fixable_rules(self) -> List[str]:
        """Return list of rule codes that can be auto-fixed."""
        # Most Ruff rules are auto-fixable
        return [
            "F", "E", "W",  # Pyflakes, pycodestyle
            "I",  # isort
            "UP",  # pyupgrade
            "C901",  # Some complexity issues (via refactoring)
            "SIM",  # simplify
            "PTH",  # pathlib
            "RUF",  # Ruff-specific
        ]

    def get_manual_fix_instructions(self, rule_code: str) -> str:
        """Get manual fix instructions for a specific rule."""
        manual_instructions = {
            "ARG001": (
                "Remove unused function argument or prefix with underscore (_arg) "
                "to indicate intentional non-use."
            ),
            "ARG002": "Remove unused method argument or prefix with underscore",
            "PLR0913": (
                "Reduce number of function arguments. "
                "Consider grouping related args into a dataclass/config object."
            ),
            "C901": "Reduce cyclomatic complexity by extracting logic into smaller functions",
            "PLR0912": "Reduce number of branches. Consider using early returns, lookup tables, or strategy pattern",
            "PLR0915": "Reduce function length by extracting logic into helper methods",
            "B008": (
                "Move default mutable argument (list/dict) inside function body "
                "with 'if arg is None: arg = []'."
            ),
        }
        default: str = "See Ruff documentation: https://docs.astral.sh/ruff/rules/"
        return manual_instructions.get(rule_code, default)

    def apply_fixes(self, target_path: Path) -> bool:
        """Apply Ruff automatic fixes to the target path.

        Args:
            target_path: Path to fix

        Returns:
            True if fixes were applied, False otherwise
        """
        try:
            if self.telemetry:
                self.telemetry.step(f"🔧 Applying Ruff fixes to {target_path}...")

            # Ruff --fix applies automatic fixes
            cmd = [
                "ruff",
                "check",
                str(target_path),
                "--fix"
            ]

            # Use config from ConfigurationLoader if available
            from clean_architecture_linter.config import ConfigurationLoader
            config_loader = ConfigurationLoader()
            merged_config = config_loader.get_merged_ruff_config()

            if merged_config and merged_config.get("lint", {}).get("select"):
                select_rules = merged_config["lint"]["select"]
                cmd.extend(["--select", ",".join(select_rules)])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )

            # Ruff returns 0 if it fixed everything, 1 if there are still issues
            # Either way, if it ran successfully, fixes may have been applied
            if self.telemetry:
                if result.returncode == 0:
                    self.telemetry.step("✅ All Ruff issues fixed")
                else:
                    self.telemetry.step("⚠️  Some Ruff issues remain (may require manual fixes)")

            return True

        except FileNotFoundError:
            if self.telemetry:
                self.telemetry.step("❌ Ruff not found. Install with: pip install ruff")
            return False
        except Exception as e:
            if self.telemetry:
                self.telemetry.step(f"❌ Ruff fix error: {str(e)}")
            return False
