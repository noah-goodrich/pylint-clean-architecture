"""Configuration loader for linter settings."""

import sys
from pathlib import Path
from typing import ClassVar, Optional

import astroid  # type: ignore[import-untyped]

if sys.version_info >= (3, 11):
    import tomllib as toml_lib
else:
    try:
        import tomli as toml_lib  # type: ignore[import-not-found]
    except ImportError:
        # Fallback for environment where neither is found during type checking
        toml_lib = None  # type: ignore

from clean_architecture_linter.domain.layer_registry import LayerRegistry, LayerRegistryConfig


class ConfigurationLoader:
    """
    Singleton that loads linter configuration from pyproject.toml.

    Looks for [tool.clean-arch] section.
    """

    _instance: ClassVar[Optional["ConfigurationLoader"]] = None
    _config: ClassVar[dict[str, object]] = {}
    _registry: ClassVar[Optional[LayerRegistry]] = None
    _tool_section: ClassVar[dict[str, object]] = {}  # Full [tool] section for ruff, etc.

    def __new__(cls) -> "ConfigurationLoader":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.load_config()

            # Extract custom layer mappings from config
            # Config format: [tool.clean-arch.layer_map]
            # Key = Layer Name (e.g. "Infrastructure"), Value = Directory/Suffix (e.g. "gateways")
            # We need to flip this for LayerRegistry: Pattern -> Layer Name
            raw_layer_map = cls._config.get("layer_map", {})
            directory_map_override: dict[str, str] = {}

            if isinstance(raw_layer_map, dict):
                for layer_name, pattern_or_list in raw_layer_map.items():
                    if not isinstance(layer_name, str):
                        continue
                    if isinstance(pattern_or_list, list):
                        for pattern in pattern_or_list:
                            if isinstance(pattern, str):
                                directory_map_override[pattern] = layer_name
                    elif isinstance(pattern_or_list, str):
                        directory_map_override[pattern_or_list] = layer_name

            base_class_map = cls._config.get("base_class_map", {})
            module_map = cls._config.get("module_map", {})

            registry_config = LayerRegistryConfig(
                project_type=str(cls._config.get("project_type", "generic")),
                directory_map=directory_map_override,
                base_class_map=_invert_map(base_class_map),
                module_map=_invert_map(module_map),
            )

            cls._registry = LayerRegistry(config=registry_config)
        return cls._instance

    def set_registry(self, registry: LayerRegistry) -> None:
        """Set the layer registry."""
        ConfigurationLoader._registry = registry

    def load_config(self) -> None:
        """Find and load pyproject.toml configuration."""
        current_path = Path.cwd()
        root_path = Path("/")

        while current_path != root_path:
            config_file = current_path / "pyproject.toml"
            if config_file.exists():
                try:
                    with config_file.open("rb") as f:
                        data = toml_lib.load(f)
                        tool_section = data.get("tool", {})

                        # Store full tool section for ruff, mypy, etc.
                        ConfigurationLoader._tool_section = tool_section

                        # 1. Check for [tool.clean-arch] (New)
                        # JUSTIFICATION: Internal access to static configuration singleton
                        ConfigurationLoader._config = tool_section.get("clean-arch", {})  # pylint: disable=clean-arch-visibility

                        # 2. Check for [tool.clean-architecture-linter] (Oldest Legacy)
                        # We keep this strictly for smooth upgrades, but undocumented.
                        # JUSTIFICATION: Internal access to static configuration singleton
                        if not ConfigurationLoader._config:  # pylint: disable=clean-arch-visibility
                            # JUSTIFICATION: Internal access to static configuration singleton
                            ConfigurationLoader._config = tool_section.get(  # pylint: disable=clean-arch-visibility
                                "clean-architecture-linter", {}
                            )

                        # JUSTIFICATION: Internal access to static configuration singleton
                        if ConfigurationLoader._config:  # pylint: disable=clean-arch-visibility
                             # JUSTIFICATION: Internal access to static configuration singleton
                             self.validate_config(ConfigurationLoader._config)  # pylint: disable=clean-arch-visibility
                             return
                except OSError:
                    # Keep looking in parent dirs
                    pass
            current_path = current_path.parent

    def validate_config(self, config: dict[str, object]) -> None:
        """Validate configuration values."""
        allowed_methods = config.get("allowed_lod_methods", [])
        if not isinstance(allowed_methods, (list, set)):
            return

        if allowed_methods:
            import logging
            logging.warning("Configuration Warning: 'allowed_lod_methods' is deprecated. "
                            "Excelsior v3 uses dynamic Type Inference.")

    @property
    def config(self) -> dict[str, object]:
        """Return the loaded configuration."""
        # JUSTIFICATION: Exposing internal static configuration via instance property
        return ConfigurationLoader._config  # pylint: disable=clean-arch-visibility

    @property
    def registry(self) -> LayerRegistry:
        """Return the layer registry."""
        # JUSTIFICATION: Exposing internal static registry via instance property
        if ConfigurationLoader._registry is None:  # pylint: disable=clean-arch-visibility
            # Fallback for unconfigured cases (e.g. tests without config loading)
            # JUSTIFICATION: Lazy initialization of singleton default
            ConfigurationLoader._registry = LayerRegistry(  # pylint: disable=clean-arch-visibility
                LayerRegistryConfig(project_type="generic")
            )
        # JUSTIFICATION: Exposing internal static registry
        return ConfigurationLoader._registry  # pylint: disable=clean-arch-visibility

    def get_layer_for_module(self, module_name: str, file_path: str = "") -> str | None:
        """Get the architectural layer for a module/file."""
        # Check explicit config first
        if "layers" in self._config and isinstance(self._config["layers"], list):
            layers: list[dict[str, object]] = sorted(
                self._config["layers"],
                key=lambda x: len(getattr(x, "get", lambda k, d: "")("module", "")),
                reverse=True,
            )
            match = next(
                (
                    str(getattr(layer, "get", lambda k: None)("name"))
                    for layer in layers
                    if isinstance(layer, dict) and module_name.startswith(str(layer.get("module", "")))
                ),
                None,
            )
            if match:
                return match

        # Check layer_map (Modern)
        if "layer_map" in self._config and isinstance(self._config["layer_map"], dict):
            # Sort by longest prefix first to ensure precision
            sorted_prefixes = sorted(self._config["layer_map"].keys(), key=len, reverse=True)
            for prefix in sorted_prefixes:
                if module_name.startswith(prefix):
                    return str(self._config["layer_map"][prefix])

        # Fall back to convention registry
        return self.registry.resolve_layer("", file_path or module_name)

    @property
    def visibility_enforcement(self) -> bool:
        """Whether to enforce protected member visibility."""
        val = self._config.get("visibility_enforcement", True)
        return bool(val)

    def _get_set(self, key: str, defaults: Optional[set[str]] = None) -> set[str]:
        """Helper to safely get a set of strings from config."""
        raw = self._config.get(key, [])
        items: set[str] = set()
        if isinstance(raw, (list, set)):
            for item in raw:
                if isinstance(item, str):
                    items.add(item)
        if defaults:
            return defaults.union(items)
        return items

    @property
    def allowed_lod_roots(self) -> set[str]:
        """Return allowed LoD roots from config, defaulting to SAFE_ROOTS."""
        defaults = {"builtins", "typing", "importlib", "pathlib", "ast", "os", "json", "yaml", "logging"}
        return self._get_set("allowed_lod_roots", defaults)

    @property
    def allowed_lod_modules(self) -> set[str]:
        """Deprecated: Return allowed LoD modules from config (Legacy Support Only)."""
        return self._get_set("allowed_lod_modules")

    @property
    def allowed_lod_methods(self) -> set[str]:
        """Deprecated: Return allowed LoD methods from config (Legacy Support Only)."""
        return self._get_set("allowed_lod_methods")

    @property
    def internal_modules(self) -> set[str]:
        """Return list of internal modules (merged with defaults)."""
        from clean_architecture_linter.domain.constants import DEFAULT_INTERNAL_MODULES
        return set(DEFAULT_INTERNAL_MODULES).union(self._get_set("internal_modules"))

    @property
    def infrastructure_modules(self) -> set[str]:
        """Return list of modules considered infrastructure."""
        return self._get_set("infrastructure_modules")

    @property
    def raw_types(self) -> set[str]:
        """Return list of type names considered raw/infrastructure."""
        return self._get_set("raw_types")

    @property
    def silent_layers(self) -> set[str]:
        """Return list of layers where I/O is restricted."""
        defaults = {"Domain", "UseCase", "domain", "use_cases"}
        return self._get_set("silent_layers", defaults)

    @property
    def allowed_io_interfaces(self) -> set[str]:
        """Return list of interfaces/types allowed to perform I/O in silent layers."""
        defaults = {"TelemetryPort", "LoggerPort"}
        return self._get_set("allowed_io_interfaces", defaults)

    @property
    def shared_kernel_modules(self) -> set[str]:
        """Return list of modules considered Shared Kernel."""
        return self._get_set("shared_kernel_modules")

    def get_layer_for_class_node(self, node: astroid.nodes.ClassDef) -> Optional[str]:
        """Delegate to registry for LoD compliance."""
        return self.registry.get_layer_for_class_node(node)

    def resolve_layer(
        self,
        node_name: str,
        file_path: str,
        node: Optional[astroid.nodes.NodeNG] = None,
    ) -> Optional[str]:
        """Delegate to registry for LoD compliance."""
        return self.registry.resolve_layer(node_name, file_path, node=node)

    # Ruff configuration methods

    def get_project_ruff_config(self) -> dict[str, object]:
        """Get [tool.ruff] configuration from pyproject.toml."""
        return ConfigurationLoader._tool_section.get("ruff", {})  # type: ignore

    def get_excelsior_ruff_config(self) -> dict[str, object]:
        """Get [tool.excelsior.ruff] configuration from pyproject.toml."""
        excelsior_section = ConfigurationLoader._tool_section.get("excelsior", {})
        if isinstance(excelsior_section, dict):
            return excelsior_section.get("ruff", {})  # type: ignore
        return {}

    def get_ruff_config(self) -> dict[str, object]:
        """Alias for get_project_ruff_config for backward compatibility."""
        return self.get_project_ruff_config()

    def get_merged_ruff_config(self) -> dict[str, object]:
        """Get merged Ruff config (Excelsior defaults + project overrides).

        Uses Option C strategy:
        - Excelsior provides comprehensive defaults
        - Project-specific settings override defaults
        """
        from clean_architecture_linter.infrastructure.adapters.ruff_adapter import RuffAdapter

        adapter = RuffAdapter()
        project_config = self.get_project_ruff_config()
        excelsior_config = self.get_excelsior_ruff_config()

        return adapter._merge_configs(
            project_config if isinstance(project_config, dict) else {},
            excelsior_config if isinstance(excelsior_config, dict) else {}
        )

    @property
    def ruff_enabled(self) -> bool:
        """Check if Ruff is enabled (default: True)."""
        excelsior_section = ConfigurationLoader._tool_section.get("excelsior", {})
        if isinstance(excelsior_section, dict):
            return bool(excelsior_section.get("ruff_enabled", True))
        return True  # Enabled by default


def _invert_map(config_map: object) -> dict[str, str]:
    """Invert config map (Layer -> Items) to (Item -> Layer)."""
    inverted: dict[str, str] = {}
    if not isinstance(config_map, dict):
        return inverted
    for layer_name, item_or_list in config_map.items():
        if not isinstance(layer_name, str):
            continue
        if isinstance(item_or_list, list):
            for item in item_or_list:
                if isinstance(item, str):
                    inverted[item] = layer_name
        elif isinstance(item_or_list, str):
            inverted[item_or_list] = layer_name
    return inverted
