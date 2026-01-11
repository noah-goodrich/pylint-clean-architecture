"""Configuration loader for linter settings."""

from pathlib import Path
from typing import Any, Dict, Optional

try:
    import tomli as toml  # type: ignore[import-not-found]
except ImportError:
    # Python 3.11+ has tomllib
    import tomllib as toml  # type: ignore[import-not-found]

from clean_architecture_linter.layer_registry import LayerRegistry, LayerRegistryConfig


class ConfigurationLoader:
    """
    Singleton that loads linter configuration from pyproject.toml.

    Looks for [tool.clean-arch] section.
    """

    _instance = None
    _config: Dict[str, Any] = {}
    _registry: Optional[LayerRegistry] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigurationLoader, cls).__new__(cls)
            cls._instance.load_config()

            project_type = cls._instance.config.get("project_type", "generic")

            # Extract custom layer mappings from config
            # Config format: [tool.clean-arch.layer_map]
            # Key = Layer Name (e.g. "Infrastructure"), Value = Directory/Suffix (e.g. "gateways")
            # We need to flip this for LayerRegistry: Pattern -> Layer Name
            raw_layer_map = cls._instance.config.get("layer_map", {})
            directory_map_override = {}

            for layer_name, pattern_or_list in raw_layer_map.items():
                if isinstance(pattern_or_list, list):
                    for pattern in pattern_or_list:
                        directory_map_override[pattern] = layer_name
                else:
                    directory_map_override[pattern_or_list] = layer_name

            registry_config = LayerRegistryConfig(
                project_type=project_type,
                directory_map=directory_map_override,
                base_class_map=_invert_map(cls._instance.config.get("base_class_map", {})),
                module_map=_invert_map(cls._instance.config.get("module_map", {})),
            )

            cls._instance.set_registry(LayerRegistry(config=registry_config))
        return cls._instance

    def set_registry(self, registry: LayerRegistry) -> None:
        """Set the layer registry."""
        self._registry = registry

    def load_config(self) -> None:
        """Find and load pyproject.toml configuration."""
        current_path = Path.cwd()
        root_path = Path("/")

        while current_path != root_path:
            config_file = current_path / "pyproject.toml"
            if config_file.exists():
                try:
                    with open(config_file, "rb") as f:
                        data = toml.load(f)
                        tool_section = data.get("tool", {})

                        # 1. Check for [tool.clean-arch] (New)
                        self._config = tool_section.get("clean-arch", {})

                        # 2. Check for [tool.clean-architecture-linter] (Oldest Legacy)
                        # We keep this strictly for smooth upgrades, but undocumented.
                        if not self._config:
                            self._config = tool_section.get("clean-architecture-linter", {})

                        if self._config:
                            return
                except (IOError, OSError):
                    # Keep looking in parent dirs
                    pass
            current_path = current_path.parent

    @property
    def config(self) -> Dict[str, Any]:
        """Return the loaded configuration."""
        return self._config

    @property
    def registry(self) -> LayerRegistry:
        """Return the layer registry."""
        if self._registry is None:
            # Fallback for unconfigured cases (e.g. tests without config loading)
            self._registry = LayerRegistry(LayerRegistryConfig(project_type="generic"))
        return self._registry

    def get_layer_for_module(self, module_name: str, file_path: str = "") -> Optional[str]:
        """Get the architectural layer for a module/file."""
        # Check explicit config first
        if "layers" in self._config:
            layers = sorted(
                self._config["layers"],
                key=lambda x: len(x.get("module", "")),
                reverse=True,
            )
            match = next(
                (layer.get("name") for layer in layers if module_name.startswith(layer.get("module", ""))),
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
    def infrastructure_modules(self) -> set[str]:
        """Return list of modules considered infrastructure."""
        return set(self._config.get("infrastructure_modules", []))

    @property
    def raw_types(self) -> set[str]:
        """Return list of type names considered raw/infrastructure."""
        return set(self._config.get("raw_types", []))


def _invert_map(config_map: Dict[str, Any]) -> Dict[str, str]:
    """Invert config map (Layer -> Items) to (Item -> Layer)."""
    inverted = {}
    for layer_name, item_or_list in config_map.items():
        if isinstance(item_or_list, list):
            for item in item_or_list:
                inverted[item] = layer_name
        else:
            inverted[item_or_list] = layer_name
    return inverted
