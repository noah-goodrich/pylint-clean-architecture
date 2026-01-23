import astroid

code: str = """
class S:
    def get_s(self) -> str:
        return "s"

def test(s: S):
    v: str = s.get_s()
    return v
"""
node = astroid.parse(code)
func = node.body[1]
ret_v = func.body[1].value
print(f"Node v infer:")
try:
    for inf in ret_v.infer():
        print(f"  Inferred Type: {getattr(inf, 'qname', lambda: str(inf))()}")
except Exception as e:
    print(f"  Error: {e}")
