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

def primitive_chain_exemption(service: CustomService) -> None:
    _rev: str = service.get_version().upper().strip()
"""

gateway = AstroidGateway()
node = astroid.parse(code)
func = node.body[1]
strip_call = func.body[0].value
upper_call = strip_call.func.expr
get_v_call = upper_call.func.expr

print(f"Get Version Call: {get_v_call.as_string()}")
print(f"  Return Type QName: {gateway.get_node_return_type_qname(get_v_call)}")

print(f"\nUpper Call: {upper_call.as_string()}")
print(f"  Is Trusted Authority Call: {gateway.is_trusted_authority_call(upper_call)}")

print(f"\nStrip Call: {strip_call.as_string()}")
print(f"  Is Trusted Authority Call: {gateway.is_trusted_authority_call(strip_call)}")
