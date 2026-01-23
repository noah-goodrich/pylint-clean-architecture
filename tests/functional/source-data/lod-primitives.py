from typing import Iterable, Iterator

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
