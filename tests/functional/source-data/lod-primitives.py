from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path


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


# --- Real-world patterns that must NOT be flagged (W9006 false positive regression tests) ---

@dataclass
class Messageable:
    message: str


def message_find(obj: Messageable) -> int:
    # Allowed: .message is str; .find is str method. (governance_comments.py:71)
    return obj.message.find("(")


def message_slice(obj: Messageable, start: int, end: int) -> str:
    # Allowed: subscription on str is not a call; no LoD. (governance_comments.py:72)
    return obj.message[start:end]


@dataclass
class WithBlocked:
    blocked_by: str


def blocked_by_upper(obj: WithBlocked) -> str:
    # Allowed: .blocked_by is str; .upper is str method. (reporters.py:30)
    return obj.blocked_by.upper()


@dataclass
class WithMeta:
    metadata: dict


def metadata_get(node: WithMeta, key: str) -> object:
    # Allowed: .metadata is dict; .get is dict method. (transformers.py:378)
    return node.metadata.get(key, None)


def dict_get_get(d: dict) -> object:
    # Allowed: d.get("a",{}) returns dict; .get on dict is primitive. (scaffolder.py:248)
    return d.get("a", {}).get("b")


def str_splitlines(s: str) -> list:
    # Allowed: one-level chain only; also str.splitlines is primitive. (libcst:27)
    return s.splitlines()


class QNameReturnsStr:
    def qname(self) -> str:
        return self.__class__.__qualname__


def qname_endswith(obj: QNameReturnsStr, suffix: str) -> bool:
    # Allowed: .qname() returns str; .endswith is str method. (astroid_gateway.py:604)
    return obj.qname().endswith(suffix)


def path_name_startswith(p: Path, prefix: str) -> bool:
    # Allowed: Path.name is str; .startswith is str method. (structure.py:160)
    return p.name.startswith(prefix)


class OneLevel:
    def foo(self) -> None:
        return None


def one_level_call(o: OneLevel) -> None:
    # Allowed: one-level chain (o.foo) is below LoD threshold. (apply_fixes.py:320)
    o.foo()
