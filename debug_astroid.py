# Debugging the test failure logic
from clean_architecture_linter.infrastructure.gateways.astroid_gateway import AstroidGateway
from clean_architecture_linter.infrastructure.typeshed_integration import TypeshedService
import astroid
import sys
from unittest.mock import MagicMock

# Ensure src is in path
sys.path.insert(0, "src")

gateway = AstroidGateway()
# Mock typeshed
gateway.typeshed.is_stdlib_qname = MagicMock(return_value: bool = True)

code: str = """
import re
pattern = re.compile('p')
match = pattern.match('s')
"""
module = astroid.parse(code)
assign_match = module.body[2]
match_call = assign_match.value

print(f"Testing call: {match_call.as_string()}")

# Trace safety manually
result = gateway._trace_safety(match_call, set())
print(f"Result: {result}")

# Debug lookup for re
re_node = module.body[1].value.func.expr # re
print(f"Looking up 're' from {re_node}: {re_node.lookup('re')}")
