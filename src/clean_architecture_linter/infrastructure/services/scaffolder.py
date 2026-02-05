"""Service for initializing project scaffolding."""

import json
import sys
from pathlib import Path
from typing import Optional, cast

from clean_architecture_linter.domain.config import ConfigurationLoader
from clean_architecture_linter.domain.constants import (
    AGENT_INSTRUCTIONS_TEMPLATE,
    HANDSHAKE_SNIPPET,
    ONBOARDING_TEMPLATE,
    PRE_FLIGHT_WORKFLOW_TEMPLATE,
)
from clean_architecture_linter.interface.telemetry import TelemetryPort


class Scaffolder:
    """Handles project initialization and configuration."""

    def __init__(
        self,
        telemetry: TelemetryPort,
        config_loader: ConfigurationLoader,
    ) -> None:
        self.telemetry = telemetry
        self._config_loader = config_loader

    def init_project(self, template: Optional[str] = None, check_layers: bool = False) -> None:
        """Initialize configuration and artifacts."""
        if check_layers:
            self._check_layers()
            return

        agent_dir = Path(".agent")
        if not agent_dir.exists():
            agent_dir.mkdir()
            self.telemetry.step(f"Created directory: {agent_dir}")

        # Instructions
        instructions_file = agent_dir / "instructions.md"
        self._generate_instructions(instructions_file)

        # Pre-Flight Workflow
        pre_flight_file = agent_dir / "pre-flight.md"
        with pre_flight_file.open("w", encoding="utf-8") as f:
            f.write(PRE_FLIGHT_WORKFLOW_TEMPLATE)
        self.telemetry.step(f"Generated: {pre_flight_file}")

        # Makefile Handshake Injection
        self._update_makefile()

        # Onboarding Artifact
        onboarding_file = Path("ARCHITECTURE_ONBOARDING.md")
        if not onboarding_file.exists():
            with onboarding_file.open("w", encoding="utf-8") as f:
                f.write(ONBOARDING_TEMPLATE)
            self.telemetry.step(f"Generated: {onboarding_file}")

        # Tool Audit & Smart Config
        self._perform_tool_audit(template)

        # Ruff Configuration Wizard
        self._configure_ruff_wizard()

        # AI Handover message
        self.telemetry.step("AI Agent Handover initialized.")
        print("\n" + "=" * 40)
        print("🤖 AI AGENT HANDOVER")
        print("=" * 40)
        print(
            "Please read 'ARCHITECTURE_ONBOARDING.md' and '.agent/instructions.md' "
            "to understand the architectural rules and refactoring plan."
        )
        print("Start with Phase 1 in ARCHITECTURE_ONBOARDING.md.")
        print("=" * 40 + "\n")

    def _update_makefile(self) -> None:
        makefile_path = Path("Makefile")
        content: str = ""
        if makefile_path.exists():
            with makefile_path.open("r", encoding="utf-8") as f:
                content = f.read()

        if "handshake:" in content:
            self.telemetry.step(
                "Makefile already contains handshake protocol.")
            return

        with makefile_path.open("a", encoding="utf-8") as f:
            f.write(HANDSHAKE_SNIPPET)
        self.telemetry.step(
            "Injected Stellar Handshake Protocol into Makefile.")

    def _check_layers(self) -> None:
        config = self._config_loader.config
        layer_map = config.get("layer_map", {})

        self.telemetry.step("Active Layer Configuration:")
        if not isinstance(layer_map, dict) or not layer_map:
            self.telemetry.error(
                "No layer_map found in pyproject.toml [tool.clean-arch].")
            return

        for pattern, layer in layer_map.items():
            self.telemetry.step(f"  {pattern} -> {layer}")

    def _generate_instructions(self, path: Path) -> None:
        config = self._config_loader.config
        layer_map = config.get("layer_map", {})

        display_names = {
            "Domain": "Domain",
            "UseCase": "UseCase",
            "Infrastructure": "Infrastructure",
            "Interface": "Interface",
        }

        if isinstance(layer_map, dict):
            for directory, layer in layer_map.items():
                if not isinstance(layer, str) or not isinstance(directory, str):
                    continue
                cleaned: str = directory.replace("_", "")
                if layer in display_names and cleaned.isalnum():
                    display_names[layer] = f"{directory.capitalize()} ({layer})"

        with path.open("w", encoding="utf-8") as f:
            f.write(
                AGENT_INSTRUCTIONS_TEMPLATE.format(
                    domain_layer=display_names["Domain"],
                    use_case_layer=display_names["UseCase"],
                    infrastructure_layer=display_names["Infrastructure"],
                    interface_layer=display_names["Interface"],
                )
            )
        self.telemetry.step(f"Generated: {path}")

    def _perform_tool_audit(self, template: Optional[str]) -> None:
        pyproject_path = Path("pyproject.toml")
        if not pyproject_path.exists():
            return

        data = self._load_pyproject(pyproject_path)
        if not data or not isinstance(data, dict):
            return

        tool_section = data.get("tool", {})
        if not isinstance(tool_section, dict):
            return

        style_tools = {"ruff", "black", "flake8"}
        found_tools = style_tools.intersection(tool_section.keys())

        new_data = data.copy()
        new_tool = cast(dict[str, object], new_data.setdefault("tool", {}))
        if "clean-arch" not in new_tool:
            new_tool["clean-arch"] = {}

        if template:
            self._apply_template_updates(new_data, template)
            self.telemetry.step(f"Applied template updates for: {template}")

        if found_tools:
            self._print_architecture_only_mode_advice(found_tools)

        if template:
            print(
                f"\n[TEMPLATE CONFIG] Add the following to [tool.clean-arch] for {template}:")
            clean_arch_section_raw = cast(
                dict[str, object], new_data["tool"]).get("clean-arch")
            print(json.dumps(clean_arch_section_raw, indent=2))

    def _load_pyproject(self, path: Path) -> dict[str, object] | None:
        try:
            if sys.version_info >= (3, 11):
                import tomllib as toml_lib
            else:
                try:
                    import tomli as toml_lib  # type: ignore
                except ImportError:
                    return None
            with path.open("rb") as f:
                return cast(dict[str, object], toml_lib.load(f))
        except (OSError, ValueError) as e:
            print(f"Warning: Could not parse pyproject.toml: {e}")
        return None

    def _apply_template_updates(self, data: dict[str, object], template: str) -> None:
        tool_section = data.get("tool", {})
        if not isinstance(tool_section, dict):
            return
        clean_arch = tool_section.get("clean-arch")
        if not isinstance(clean_arch, dict):
            return

        if template == "fastapi":
            layer_map = cast(
                dict[str, str], clean_arch.setdefault("layer_map", {}))
            layer_map.update(
                {"routers": "Interface", "services": "UseCase", "schemas": "Interface"})
        elif template == "sqlalchemy":
            layer_map = cast(
                dict[str, str], clean_arch.setdefault("layer_map", {}))
            layer_map.update({"models": "Infrastructure",
                             "repositories": "Infrastructure"})
            base_class_map = cast(
                dict[str, str], clean_arch.setdefault("base_class_map", {}))
            base_class_map.update(
                {"Base": "Infrastructure", "DeclarativeBase": "Infrastructure"})

    def _print_architecture_only_mode_advice(self, found_tools: set[str]) -> None:
        self.telemetry.step(
            f"Detected style tools: {', '.join(found_tools)}. Enabling Architecture-Only Mode.")
        print(
            "\n[RECOMMENDED ACTION] Add this to pyproject.toml to disable conflicting style checks:")
        print(
            """
[tool.pylint.messages_control]
disable: str = "all"
enable = ["clean-arch-classes", "clean-arch-imports", "clean-arch-layers"] # and other specific checks
            """
        )

    def _configure_ruff_wizard(self) -> None:
        """Interactive wizard for Ruff configuration."""
        if not sys.stdin.isatty():
            return
        if Path("pyproject.toml").exists() and not self._ruff_wizard_can_use_toml():
            return
        from clean_architecture_linter.infrastructure.adapters.ruff_adapter import RuffAdapter

        print("\n" + "=" * 60)
        print("🎨 RUFF CODE QUALITY CONFIGURATION")
        print("=" * 60)

        if self._ruff_wizard_has_existing_config() and not self._ruff_wizard_prompt_overwrite():
            return

        defaults = RuffAdapter.get_default_config()
        if not self._ruff_wizard_prompt_use_defaults(defaults):
            return

        line_length, max_complexity, select_rules = self._ruff_wizard_customize(
            defaults)
        self._write_ruff_config(line_length, max_complexity, select_rules)
        self.telemetry.step("✅ Ruff configuration added to pyproject.toml")
        print("\nℹ️  Configuration written to [tool.excelsior.ruff]")
        print("   To override specific rules, add [tool.ruff] section.")
        print("   Project-specific [tool.ruff] settings will take precedence.")

    def _ruff_wizard_can_use_toml(self) -> bool:
        """Return False if pyproject exists but tomllib/tomli unavailable (step + skip wizard)."""
        if sys.version_info >= (3, 11):
            return True
        import importlib.util
        if importlib.util.find_spec("tomli") is None:
            self.telemetry.step(
                "⚠️  tomli not available, skipping Ruff wizard")
            return False
        return True

    def _ruff_wizard_has_existing_config(self) -> bool:
        """Check if pyproject.toml has ruff or excelsior.ruff config."""
        data = self._load_pyproject_toml()
        if not data:
            return False
        tool = data.get("tool", {})
        return bool(tool.get("ruff") or tool.get("excelsior", {}).get("ruff"))

    def _load_pyproject_toml(self) -> Optional[dict[str, object]]:
        """Load pyproject.toml via tomllib/tomli. Returns None on missing or error."""
        pyproject_path = Path("pyproject.toml")
        if not pyproject_path.exists():
            return None
        if sys.version_info >= (3, 11):
            import tomllib as toml_lib
        else:
            try:
                import tomli as toml_lib  # type: ignore
            except ImportError:
                return None
        try:
            with pyproject_path.open("rb") as f:
                return toml_lib.load(f)
        except Exception:
            return None

    def _ruff_wizard_prompt_overwrite(self) -> bool:
        """Ask user to overwrite existing Ruff config. True = overwrite."""
        print("✅ Ruff configuration already exists in pyproject.toml")
        response = input(
            "Overwrite with Excelsior defaults? [y/N]: ").strip().lower()
        if response not in ["y", "yes"]:
            print("Keeping existing Ruff configuration.")
            return False
        return True

    def _ruff_wizard_prompt_use_defaults(self, defaults: dict[str, object]) -> bool:
        """Print defaults, ask to use them. False = skip wizard."""
        print("\nExcelsior provides opinionated Ruff defaults for consistency:")
        print(f"  • Line Length: {defaults['line-length']} chars")
        print(
            f"  • Max Complexity: {defaults['lint']['mccabe']['max-complexity']}")
        print(
            f"  • Rule Categories: {len(defaults['lint']['select'])} enabled")
        print(f"    ({', '.join(defaults['lint']['select'][:8])}...)")
        print("\nThese defaults match the strictest config across your projects.")
        response = input("\nUse Excelsior defaults? [Y/n]: ").strip().lower()
        if response in ["n", "no"]:
            print("\nℹ️  Skipping Ruff configuration.")
            print(
                "   You can manually add [tool.excelsior.ruff] to pyproject.toml later.")
            return False
        return True

    def _ruff_wizard_customize(
        self, defaults: dict[str, object]
    ) -> tuple[int, int, list[str]]:
        """Optional line-length and max-complexity overrides."""
        print("\n--- Optional Customizations ---")
        line_length = defaults["line-length"]
        custom_length = input(f"Line length [{line_length}]: ").strip()
        if custom_length.isdigit():
            line_length = int(custom_length)
        max_complexity = defaults["lint"]["mccabe"]["max-complexity"]
        custom_complexity = input(
            f"Max complexity [{max_complexity}]: ").strip()
        if custom_complexity.isdigit():
            max_complexity = int(custom_complexity)
        return (line_length, max_complexity, defaults["lint"]["select"])

    def _write_ruff_config(self, line_length: int, max_complexity: int, select_rules: list[str]) -> None:
        """Write Ruff configuration to pyproject.toml."""
        import sys
        if sys.version_info >= (3, 11):
            import tomllib as toml_lib
        else:
            try:
                import tomli as toml_lib  # type: ignore
            except ImportError:
                print("⚠️  Cannot write config: tomli not available")
                return

        pyproject_path = Path("pyproject.toml")
        data: dict[str, Any] = {}

        if pyproject_path.exists():
            with pyproject_path.open("rb") as f:
                data = toml_lib.load(f)

        # Ensure structure
        if "tool" not in data:
            data["tool"] = {}
        if "excelsior" not in data["tool"]:
            data["tool"]["excelsior"] = {}

        # Write Ruff config
        data["tool"]["excelsior"]["ruff"] = {
            "line-length": line_length,
            "target-version": "py310",
            "lint": {
                "select": select_rules,
                "ignore": ["E501", "PLR0913"],
                "mccabe": {"max-complexity": max_complexity}
            }
        }

        # Write back (we need tomlkit or tomli-w for writing)
        try:
            import tomli_w  # type: ignore[import-not-found]
            with pyproject_path.open("wb") as f:
                tomli_w.dump(data, f)
        except ImportError:
            # Fallback: append as text
            print("⚠️  tomli-w not available, appending config as text...")
            with pyproject_path.open("a", encoding="utf-8") as f:
                f.write("\n[tool.excelsior.ruff]\n")
                f.write(f"line-length = {line_length}\n")
                f.write('target-version = "py310"\n')
                f.write("\n[tool.excelsior.ruff.lint]\n")
                f.write(f'select = {json.dumps(select_rules)}\n')
                f.write('ignore = ["E501", "PLR0913"]\n')
                f.write("\n[tool.excelsior.ruff.lint.mccabe]\n")
                f.write(f"max-complexity = {max_complexity}\n")
