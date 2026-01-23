import astroid

code: str = """
class S:
    def get_s(self) -> str:
        return "s"

def test(s: S):
    v: str = s.get_s()
    res = v.upper()
"""
node = astroid.parse(code)
func = node.body[1]
v_call = func.body[0].value
print(f"V Call: {v_call.as_string()}")
try:
    for inf in v_call.infer():
        print(f"  Inferred Type: {getattr(inf, 'qname', lambda: str(inf))()}")
except Exception as e:
    print(f"  Error: {e}")

upper_call = func.body[1].value
print(f"\nUpper Call: {upper_call.as_string()}")
try:
    for inf in upper_call.infer():
        print(f"  Inferred Type: {getattr(inf, 'qname', lambda: str(inf))()}")
except Exception as e:
    print(f"  Error: {e}")
factory_v = func.body[0].target
print(f"\nV node type: {type(factory_v)}")
for def_node in factory_v.lookup(factory_v.name)[1]:
    if hasattr(def_node, "annotation"):
        print(f"  Found annotation: {def_node.annotation.as_string()}")
