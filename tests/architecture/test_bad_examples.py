# Architecture Validation Suite
# This suite contains "Bad Examples" designed to trigger every linter rule.
# These serve as both regression tests and documentation of what NOT to do.

import os
import subprocess
import sys
from pathlib import Path

import pytest

# Plugin Discovery
PLUGIN_DIR = Path("/development/pylint-clean-architecture/src").resolve()


def run_pylint(file_path):
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{PLUGIN_DIR}:{env.get('PYTHONPATH', '')}"

    cmd = [
        "pylint",
        str(file_path),
        "--load-plugins=clean_architecture_linter",
        "--disable=all",
        "--enable=W9003,W9004,W9005,W9006,W9007,W9009",
        "--score=n",
        "--persistent=n",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    return result


def test_bad_io_access(tmp_path):
    """
    Test W9004: A Use Case calling open() or requests.*
    """
    d = tmp_path / "snowfort" / "orchestrators"  # Use Case Layer (by dir)
    d.mkdir(parents=True)
    f = d / "bad_io_usecase.py"

    f.write_text(
        """
import os
import requests

class ProcessDataUseCase:
    def execute(self):
        # Violation: Raw I/O in Use Case
        f = open('data.txt', 'r')
        requests.get('api')
"""
    )

    res = run_pylint(f)
    print(res.stdout)
    assert "W9004" in res.stdout
    assert "clean-arch-resources" in res.stdout
    assert "import os" in res.stdout


def test_bad_coupling(tmp_path):
    """
    Test W9006: A Command accessing repo.client.session
    """
    d = tmp_path / "snowfort" / "commands"
    d.mkdir(parents=True)
    f = d / "bad_coupling_command.py"

    f.write_text(
        """
class DeployCommand:
    def __init__(self, repo):
        self.repo = repo

    def run(self):
        # Violation: Law of Demeter (>1 dot)
        # Checking repo -> client -> execute()
        self.repo.client.execute()
"""
    )

    res = run_pylint(f)
    print(res.stdout)
    assert "W9006" in res.stdout
    assert "clean-arch-demeter" in res.stdout


def test_bad_return(tmp_path):
    """
    Test W9007: A Repository returning a raw requests.Response
    """
    d = tmp_path / "snowfort" / "io"  # Infrastructure Layer (by dir)
    d.mkdir(parents=True)
    f = d / "bad_return_repository.py"

    f.write_text(
        """
class UserRepository:
    def get_user(self):
        # Violation: Returning raw Response object
        # Should return Domain Entity
        return requests.Response()
"""
    )

    res = run_pylint(f)
    print(res.stdout)
    assert "W9007" in res.stdout
    assert "naked-return-violation" in res.stdout


def test_missing_abstraction(tmp_path):
    """
    Test W9009: UseCase holding reference to Client
    """
    d = tmp_path / "snowfort" / "orchestrators"
    d.mkdir(parents=True)
    f = d / "bad_abstraction_usecase.py"

    f.write_text(
        """
class SyncUseCase:
    def execute(self, repo):
        # Violation: Holding Client ref from repo
        snowflake_client = repo.get_snowflake_client()
        snowflake_client.query("SELECT 1")
"""
    )

    res = run_pylint(f)
    print(res.stdout)
    assert "W9009" in res.stdout
    assert "missing-abstraction-violation" in res.stdout


def test_delegation_advice(tmp_path):
    """
    Test W9005 advice validation
    """
    d = tmp_path / "snowfort" / "domain"
    d.mkdir(parents=True)
    f = d / "strategy_bad.py"

    f.write_text(
        """
def handle_request(req_type):
    # Violation: Delegation on type
    if req_type == 'A':
        return handler_a()
    elif req_type == 'B':
        return handler_b()
    else:
        return handler_c()
"""
    )

    res = run_pylint(f)
    print(res.stdout)
    assert "W9005" in res.stdout
    assert "Strategy Pattern" in res.stdout  # Validate advice text
