# SAFE_ZONE
import os

def safe_calls():
    # Builtins/Primitives (Category 1)
    "abc".strip().lower()
    x = [1, 2]
    x.append(3)
    y = {"a": 1}
    y.items()

    # Stdlib (Category 1)
    os.path.join("a", "b").strip()

    class A:
        def b(self): return self
        def c(self): return self
        def test(self):
            # Self calls (depth 2 max)
            self.b().c()

# VIOLATION_ZONE
class Stranger:
    def do_it(self): pass

class Friend:
    def get_stranger(self): return Stranger()

def bad_calls(f: Friend):
    # Direct chain on non-safe root (f is trusted but not local)
    f.get_stranger().do_it()

    # Stranger variable
    s = f.get_stranger()
    s.do_it()
