import json
import pathlib
from typing import Optional


def std_lib_exemption() -> None:
    p: pathlib.Path = pathlib.Path("config.json")
    # Allowed: pathlib is StdLib
    _dirs: pathlib.Path = p.parent.parent.absolute()

    # Allowed: json is StdLib
    json_str: str = "{}"
    data: Optional[str] = json.loads(json_str).get("key")
    if data:
        _res: str = data.strip()
