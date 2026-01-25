"""
Exhaustive Law of Demeter Benchmark Samples.
Used by test_lod_benchmarks.py for True Inference verification.
"""

import json
from datetime import datetime
from pathlib import Path


# 1. ALLOWED: Standard Library Chaining (str, Path, json, etc.)
def allowed_str_chain(name: str) -> str:
    # str -> str -> str (Allowed)
    return name.lower().strip().replace(" ", "_")

def allowed_path_chain(p: Path) -> str:
    # Path -> Path -> str (Allowed)
    return str(p.parent.absolute())

def allowed_json_chain(data_str: str) -> str:
    # json.loads -> dict -> str (Allowed if dict is in allowed_lod_modules)
    return json.loads(data_str).get("key", "default").strip()

def allowed_datetime_chain() -> int:
    # datetime -> date -> int (Allowed)
    return datetime.now().date().year

# 2. ALLOWED: Member Access (Level 1)
class Entity:
    def __init__(self, name: str) -> None:
        self.name = name

def allowed_level_1(e: Entity) -> str:
    return e.name

# 3. FORBIDDEN: Deep Chaining on Custom Objects
class Child:
    def get_name(self) -> str:
        return "child"

class Parent:
    def __init__(self) -> None:
        self.child = Child()
    def get_child(self) -> Child:
        return self.child

def forbidden_deep_chain(p: Parent) -> str:
    # Parent -> Child -> str (Violation: 2 levels)
    # Clean Fix: p.get_child_name()
    return p.get_child().get_name()

# 4. FORBIDDEN: Deep Member Access
class DeepEntity:
    def __init__(self) -> None:
        self.child = Child()

def forbidden_member_chain(de: DeepEntity) -> str:
    # DeepEntity -> Child -> str (Violation)
    return de.child.get_name()

# 5. COMPLEX: Mixed Chains (Should fail if any part is a custom deep chain)
def forbidden_mixed_chain(p: Parent) -> str:
    # Parent -> Child -> str -> str (Violation happens at Child.get_name())
    return p.get_child().get_name().upper()
