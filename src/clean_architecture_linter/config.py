import tomllib
from typing import Any, Dict, List, Optional
from pathlib import Path

class ConfigurationLoader:
    _instance = None
    _config: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigurationLoader, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self) -> None:
        """
        Traverse up from CWD to find pyproject.toml and load [tool.clean-architecture-linter].
        """
        current_path = Path.cwd()
        root_path = Path("/")

        while current_path != root_path:
            config_file = current_path / "pyproject.toml"
            if config_file.exists():
                try:
                    with open(config_file, "rb") as f:
                        data = tomllib.load(f)
                        self._config = data.get("tool", {}).get("clean-architecture-linter", {})
                        if self._config:
                            return
                except Exception:
                    pass
            current_path = current_path.parent

        # If no config found, self._config remains empty.

    @property
    def config(self) -> Dict[str, Any]:
        return self._config

    def get_layer_config(self, module_name: str) -> Optional[Dict[str, Any]]:
        """
        Finds the layer configuration that matches the given module name.
        Matches by finding the most specific module prefix.
        """
        layers = self._config.get("layers", [])
        matched_layer = None
        longest_match = 0

        for layer in layers:
            prefix = layer.get("module", "")
            if module_name.startswith(prefix):
                if len(prefix) > longest_match:
                    longest_match = len(prefix)
                    matched_layer = layer

        return matched_layer

    def get_resource_access_methods(self) -> Dict[str, List[str]]:
        return self._config.get("resource_access_methods", {})

    @property
    def visibility_enforcement(self) -> bool:
        return self._config.get("visibility_enforcement", False)
