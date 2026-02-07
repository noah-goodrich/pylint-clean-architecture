"""Load [tool.clean-arch] and [tool] from pyproject.toml. Infrastructure I/O only."""

import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib as toml_lib
else:
    try:
        import tomli as toml_lib  # type: ignore[import-not-found]
    except ImportError:
        toml_lib = None  # type: ignore[assignment]


class ConfigFileLoader:
    """
    Loads config from pyproject.toml. No top-level functions (W9018).
    """

    @staticmethod
    def load_config_from_fs() -> tuple[dict[str, object], dict[str, object]]:
        """Load [tool.clean-arch] and [tool] from pyproject.toml. Returns (config_dict, tool_section)."""
        current_path = Path.cwd()
        root_path = Path("/")
        empty: dict[str, object] = {}
        if toml_lib is None:
            return (empty, empty)
        while current_path != root_path:
            config_file = current_path / "pyproject.toml"
            if config_file.exists():
                try:
                    with config_file.open("rb") as f:
                        data = toml_lib.load(f)
                    tool_section = data.get("tool", {}) or {}
                    config_dict = tool_section.get("clean-arch", {}) or tool_section.get(
                        "clean-architecture-linter", {}
                    )
                    return (config_dict, tool_section)
                except OSError:
                    pass
            current_path = current_path.parent
        return (empty, empty)
