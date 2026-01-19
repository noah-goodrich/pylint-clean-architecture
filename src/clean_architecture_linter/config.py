"""Configuration loader for linter settings."""

import sys
from pathlib import Path
from typing import ClassVar, Optional, Union

import astroid  # type: ignore[import-untyped]

if sys.version_info >= (3, 11):
    import tomllib as toml_lib
else:
    try:
        import tomli as toml_lib  # type: ignore[import-not-found]
    except ImportError:
        # Fallback for environment where neither is found during type checking
        toml_lib = None  # type: ignore

from clean_architecture_linter.layer_registry import LayerRegistry, LayerRegistryConfig


class ConfigurationLoader:
    """
    Singleton that loads linter configuration from pyproject.toml.

    Looks for [tool.clean-arch] section.
    """

    _instance: ClassVar[Optional["ConfigurationLoader"]] = None
    _config: ClassVar[dict[str, object]] = {}
    _registry: ClassVar[Optional[LayerRegistry]] = None

    def __new__(cls) -> "ConfigurationLoader":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.load_config()

            project_type = cls._config.get("project_type", "generic")

            # Extract custom layer mappings from config
            # Config format: [tool.clean-arch.layer_map]
            # Key = Layer Name (e.g. "Infrastructure"), Value = Directory/Suffix (e.g. "gateways")
            # We need to flip this for LayerRegistry: Pattern -> Layer Name
            raw_layer_map: dict[str, object] = cls._config.get("layer_map", {})
            directory_map_override: dict[str, str] = {}

            for layer_name, pattern_or_list in raw_layer_map.items():
                if isinstance(pattern_or_list, list):
                    for pattern in pattern_or_list:
                        directory_map_override[pattern] = layer_name
                else:
                    directory_map_override[pattern_or_list] = layer_name

            registry_config = LayerRegistryConfig(
                project_type=project_type,
                directory_map=directory_map_override,
                base_class_map=_invert_map(cls._config.get("base_class_map", {})),
                module_map=_invert_map(cls._config.get("module_map", {})),
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
                            self.validate_config(ConfigurationLoader._config)
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

        for method in allowed_methods:
            if not isinstance(method, str):
                continue
            # Task 3: Surgical FQN Overrides (Tier 3 Hardening)
            # Every entry in allowed_lod_methods MUST be a Fully Qualified Name (FQN)
            # with at least two dots (e.g., snowflake.snowpark.Table.collect).
            if method.count(".") < 2:
                error_msg = (
                    f"Invalid LoD configuration: Method override '{method}' must use "
                    "a Fully Qualified Name with at least two dots (e.g. 'builtins.str.split') "
                    "to prevent global shadowing. Bare names like 'get' are rejected."
                )
                raise ValueError(error_msg)

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
                    getattr(layer, "get", lambda k: None)("name")
                    for layer in layers
                    if isinstance(layer, dict) and module_name.startswith(layer.get("module", ""))
                ),
                None,
            )
            if match:
                return match

        # Fall back to convention registry
        return self.registry.resolve_layer("", file_path or module_name)

    @property
    def visibility_enforcement(self) -> bool:
        """Whether to enforce protected member visibility."""
        return self._config.get("visibility_enforcement", True)  # Default ON

    @property
    def allowed_lod_roots(self) -> set[str]:
        """Return allowed LoD roots from config, defaulting to SAFE_ROOTS."""
        # Default roots
        defaults = {"importlib", "pathlib", "ast", "os", "json", "yaml"}
        config_val = self._config.get("allowed_lod_roots", [])
        return defaults.union(set(config_val))

    @property
    def allowed_lod_modules(self) -> set[str]:
        """Return allowed LoD modules from config."""
        return set(self._config.get("allowed_lod_modules", []))

    @property
    def allowed_lod_methods(self) -> set[str]:
        """Return allowed LoD methods from config."""
        return set(self._config.get("allowed_lod_methods", []))

    @property
    def internal_modules(self) -> set[str]:
        """Return list of internal modules (domain/use_cases etc) from config (merged with defaults)."""
        from clean_architecture_linter.constants import DEFAULT_INTERNAL_MODULES

        config_val = self._config.get("internal_modules", [])
        return DEFAULT_INTERNAL_MODULES.union(set(config_val))

    @property
    def infrastructure_modules(self) -> set[str]:
        """Return list of modules considered infrastructure."""
        return set(self._config.get("infrastructure_modules", []))

    @property
    def raw_types(self) -> set[str]:
        """Return list of type names considered raw/infrastructure."""
        return set(self._config.get("raw_types", []))

    @property
    def silent_layers(self) -> set[str]:
        """Return list of layers where I/O is restricted."""
        defaults = {"Domain", "UseCase", "domain", "use_cases"}
        config_val = self._config.get("silent_layers", [])
        return defaults.union(set(config_val))

    @property
    def allowed_io_interfaces(self) -> set[str]:
        """Return list of interfaces/types allowed to perform I/O in silent layers."""
        defaults = {"TelemetryPort", "LoggerPort"}
        config_val = self._config.get("allowed_io_interfaces", [])
        return defaults.union(set(config_val))

    @property
    def shared_kernel_modules(self) -> set[str]:
        """Return list of modules considered Shared Kernel (allowed to be imported anywhere)."""
        return set(self._config.get("shared_kernel_modules", []))

    def get_layer_for_class_node(self, node: astroid.nodes.ClassDef) -> Optional[str]:
        """Delegate to registry for LoD compliance."""
        return self.registry.get_layer_for_class_node(node)

    def resolve_layer(
        self, node_name: str, file_path: str, node: Optional[astroid.nodes.NodeNG] = None
    ) -> Optional[str]:
        """Delegate to registry for LoD compliance."""
        return self.registry.resolve_layer(node_name, file_path, node=node)


def _invert_map(config_map: Union[dict[str, object], object]) -> dict[str, str]:
    """Invert config map (Layer -> Items) to (Item -> Layer)."""
    inverted: dict[str, str] = {}
    if not isinstance(config_map, dict):
        return inverted
    for layer_name, item_or_list in config_map.items():
        if isinstance(item_or_list, list):
            for item in item_or_list:
                inverted[item] = layer_name
        else:
            inverted[item_or_list] = layer_name
    return inverted
