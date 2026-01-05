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

    # Priority 1: Class name suffixes
    SUFFIX_MAP = {
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

    # Priority 2: Directory patterns
    DIRECTORY_MAP = {
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

    def __init__(self, project_type: str = "generic"):
        self.project_type = project_type
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
            self.SUFFIX_MAP.update(presets[self.project_type])

    def resolve_layer(self, node_name: str, file_path: str) -> Optional[str]:
        """
        Resolve the architectural layer for a node.

        Args:
            node_name: Class or function name
            file_path: Full file path

        Returns:
            Layer name or None if unresolved
        """
        # 1. Check class name suffix
        if node_name:
            for pattern, layer in self.SUFFIX_MAP.items():
                if re.match(pattern, node_name):
                    return layer

        # 2. Check directory path
        normalized_path = file_path.replace("\\", "/")
        for pattern, layer in self.DIRECTORY_MAP.items():
            if re.match(pattern, normalized_path):
                return layer

        return None
