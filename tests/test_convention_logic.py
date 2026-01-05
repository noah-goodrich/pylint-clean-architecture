import sys
import os
import pytest
import subprocess
from pathlib import Path

# Ensure plugin is discoverable
PLUGIN_DIR = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(PLUGIN_DIR))

def run_pylint_on_snippet(file_path, snippet, extra_args=None):
    """
    Helper to create a temporary file, write snippet, and run pylint.
    """
    file_path.write_text(snippet)

    cmd = [
        "pylint",
        str(file_path),
        "--load-plugins=clean_architecture_linter",
        "--disable=all",
        "--enable=W9003,W9004,W9005,W9006,W9007,W9009",
        "--score=n",
        "--persistent=n"
    ]

    if extra_args:
        cmd.extend(extra_args)

    env = os.environ.copy()
    env["PYTHONPATH"] = str(PLUGIN_DIR)

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=env
    )
    return result

def test_convention_w9004_usecase_resource_ban(tmp_path):
    # Test valid UseCase logic (Suffix-based)
    # Convention: *UseCase suffix -> UseCase layer -> Bans raw I/O

    d = tmp_path / "app" / "use_cases"
    d.mkdir(parents=True)
    f = d / "create_user_usecase.py"

    snippet = """
import os
import requests

class CreateUserUseCase:
    def execute(self):
        # Violation: os.environ access in UseCase
        print(os.environ.get('KEY'))

        # Violation: requests usage
        requests.get('http://google.com')
"""
    result = run_pylint_on_snippet(f, snippet)

    assert "clean-arch-resources" in result.stdout
    assert "Forbidden I/O access (os.environ.get)" in result.stdout or "Forbidden I/O access (requests.get)" in result.stdout

def test_convention_w9004_infrastructure_allowed(tmp_path):
    # Test valid Infrastructure logic (Suffix-based)
    # Convention: *Repository suffix -> Infrastructure layer -> Allows I/O

    d = tmp_path / "app" / "infrastructure"
    d.mkdir(parents=True)
    f = d / "user_repository.py"

    snippet = """
import os

class UserRepository:
    def save(self):
        # Should be allowed
        print(os.environ.get('KEY'))
"""
    result = run_pylint_on_snippet(f, snippet)

    assert "abstract-resource-access-violation" not in result.stdout

def test_convention_w9009_missing_abstraction(tmp_path):
    # Test W9009: UseCase holding Client reference

    d = tmp_path / "app" / "use_cases"
    d.mkdir(parents=True)
    f = d / "sync_data_usecase.py"

    snippet = """
class SyncDataUseCase:
    def __init__(self, repo):
        self.repo = repo

    def execute(self):
        # Violation: Assigning a 'Client' from a repo method
        # This implies we are getting a raw client instead of doing business logic via repo
        snowflake_client = self.repo.get_snowflake_client()
        snowflake_client.query("SELECT *")
"""
    result = run_pylint_on_snippet(f, snippet)

    assert "missing-abstraction-violation" in result.stdout
    assert "snowflake_client" in result.stdout

def test_convention_directory_resolution(tmp_path):
    # Test resolution by directory structure

    d = tmp_path / "src" / "domain"
    d.mkdir(parents=True)
    f = d / "logic.py"

    # Domain banning requests
    snippet = """
import requests

def do_logic():
    # Domain layer (by directory) -> Violation
    requests.post('api')
"""
    result = run_pylint_on_snippet(f, snippet)

    assert "clean-arch-resources" in result.stdout
