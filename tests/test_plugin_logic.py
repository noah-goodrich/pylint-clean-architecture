import os
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def test_env(tmp_path_factory):
    root = tmp_path_factory.mktemp("snowfort_test")

    # Create pyproject.toml
    toml_content = """
[tool.clean-architecture-linter]
visibility_enforcement = true
forbidden_prefixes = ["db", "requests"]
layers = [
    { name = "Domain", module = "pkg.domain" },
    { name = "Adapters", module = "pkg.adapters" },
    { name = "Interface", module = "pkg.ui" }
]
"""
    with open(root / "pyproject.toml", "w") as f:
        f.write(toml_content)

    # Create package structure
    pkg = root / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").touch()

    # Domain Layer (Strict)
    domain = pkg / "domain"
    domain.mkdir()
    (domain / "__init__.py").touch()

    # Adapters Layer (Permissive)
    adapters = pkg / "adapters"
    adapters.mkdir()
    (adapters / "__init__.py").touch()

    return root


def run_pylint(file_path, root_dir):
    """Run pylint via subprocess to avoid SystemExit issues."""
    import subprocess

    # Ensure plugin is in pythonpath
    plugin_path = Path("/development/pylint-clean-architecture/src").resolve()
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{plugin_path}:{env.get('PYTHONPATH', '')}"

    cmd = [
        "pylint",
        str(file_path),
        "--load-plugins=clean_architecture_linter",
        "--disable=all",
        "--enable=W9003,W9004,W9005,W9006,W9007",
        "--score=n",
        "--persistent=n",
    ]

    # We expect failure (exit code non-zero) if violations are found,
    # so we don't check_returncode=True immediately.
    result = subprocess.run(cmd, cwd=root_dir, capture_output=True, text=True, env=env)
    return result.stdout


def test_w9003_protected_access(test_env):
    """Test W9003: Protected member access."""
    code = """
class User:
    def __init__(self):
        self._secret = 'shh'

def access_secret():
    u = User()
    print(u._secret)
"""
    f = test_env / "pkg" / "domain" / "protected.py"
    f.write_text(code)

    output = run_pylint(f, test_env)
    assert "W9003" in output
    assert 'Access to protected member "_secret"' in output


def test_w9004_resource_access_violation(test_env):
    """Test W9004 in Domain layer (Should fail)."""
    code = """
import db

def save():
    db.execute("SELECT *")
"""
    f = test_env / "pkg" / "domain" / "resource_bad.py"
    f.write_text(code)

    output = run_pylint(f, test_env)
    assert "W9004" in output
    assert "clean-arch-resources" in output


def test_w9004_resource_access_allowed(test_env):
    """Test W9004 in Adapters layer (Should pass)."""
    code = """
import db

def save():
    db.execute("SELECT *")
"""
    f = test_env / "pkg" / "adapters" / "resource_ok.py"
    f.write_text(code)

    output = run_pylint(f, test_env)
    assert "W9004" not in output


def test_w9005_delegation_anti_pattern(test_env):
    """Test W9005: Delegation anti-pattern."""
    code = """
def handle(x):
    if x == 1:
        return do_a()
    elif x == 2:
        return do_b()
    else:
        return do_c()
"""
    f = test_env / "pkg" / "domain" / "delegation.py"
    f.write_text(code)

    output = run_pylint(f, test_env)
    assert "W9005" in output
    assert "Delegation Anti-Pattern" in output


def test_w9006_law_of_demeter(test_env):
    """Test W9006: Law of Demeter."""
    code = """
def get_stuff(obj):
    return obj.a.b.c()
"""
    f = test_env / "pkg" / "domain" / "demeter.py"
    f.write_text(code)

    output = run_pylint(f, test_env)
    assert "W9006" in output
    assert "clean-arch-demeter" in output
