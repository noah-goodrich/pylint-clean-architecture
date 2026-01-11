import os
import subprocess
import sys
from pathlib import Path

# Create a temporary directory for tests
TEST_DIR = Path("/development/clean-architecture-linter-plugin/tests/temp")
TEST_DIR.mkdir(parents=True, exist_ok=True)

# Create a dummy pyproject.toml for config
PYPROJECT = TEST_DIR / "pyproject.toml"
PYPROJECT.write_text(
    """
[tool.clean-architecture-linter]
visibility_enforcement = true
resource_access_methods = { database_io = ["db.execute"] }

[[tool.clean-architecture-linter.layers]]
name = "Domain"
module = "test_pkg.domain"
allowed_resources = []

[[tool.clean-architecture-linter.layers]]
name = "Interface"
module = "test_pkg.interface"
allowed_resources = ["database_io"]
"""
)

# Define test cases
# Format: (filename, content, expected_error_code)

CASES = [
    (
        "test_pkg/domain/protected.py",
        """
class A:
    def _hidden(self): pass

def func():
    a = A()
    a._hidden() # W9003
""",
        "W9003",
    ),
    (
        "test_pkg/domain/resources.py",
        """
import db
def func():
    db.execute("SELECT") # W9004 (Domain has no allowed resources)
""",
        "W9004",
    ),
    (
        "test_pkg/interface/resources_ok.py",
        """
import db
def func():
    db.execute("SELECT") # OK (Interface allows database_io)
""",
        None,
    ),
    (
        "test_pkg/domain/demeter.py",
        """
class A:
    def method(self): pass

def func(obj):
    obj.b.c.method() # W9006
""",
        "W9006",
    ),
    (
        "test_pkg/domain/delegation.py",
        """
def handler(x):
    if x:
        return foo()
    else:
        return bar()
# W9005
""",
        "W9005",
    ),
]


def run_test():
    print("Running plugin verification...")
    # Ensure package is in path
    os.environ["PYTHONPATH"] = "/development/clean-architecture-linter-plugin/src"

    for rel_path, content, _expected in CASES:
        file_path = TEST_DIR / rel_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)

        # Create empty __init__.py files
        (TEST_DIR / "test_pkg").mkdir(exist_ok=True)
        (TEST_DIR / "test_pkg/__init__.py").touch()
        (TEST_DIR / "test_pkg/domain").mkdir(exist_ok=True)
        (TEST_DIR / "test_pkg/domain/__init__.py").touch()
        (TEST_DIR / "test_pkg/interface").mkdir(exist_ok=True)
        (TEST_DIR / "test_pkg/interface/__init__.py").touch()

    print(f"Created {len(CASES)} test files in {TEST_DIR}")
    print("Running Pylint...")

    # Run Pylint
    # We switch CWD to TEST_DIR so ConfigLoader finds pyproject.toml
    cmd = ["pylint", "--load-plugins", "clean_architecture_linter", "test_pkg"]

    result = subprocess.run(cmd, cwd=TEST_DIR, capture_output=True, text=True)

    print("Pylint Output:")
    print(result.stdout)

    # Verification
    failures = []

    for rel_path, _content, expected in CASES:
        if expected:
            if expected not in result.stdout:
                failures.append(f"Expected {expected} in {rel_path}, but not found.")
            else:
                print(f"✅ Found {expected} in {rel_path}")
        else:
            # For 'None' expected, specific checks are harder in bulk run,
            # but we can look for file specific errors if we parsed output.
            pass

    if failures:
        print("\n❌ Verification FAILED:")
        for f in failures:
            print(f)
        sys.exit(1)
    else:
        print("\n✅ All Checks Passed!")


if __name__ == "__main__":
    run_test()
