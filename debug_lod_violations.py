import astroid
import os
import sys

# Add src to sys.path
sys.path.insert(0, os.path.abspath("src"))

from clean_architecture_linter.checks.patterns import CouplingChecker
from pylint.testutils import UnittestLinter

def walk(node, checker):
    name = f"visit_{node.__class__.__name__.lower()}"
    if hasattr(checker, name):
        getattr(checker, name)(node)

    for child in node.get_children():
        walk(child, checker)

def debug_violation():
    path: str = "tests/functional/source-data/lod-violations.py"
    with open(path, "r") as f:
        content = f.read()

    node = astroid.parse(content, module_name: str = "lod_violations")
    linter = UnittestLinter()
    checker = CouplingChecker(linter)

    print(f"Checking {path}...")
    walk(node, checker)

    messages = [m for m in linter.release_messages() if m.msg_id == "law-of-demeter"]
    print(f"Found {len(messages)} violations:")
    for m in messages:
        print(f"  Line {m.line}: {m.args}")

if __name__ == "__main__":
    debug_violation()
