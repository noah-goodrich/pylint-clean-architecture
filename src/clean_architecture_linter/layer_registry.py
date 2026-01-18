"""Layer registry for convention-based layer resolution."""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, ClassVar

logger = logging.getLogger(__name__)


@dataclass
class LayerRegistryConfig:
    """Configuration for LayerRegistry."""

    project_type: str = "generic"
    suffix_map: dict | None = field(default_factory=dict)
    directory_map: dict | None = field(default_factory=dict)
    base_class_map: dict | None = field(default_factory=dict)
    module_map: dict | None = field(default_factory=dict)


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
    DEFAULT_SUFFIX_MAP: ClassVar[dict[str, str]] = {
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

    DEFAULT_DIRECTORY_MAP: ClassVar[dict[str, str]] = {
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

    def __init__(self, config: LayerRegistryConfig | None = None):
        if config is None:
            config = LayerRegistryConfig()

        self.project_type = config.project_type

        # Initialize with defaults copy
        self.suffix_map = self.DEFAULT_SUFFIX_MAP.copy()
        self.directory_map = self.DEFAULT_DIRECTORY_MAP.copy()
        self.base_class_map = config.base_class_map or {}
        self.module_map = config.module_map or {}

        # Update with config overrides
        if config.suffix_map:
            self.suffix_map.update(config.suffix_map)
        if config.directory_map:
            # Handle simple directory names to regex conversion
            for patterns, layer in config.directory_map.items():
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

    def get_layer_for_class_node(self, node) -> str | None:
        """
        Get layer for a class node using name and inheritance.
        1. Check suffix match on class name.
        2. Check inheritance via ancestors.
        """
        if not node:
            return None

        # 1. Direct Name Match (Suffix Map)
        # Note: The user mentioned 'class_map' but we use suffix_map for name patterns
        for pattern, layer in self.suffix_map.items():
            if re.match(pattern, node.name):
                return layer

        # 2. Inheritance Check
        return self.resolve_by_inheritance(node)

    def resolve_by_inheritance(self, node) -> str | None:
        """Resolve layer by checking base classes."""
        if not node:
            return None

        try:
            # Check ancestors if available (astroid nodes)
            if hasattr(node, "ancestors"):
                for ancestor in node.ancestors():
                    if ancestor.name in self.base_class_map:
                        return self.base_class_map[ancestor.name]
        except Exception as e:
            logger.debug(f"LayerRegistry: Error resolving inheritance for node {getattr(node, 'name', '?')}: {e}")
            return None
        return None

    def resolve_layer(self, node_name: str, file_path: str, node: Any | None = None) -> str | None:
        """
        Resolve the architectural layer for a node.
        """
        # 1. Base Class Map (Inheritance)
        if node:
            layer = self.resolve_by_inheritance(node)
            if layer:
                return layer

        # 2. Module Map (Specific files)
        file_name = file_path.split("/")[-1]
        if file_name in self.module_map:
            return self.module_map[file_name]

        # 3. Directory Map
        layer = self._resolve_by_directory(file_path)
        if layer:
            return layer

        # 4. Suffix Map
        if node_name:
            return self._resolve_by_suffix(node_name)

        return None

    def _resolve_by_directory(self, file_path: str) -> str | None:
        """Check path/module for directory matching."""
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

    def _resolve_by_suffix(self, node_name: str) -> str | None:
        """Check node name against suffix patterns."""
        for pattern, layer in self.suffix_map.items():
            if re.match(pattern, node_name):
                return layer
        return None
