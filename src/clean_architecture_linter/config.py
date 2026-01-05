"""Configuration loader for linter settings."""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import tomli as toml  # type: ignore[import-not-found]
except ImportError:
    # Python 3.11+ has tomllib
    import tomllib as toml  # type: ignore[import-not-found]

from clean_architecture_linter.layer_registry import LayerRegistry


class ConfigurationLoader:
    """
    Singleton that loads linter configuration from pyproject.toml.

    Looks for [tool.snowarch] section.
    """

    _instance = None
    _config: Dict[str, Any] = {}
    _registry: Optional[LayerRegistry] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigurationLoader, cls).__new__(cls)
            cls._instance.load_config()
            project_type = cls._instance.config.get("project_type", "generic")
            cls._instance.set_registry(LayerRegistry(project_type))
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
                        # Check for new [tool.snowarch] OR legacy [tool.clean-architecture-linter]
                        self._config = data.get("tool", {}).get("snowarch", {})
                        if not self._config:
                            self._config = data.get("tool", {}).get("clean-architecture-linter", {})
                        if self._config:
                            return
                except (IOError, OSError):
                    # Keep looking in parent dirs
                    pass
            current_path = current_path.parent

    @property
    def config(self) -> Dict[str, Any]:
        return self._config

    @property
    def registry(self) -> LayerRegistry:
        if self._registry is None:
            self._registry = LayerRegistry("generic")
        return self._registry

    def get_layer_for_module(self, module_name: str, file_path: str = "") -> Optional[str]:
        """Get the architectural layer for a module/file."""
        # Check explicit config first
        if "layers" in self._config:
            layers = sorted(self._config["layers"], key=lambda x: len(x.get("module", "")), reverse=True)
            match = next(
                (layer.get("name") for layer in layers if module_name.startswith(layer.get("module", ""))), None
            )
            if match:
                return match

        # Fall back to convention registry
        return self.registry.resolve_layer("", file_path or module_name)

    def get_resource_access_methods(self) -> Dict[str, List[str]]:
        """Get configured resource access methods (legacy)."""
        return self._config.get("resource_access_methods", {})

    @property
    def visibility_enforcement(self) -> bool:
        """Whether to enforce protected member visibility."""
        return self._config.get("visibility_enforcement", True)  # Default ON
