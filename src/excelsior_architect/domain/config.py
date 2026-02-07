"""Configuration loader for linter settings. Immutable value object created by Infrastructure."""

from __future__ import annotations

import astroid

from excelsior_architect.domain.layer_registry import LayerRegistry, LayerRegistryConfig


class ConfigurationLoader:
    """
    Immutable configuration for linter settings.

    Created by Infrastructure from (config_dict, tool_section). Domain does not
    read the filesystem; Infrastructure calls ConfigFileLoader.load_config_from_fs()
    and constructs ConfigurationLoader(config_dict, tool_section) at composition root.
    """

    def __init__(
        self,
        config_dict: dict[str, object],
        tool_section: dict[str, object],
    ) -> None:
        """Set config once at construction. No mutable class or instance state after init."""
        self._config = config_dict
        self._tool_section = tool_section
        if config_dict:
            self.validate_config(config_dict)

        raw_layer_map = self._config.get("layer_map", {})
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

        base_class_map = self._config.get("base_class_map", {})
        module_map = self._config.get("module_map", {})
        registry_config = LayerRegistryConfig(
            project_type=str(self._config.get("project_type", "generic")),
            directory_map=directory_map_override,
            base_class_map=ConfigurationLoader.invert_map(base_class_map),
            module_map=ConfigurationLoader.invert_map(module_map),
        )
        self._registry = LayerRegistry(config=registry_config)

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
        return self._config

    @property
    def audit_exclude_paths(self) -> list[str]:
        """
        Path fragments to exclude from the main audit.

        Intended for deliberate-violation fixtures like tests/bait/.
        """
        raw = self._config.get("audit_exclude_paths", [])
        if isinstance(raw, list):
            return [str(x) for x in raw if isinstance(x, str)]
        return []

    # Contract Integrity Configuration (W9201)

    @property
    def contract_integrity_config(self) -> dict[str, object]:
        """Return contract integrity configuration section."""
        raw = self._config.get("contract_integrity", {})
        return raw if isinstance(raw, dict) else {}

    @property
    def contract_integrity_require_protocol(self) -> list[str]:
        """Classes explicitly marked as requiring protocol."""
        raw = self.contract_integrity_config.get("require_protocol", [])
        return [str(x) for x in raw] if isinstance(raw, list) else []

    @property
    def contract_integrity_internal_implementation(self) -> list[str]:
        """Classes explicitly marked as internal implementation."""
        raw = self.contract_integrity_config.get("internal_implementation", [])
        return [str(x) for x in raw] if isinstance(raw, list) else []

    @property
    def contract_integrity_framework_base_classes(self) -> list[str]:
        """Framework base class patterns."""
        defaults = [
            "cst.CSTTransformer",
            "pylint.checkers.BaseChecker",
            "ast.NodeVisitor",
            "typing.TypedDict",
            "typing.NamedTuple",
        ]
        raw = self.contract_integrity_config.get("framework_base_classes", [])
        custom = [str(x) for x in raw] if isinstance(raw, list) else []
        return defaults + custom

    @property
    def contract_integrity_data_structure_patterns(self) -> list[str]:
        """Data structure name patterns."""
        defaults = ["*Row", "*Entry", "*Record", "*Data", "*Item", "*Result"]
        raw = self.contract_integrity_config.get("data_structure_patterns", [])
        custom = [str(x) for x in raw] if isinstance(raw, list) else []
        return defaults + custom

    @property
    def contract_integrity_helper_patterns(self) -> list[str]:
        """Helper/utility class name patterns."""
        defaults = ["_*", "*Helper", "*Utils", "*Utility"]
        raw = self.contract_integrity_config.get("helper_patterns", [])
        custom = [str(x) for x in raw] if isinstance(raw, list) else []
        return defaults + custom

    @property
    def contract_integrity_enable_di_container_detection(self) -> bool:
        """Whether to auto-detect classes returned by DI container."""
        return bool(self.contract_integrity_config.get("enable_di_container_detection", True))

    @property
    def contract_integrity_enable_cross_layer_detection(self) -> bool:
        """Whether to auto-detect cross-layer imports."""
        return bool(self.contract_integrity_config.get("enable_cross_layer_detection", True))

    @property
    def contract_integrity_enable_protocol_exists_detection(self) -> bool:
        """Whether to check if matching protocol exists."""
        return bool(self.contract_integrity_config.get("enable_protocol_exists_detection", True))

    @property
    def contract_integrity_services_require_protocol(self) -> bool:
        """Default for infrastructure/services/ directory."""
        return bool(self.contract_integrity_config.get("services_require_protocol", True))

    @property
    def contract_integrity_adapters_require_protocol(self) -> bool:
        """Default for infrastructure/adapters/ directory."""
        return bool(self.contract_integrity_config.get("adapters_require_protocol", True))

    @property
    def contract_integrity_gateways_require_protocol(self) -> bool:
        """Default for infrastructure/gateways/ directory."""
        return bool(self.contract_integrity_config.get("gateways_require_protocol", True))

    @property
    def contract_integrity_other_require_protocol(self) -> bool:
        """Default for other infrastructure classes."""
        return bool(self.contract_integrity_config.get("other_require_protocol", False))

    @property
    def registry(self) -> LayerRegistry:
        """Return the layer registry."""
        return self._registry

    def get_layer_for_module(self, module_name: str, file_path: str = "") -> str | None:
        """Get the architectural layer for a module/file."""
        # Check explicit config first
        if "layers" in self._config and isinstance(self._config["layers"], list):
            layers: list[dict[str, object]] = sorted(
                self._config["layers"],
                key=lambda x: len(
                    getattr(x, "get", lambda k, d: "")("module", "")),
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
            sorted_prefixes = sorted(
                self._config["layer_map"].keys(), key=len, reverse=True)
            for prefix in sorted_prefixes:
                if module_name.startswith(prefix):
                    return str(self._config["layer_map"][prefix])

        # Fall back to convention registry
        return self._registry.resolve_layer("", file_path or module_name)

    @property
    def visibility_enforcement(self) -> bool:
        """Whether to enforce protected member visibility."""
        val = self._config.get("visibility_enforcement", True)
        return bool(val)

    def _get_set(self, key: str, defaults: set[str] | None = None) -> set[str]:
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
        defaults = {"builtins", "typing", "importlib",
                    "pathlib", "ast", "os", "json", "yaml", "logging"}
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
        from excelsior_architect.domain.constants import DEFAULT_INTERNAL_MODULES
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

    def get_layer_for_class_node(self, node: astroid.nodes.ClassDef) -> str | None:
        """Delegate to registry for LoD compliance."""
        return self._registry.get_layer_for_class_node(node)

    def resolve_layer(
        self,
        node_name: str,
        file_path: str,
        node: astroid.nodes.NodeNG | None = None,
    ) -> str | None:
        """Delegate to registry for LoD compliance."""
        return self._registry.resolve_layer(node_name, file_path, node=node)

    # Ruff configuration methods

    def get_tool_section(self) -> dict[str, object]:
        """Return the full [tool] section from pyproject.toml (for ruff, mypy, excelsior, etc.)."""
        return self._tool_section

    def get_project_ruff_config(self) -> dict[str, object]:
        """Get [tool.ruff] configuration from pyproject.toml."""
        return self.get_tool_section().get("ruff", {})  # type: ignore

    def get_excelsior_ruff_config(self) -> dict[str, object]:
        """Get [tool.excelsior.ruff] configuration from pyproject.toml."""
        excelsior_section = self.get_tool_section().get("excelsior", {})
        if isinstance(excelsior_section, dict):
            return excelsior_section.get("ruff", {})  # type: ignore
        return {}

    def get_ruff_config(self) -> dict[str, object]:
        """Alias for get_project_ruff_config for backward compatibility."""
        return self.get_project_ruff_config()

    @property
    def ruff_enabled(self) -> bool:
        """Check if Ruff is enabled (default: True)."""
        excelsior_section = self.get_tool_section().get("excelsior", {})
        if isinstance(excelsior_section, dict):
            return bool(excelsior_section.get("ruff_enabled", True))
        return True  # Enabled by default

    @staticmethod
    def invert_map(config_map: object) -> dict[str, str]:
        """Invert config map (Layer -> Items) to (Item -> Layer). Public API."""
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
