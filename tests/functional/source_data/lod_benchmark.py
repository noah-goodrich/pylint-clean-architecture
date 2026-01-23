"""
Standard-First LoD Benchmark.
This file must pass Mypy strict and Pylint with 0 warnings.
"""
import os
import re
import json
from typing import Dict, List, Optional
from dataclasses import dataclass

# Category 1: Primitives (LEGO Bricks)
def test_primitives_safety() -> None:
    data: Dict[str, int] = {"a": 1, "b": 2}

    # Trusted transformation (Primitive -> Primitive/Collection)
    keys = data.keys()
    vals = data.values()

    # Chaining on primitives is allowed because they are safe roots
    text: str = " hello world "
    clean_text = text.strip().upper().replace("WORLD", "UNIVERSE")

    # List operations
    items: List[int] = [1, 2, 3]
    items.append(4)
    items.extend([5, 6])


# Category 2: Standard Library (Trusted Authorities)
def test_stdlib_safety() -> None:
    # os chain
    path: str = os.path.join("root", "src", "file.py")
    norm: str = os.path.normpath(path)

    # re chain
    pattern = re.compile(r"\d+")
    match = pattern.search("12345")
    if match:
        # Match object is trusted because it comes from a Trusted Authority (re)
        group = match.group(0)

    # json
    serialized = json.dumps({"a": 1})
    deserialized = json.loads(serialized)


# Category 3: Domain Objects (Must respect Demeter)
@dataclass(frozen=True)
class Address:
    street: str
    city: str

@dataclass(frozen=True)
class User:
    name: str
    address: Address

    def get_address(self) -> Address:
        return self.address

def test_demeter_violations(user: User) -> None:
    # Valid: One dot
    addr = user.address
    print(addr.city)

    # Valid: Method delegation
    addr2 = user.get_address()

    # Violation: Chaining through properties (stranger)
    # user.address.city  <-- This would fail W9006

    # Violation: Chaining methods
    # user.get_address().city <-- This would fail W9006 unless Address is treated as safe/value object
