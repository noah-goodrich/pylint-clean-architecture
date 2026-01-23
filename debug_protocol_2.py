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
print(f"Functions inferred for '{call.func.as_string()}':")
try:
    for inf in call.func.infer():
        print(f"  Type: {type(inf)}")
        print(f"  Name: {getattr(inf, 'name', 'None')}")
        print(f"  Parent: {type(getattr(inf, 'parent', None))}")
        parent = getattr(inf, 'parent', None)
        if parent:
             print(f"  Parent Name: {getattr(parent, 'name', 'None')}")
             if isinstance(parent, astroid.nodes.ClassDef):
                 print(f"  Is Parent Protocol: {gateway.is_protocol(parent)}")
except Exception as e:
    print(f"Error: {e}")
