"""
Stellar Engineering Command: Visual Telemetry Constants
"""

# EXCELSIOR: ANSI Red (\033[31m)
_RED: str = "\033[31m"
_RESET: str = "\033[0m"
_EXCELSIOR_ART = r"""
    _______  ________________   _____ ________  ____
   / ____/ |/ / ____/ ____/ /  / ___//  _/ __ \/ __ \
  / __/  |   / /   / __/ / /   \__ \ / // / / / /_/ /
 / /___ /   / /___/ /___/ /______/ // // /_/ / _, _/
/_____//_/|_\____/_____/_____/____/___/\____/_/ |_|
"""
EXCELSIOR_BANNER = _RED + _EXCELSIOR_ART + _RESET


DEFAULT_INTERNAL_MODULES: frozenset[str] = frozenset(
    {
        "domain",
        "dto",
        "use_cases",
        "protocols",
        "models",
        "telemetry",
        "results",
        "entities",
        "policies",
        "interfaces",
        "exceptions",
        "types",
        "layer_registry",
        "config",
        "gateways",
    }
)

BUILTIN_TYPE_MAP: dict[str, str] = {
    "str": "builtins.str",
    "int": "builtins.int",
    "float": "builtins.float",
    "bool": "builtins.bool",
    "bytes": "builtins.bytes",
    "list": "builtins.list",
    "dict": "builtins.dict",
    "tuple": "builtins.tuple",
    "set": "builtins.set",
    "Optional": "builtins.Optional",
    "Union": "builtins.Union",
    "List": "builtins.list",
    "Dict": "builtins.dict",
    "Set": "builtins.set",
}
