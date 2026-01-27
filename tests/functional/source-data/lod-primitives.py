from collections.abc import Iterable, Iterator
from dataclasses import dataclass


@dataclass
class Locatable:
    """Minimal stand-in for Violation-like objects with location: str (path:line)."""
    location: str


def parse_location_from_obj(loc: Locatable) -> None:
    # Allowed: .location is string-typed (path:line or path:line:column); .split is str method.
    # Inference often fails for attrs on params; "location" fallback treats it as primitive.
    _ = loc.location.split(":")


def typing_collections_trust(items: Iterable[str]) -> None:
    # Allowed: collections.abc/typing logic is considered 'builtins'
    it: Iterator[str] = iter(items)
    # next(it) returns str, upper() and strip() are str methods
    _res: str = next(it).upper().strip()

class CustomService:
    def get_version(self) -> str:
        return "1.0"
    def is_active(self) -> bool:
        return True

def primitive_chain_exemption(service: CustomService) -> None:
    # Allowed: get_version returns 'str' (primitive)
    # The next member '.upper()' is on a primitive, so it's safe.
    _rev: str = service.get_version().upper().strip()
    # Allowed: is_active returns 'bool'
    if service.is_active():
        pass
