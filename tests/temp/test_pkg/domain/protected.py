
class A:
    def _hidden(self): pass

def func():
    a = A()
    a._hidden() # W9003
