import astroid
import os
import sys

# Add src to sys.path
sys.path.insert(0, os.path.abspath("src"))

from clean_architecture_linter.infrastructure.gateways.astroid_gateway import AstroidGateway

code: str = """
from typing import Protocol

class Repository(Protocol):
    def get_config(self) -> str: ...

def test(repo: Repository):
    res = repo.get_config()
"""

gateway = AstroidGateway()
node = astroid.parse(code)
func = node.body[2]
call = func.body[0].value # repo.get_config()

print(f"Call: {call.as_string()}")

# 1. Check is_protocol_call
print(f"Is Protocol Call: {gateway.is_protocol_call(call)}")

# 2. Check is_protocol on Repository class
repo_class = node.body[1]
print(f"Is Protocol (Repository): {gateway.is_protocol(repo_class)}")

# Debug ancestors
try:
    for inf in repo_class.infer():
        if isinstance(inf, astroid.nodes.ClassDef):
            print(f"Ancestors of {inf.name}:")
            for a in inf.ancestors():
                print(f"  {a.qname()}")
except Exception as e:
    print(f"Inference error: {e}")
