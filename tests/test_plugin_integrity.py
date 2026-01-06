import os
import subprocess
import sys

import pytest


def run_pylint(file_path):
    """Run pylint with the plugin against a file."""
    env = os.environ.copy()
    root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    src_path = os.path.join(root_path, "src")
    env["PYTHONPATH"] = (
        src_path + os.pathsep + root_path + os.pathsep + env.get("PYTHONPATH", "")
    )

    cmd = [
        sys.executable,
        "-m",
        "pylint",
        "--load-plugins=clean_architecture_linter",
        "--disable=all",
        "--enable=W9201,W9401,W9501",
        file_path,
    ]
    # We use -f parseable to make output easier to parse if needed, but simple string search is fine
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    return result.stdout + result.stderr


@pytest.mark.parametrize(
    "bait_file,expected_id",
    [
        ("domain/violation_immutability.py", "W9401"),
        ("infrastructure/violation_contract.py", "W9201"),
        ("violation_bypass_lazy.py", "W9501"),
        ("violation_bypass_banned.py", "W9501"),
        ("violation_bypass_unlisted.py", "W9501"),
    ],
)
def test_bait_violations(bait_file, expected_id):
    path = os.path.join(os.path.dirname(__file__), "bait", bait_file)
    output = run_pylint(path)
    assert (
        expected_id in output
    ), f"Expected {expected_id} in output for {bait_file}, but got:\n{output}"


def test_clean_file():
    path = os.path.join(os.path.dirname(__file__), "bait", "clean_file.py")
    output = run_pylint(path)
    # Ensure no arch warnings
    for arch_id in ["W9201", "W9401", "W9501"]:
        assert (
            arch_id not in output
        ), f"Expected NO {arch_id} in output for clean_file.py, but got:\n{output}"
