import pytest
from pathlib import Path
from unittest.mock import MagicMock
from clean_architecture_linter.fixer import (
    _fix_lifecycle_return_types,
    _fix_domain_immutability,
    _fix_type_integrity,
    _fix_structural_integrity,
    excelsior_fix
)

def test_fix_lifecycle_return_types():
    content: str = """
class Foo:
    def __init__(self, x):
        self.x = x
    def setUp(self):
        pass
    def tearDown(self):
        pass
    def test_logic(self):
        pass
"""
    expected: str = """
class Foo:
    def __init__(self, x) -> None:
        self.x = x
    def setUp(self) -> None:
        pass
    def tearDown(self) -> None:
        pass
    def test_logic(self) -> None:
        pass
"""
    assert _fix_lifecycle_return_types(content).strip() == expected.strip()

def test_fix_lifecycle_return_types_already_present():
    content: str = "def __init__(self) -> None: pass"
    assert _fix_lifecycle_return_types(content) == content

def test_fix_domain_immutability():
    # Only applies if file path contains 'domain'
    path = Path("src/domain/entities.py")
    content: str = "@dataclass\nclass Entity:\n    id: str"
    expected: str = "@dataclass(frozen=True)\nclass Entity:\n    id: str"
    assert _fix_domain_immutability(path, content).strip() == expected.strip()

def test_fix_domain_immutability_ignored_path():
    path = Path("src/adapters/foo.py")
    content: str = "@dataclass\nclass Foo:..."
    assert _fix_domain_immutability(path, content) == content

def test_fix_domain_immutability_existing_args():
    path = Path("domain/foo.py")
    content: str = "@dataclass(eq=True)\nclass Foo:..."
    expected: str = "@dataclass(eq=True, frozen=True)\nclass Foo:..."
    assert _fix_domain_immutability(path, content) == expected

def test_fix_type_integrity_inserts_import():
    content: str = """
def foo(x: Optional[str]) -> Any:
    pass
"""
    result = _fix_type_integrity(content)
    assert "from typing import Any, Optional" in result
    assert "def foo(x: Optional[str]) -> Any:" in result

def test_fix_type_integrity_updates_import():
    content: str = """from typing import List

def foo(x: Optional[str]) -> List[str]:
    pass
"""
    expected: str = """from typing import List, Optional

def foo(x: Optional[str]) -> List[str]:
    pass
"""
    # Note: The implementation sorts imports, so order is deterministic
    assert _fix_type_integrity(content) == expected

def test_structural_integrity_creates_init(tmp_path):
    telemetry = MagicMock()
    # Create a nested structure: pkg/sub/file.py
    pkg = tmp_path / "pkg"
    sub = pkg / "sub"
    sub.mkdir(parents=True)
    (sub / "file.py").touch()
    (pkg / "dummy.py").touch() # Ensure root also gets init

    _fix_structural_integrity(telemetry, pkg, tmp_path)

    assert (sub / "__init__.py").exists()
    assert (pkg / "__init__.py").exists()

def test_structural_integrity_creates_py_typed(tmp_path):
    telemetry = MagicMock()
    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    (pkg / "__init__.py").touch()

    _fix_structural_integrity(telemetry, pkg, tmp_path)
    assert (pkg / "py.typed").exists()

def test_excelsior_fix_integration(tmp_path):
    telemetry = MagicMock()
    target_file = tmp_path / "domain" / "entity.py"
    target_file.parent.mkdir()

    original_content: str = """
from dataclasses import dataclass

@dataclass
class MyEntity:
    def __init__(self, name) -> None:
        self.name = name
"""
    target_file.write_text(original_content, encoding="utf-8")

    excelsior_fix(telemetry, str(tmp_path))

    new_content = target_file.read_text(encoding="utf-8")

    # Check 1: frozen=True added (path conatins 'domain')
    assert "@dataclass(frozen=True)" in new_content
    # Check 2: -> None added
    assert "def __init__(self, name) -> None:" in new_content
    # Check 3: structural fix (__init__.py created in domain folder)
    assert (tmp_path / "domain" / "__init__.py").exists()
