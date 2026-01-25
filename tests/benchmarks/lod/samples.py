from typing import Dict, List, Set


def exhaustive_string_methods():
    s: str = "hello"
    s.upper()
    s.lower()
    s.strip()
    s.split(",")
    s.replace("h", "j")
    s.startswith("h")
    s.endswith("o")
    s.find("e")
    s.join(["a", "b"])
    s.encode("utf-8")
    s.isdigit()
    s.isalpha()
    s.isspace()
    s.capitalize()
    s.title()
    s.zfill(5)
    s.format(name="world")
    s.index("e")
    s.count("l")

def exhaustive_list_methods():
    lst: List[str] = ["a"]
    lst.append("b")
    lst.extend(["c", "d"])
    lst.insert(0, "z")
    lst.remove("a")
    lst.pop()
    lst.clear()
    lst.index("b")
    lst.count("b")
    lst.sort()
    lst.reverse()
    lst.copy()

def exhaustive_dict_methods():
    d: Dict[str, int] = {"a": 1}
    d.get("a")
    d.items()
    d.keys()
    d.values()
    d.update({"b": 2})
    d.pop("a")
    d.popitem()
    d.clear()
    d.copy()
    d.setdefault("c", 3)
    # Testing fromkeys (class method)
    dict.fromkeys(["x", "y"], 0)

def exhaustive_set_methods():
    s: Set[int] = {1, 2, 3}
    s.add(4)
    s.remove(1)
    s.discard(2)
    s.pop()
    s.clear()
    s.copy()
    s.union({5})
    s.intersection({3, 4})
    s.difference({3})
    s.symmetric_difference({4})
    s.update({6})
    s.intersection_update({4, 5})
    s.difference_update({6})
    s.symmetric_difference_update({5})
    s.isdisjoint({7})
    s.issubset({1, 2, 3, 4, 5, 6})
    s.issuperset({3})

def exhaustive_int_float_methods():
    i: int = 10
    i.bit_length()
    i.to_bytes(2, "big")
    int.from_bytes(b"\x00\x0a", "big")

    f = 10.5
    f.is_integer()
    f.as_integer_ratio()
    f.hex()
    float.fromhex("0x1.5p+3")

def internal_safe_cases():
    # Covering mod_file.startswith(self._stdlib_path)
    mod_file = str("some/path")
    prefix: str = "/usr/lib/python"
    mod_file.startswith(prefix)

    # Covering visited.add(expr_id)
    visited = set()
    expr_id: int = 12345
    visited.add(expr_id)
