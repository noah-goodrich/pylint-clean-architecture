"""Layer registry for convention-based layer resolution."""

import re
from typing import Optional


class LayerRegistry:
    """
    Registry to resolve architectural layers based on conventions.

    Strategies:
    1. Class name suffix matching (*UseCase, *Repository, etc.)
    2. Directory path matching (/use_cases/, /infrastructure/, etc.)
    3. Project-type presets (cli_app, fastapi_sqlalchemy)
    """

    # Pre-defined layer constants
    LAYER_USE_CASE = "UseCase"
    LAYER_DOMAIN = "Domain"
    LAYER_INFRASTRUCTURE = "Infrastructure"
    LAYER_INTERFACE = "Interface"

    # Default mappings
    DEFAULT_SUFFIX_MAP = {
        r".*UseCase$": LAYER_USE_CASE,
        r".*Interactor$": LAYER_USE_CASE,
        r".*Orchestrator$": LAYER_USE_CASE,
        r".*Query$": LAYER_USE_CASE,
        r".*Entity$": LAYER_DOMAIN,
        r".*VO$": LAYER_DOMAIN,
        r".*ValueObject$": LAYER_DOMAIN,
        r".*Repository$": LAYER_INFRASTRUCTURE,
        r".*Adapter$": LAYER_INFRASTRUCTURE,
        r".*Client$": LAYER_INFRASTRUCTURE,
        r".*Gateway$": LAYER_INFRASTRUCTURE,
        r".*Controller$": LAYER_INTERFACE,
        r".*Router$": LAYER_INTERFACE,
        r".*Command$": LAYER_INTERFACE,  # CLI commands
    }

    DEFAULT_DIRECTORY_MAP = {
        r"(?:^|.*/)use_cases?(/.*)?$": LAYER_USE_CASE,
        r"(?:^|.*/)orchestrators?(/.*)?$": LAYER_USE_CASE,
        r"(?:^|.*/)domain(/.*)?$": LAYER_DOMAIN,
        r"(?:^|.*/)entities(/.*)?$": LAYER_DOMAIN,
        r"(?:^|.*/)infrastructure(/.*)?$": LAYER_INFRASTRUCTURE,
        r"(?:^|.*/)adapters?(/.*)?$": LAYER_INFRASTRUCTURE,
        r"(?:^|.*/)io(/.*)?$": LAYER_INFRASTRUCTURE,
        r"(?:^|.*/)interface(/.*)?$": LAYER_INTERFACE,
        r"(?:^|.*/)ui(/.*)?$": LAYER_INTERFACE,
        r"(?:^|.*/)api(/.*)?$": LAYER_INTERFACE,
        r"(?:^|.*/)cli(/.*)?$": LAYER_INTERFACE,
        r"(?:^|.*/)commands?(/.*)?$": LAYER_INTERFACE,
        r"(?:^|.*/)cli\.py$": LAYER_INTERFACE,
        r"(?:^|.*/)bootstrap\.py$": LAYER_INTERFACE,
        r"(?:^|.*/)main\.py$": LAYER_INTERFACE,
    }

    def __init__(
        self,
        project_type: str = "generic",
        suffix_map: Optional[dict] = None,
        directory_map: Optional[dict] = None,
    ):
        self.project_type = project_type

        # Initialize with defaults copy
        self.suffix_map = self.DEFAULT_SUFFIX_MAP.copy()
        self.directory_map = self.DEFAULT_DIRECTORY_MAP.copy()

        # Update with config overrides
        if suffix_map:
            self.suffix_map.update(suffix_map)
        if directory_map:
            # When mapping "services" -> "UseCase" in TOML, we need to convert simple name to regex
            # or expect full regex? The user prompt implies simpler mapping "services" = "use_cases" style
            # But implementing full regex power is better.
            # However, prompt verification says: "uses 'services' instead of 'use_cases'"
            # So if user provides "services": "UseCase", we should support that.
            # But the map contains regexes as keys.
            # If the key provided by config is simple (alphanumeric), we wrap it in standard dir regex.
            # If it looks like regex, we use it as is.
            for patterns, layer in directory_map.items():
                # Handling simple directory names to regex conversion for ease of use
                if re.match(r"^[a-zA-Z0-9_]+$", patterns):
                    regex = rf"(?:^|.*/){patterns}(/.*)?$"
                    self.directory_map[regex] = layer
                else:
                    self.directory_map[patterns] = layer

        self._apply_preset()

    def _apply_preset(self):
        """Apply project-type-specific rules."""
        presets = {
            "fastapi_sqlalchemy": {
                r".*Model$": self.LAYER_INFRASTRUCTURE,
                r".*Schema$": self.LAYER_INTERFACE,
            },
            "cli_app": {
                r".*Command$": self.LAYER_INTERFACE,
                r".*Orchestrator$": self.LAYER_USE_CASE,
            },
        }

        if self.project_type in presets:
            self.suffix_map.update(presets[self.project_type])

    def resolve_layer(self, node_name: str, file_path: str) -> Optional[str]:
        """
        Resolve the architectural layer for a node.

        Args:
            node_name: Class or function name
            file_path: Full file path or module name

        Returns:
            Layer name or None if unresolved
        """
        # 1. Check class name suffix
        if node_name:
            for pattern, layer in self.suffix_map.items():
                if re.match(pattern, node_name):
                    return layer

        # 2. Check path/module (Monorepo support)
        # Normalize: replace backslashes and dots (except for .py extension)
        normalized_path = file_path.replace("\\", "/")
        if normalized_path.endswith(".py"):
            normalized_path = normalized_path[:-3]
        normalized_path = normalized_path.replace(".", "/")

        # Prefix with / for pattern matching if not already
        if not normalized_path.startswith("/"):
            normalized_path = "/" + normalized_path

        for pattern, layer in self.directory_map.items():
            if re.search(pattern, normalized_path):
                return layer

        return None
