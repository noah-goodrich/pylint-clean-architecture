import astroid
import os
import sys

# Add src to sys.path
sys.path.insert(0, os.path.abspath("src"))

from clean_architecture_linter.infrastructure.gateways.astroid_gateway import AstroidGateway

code: str = """
class CustomService:
    def get_version(self) -> str:
        return "1.0"

def test(service: CustomService):
    res = service.get_version()
"""

gateway = AstroidGateway()
node = astroid.parse(code)
func = node.body[1]
call = func.body[0].value # service.get_version()

print(f"Call: {call.as_string()}")
print(f"Inference results for call:")
try:
    for inf in call.infer():
        print(f"  {getattr(inf, 'qname', lambda: str(inf))()}")
except Exception as e:
    print(f"Error: {e}")

print(f"\nGateway return type qname: {gateway.get_node_return_type_qname(call)}")
