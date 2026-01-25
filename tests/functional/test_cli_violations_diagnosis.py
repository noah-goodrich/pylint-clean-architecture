"""Functional tests mirroring violations we should have caught in cli.py.

See .agent/cli_violations_diagnosis.md for why these matter.
"""

import os
import subprocess
from pathlib import Path

import pytest

PLUGIN_SRC = Path(__file__).resolve().parents[2] / "src"


def _run_pylint(file_path: Path, cwd: Path, enable: str = "clean-arch-dependency") -> str:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PLUGIN_SRC)
    cmd = [
        "pylint",
        str(file_path),
        "--load-plugins=clean_architecture_linter",
        "--disable=all",
        f"--enable={enable}",
        "--msg-template={path}:{line}: {msg_id} ({symbol})",
        "--score=n",
        "--persistent=n",
    ]
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env=env)
    return result.stdout + "\n" + result.stderr


@pytest.fixture
def project_interface_infra(tmp_path):
    """Minimal project with Interface and Infrastructure layers (layer_map)."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("""
[tool.clean-arch]

[tool.clean-arch.layer_map]
"pkg.interface" = "Interface"
"pkg.infrastructure" = "Infrastructure"
""")
    # pkg/interface/cli_like.py — Interface, imports from Infrastructure
    iface_dir = tmp_path / "pkg" / "interface"
    iface_dir.mkdir(parents=True)
    (tmp_path / "pkg").mkdir(exist_ok=True)
    (tmp_path / "pkg" / "__init__.py").write_text("")
    (iface_dir / "__init__.py").write_text("")
    infra_dir = tmp_path / "pkg" / "infrastructure" / "adapters"
    infra_dir.mkdir(parents=True)
    (tmp_path / "pkg" / "infrastructure" / "__init__.py").write_text("")
    (infra_dir / "__init__.py").write_text("")
    return tmp_path


def test_interface_imports_infrastructure_flagged(project_interface_infra):
    """Interface importing Infrastructure must be flagged (W9001).
    Mirrors cli.py importing adapters/gateways/services."""
    cli_like = project_interface_infra / "pkg" / "interface" / "cli_like.py"
    cli_like.write_text('''
"""CLI-style module: only functions, imports from Infrastructure."""

from pkg.infrastructure.adapters import something

def main():
    pass

def run_check():
    pass
''')
    (project_interface_infra / "pkg" / "infrastructure" / "adapters" / "__init__.py").write_text(
        "something = None"
    )

    out = _run_pylint(cli_like, project_interface_infra)

    assert "clean-arch-dependency" in out or "W9001" in out, (
        "Interface importing Infrastructure must be flagged (W9001). "
        "Output:\n" + out
    )


def test_god_module_functions_only_not_flagged(project_interface_infra):
    """Module with only functions, no classes, must NOT trigger W9010 (god-file).
    Documents current gap: we never flag 'god module'."""
    # Use a layer that wouldn't trigger other rules; avoid Interface→Infra
    (project_interface_infra / "pyproject.toml").write_text("""
[tool.clean-arch]

[tool.clean-arch.layer_map]
"pkg.interface" = "Interface"
""")
    cli_like = project_interface_infra / "pkg" / "interface" / "cli_like.py"
    cli_like.write_text('''
"""Many functions, no classes — god module like cli."""

def main():
    pass

def _run_check():
    pass

def _run_fix():
    pass

def _gather():
    pass

def _print_tables():
    pass
''')

    out = _run_pylint(
        cli_like, project_interface_infra, enable="clean-arch-god-file,clean-arch-folder-structure"
    )

    assert "clean-arch-god-file" not in out
