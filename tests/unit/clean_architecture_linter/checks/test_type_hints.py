import unittest

from clean_architecture_linter.checks.design import DesignChecker
from tests.linter_test_utils import run_checker


class TestTypeHintChecker(unittest.TestCase):
    def test_missing_return_type(self):
        code = """
def my_func(x: int):
    return x
"""
        msgs = run_checker(DesignChecker, code)
        self.assertIn("missing-type-hint", msgs)

    def test_missing_parameter_type(self):
        code = """
def my_func(x) -> int:
    return x
"""
        msgs = run_checker(DesignChecker, code)
        self.assertIn("missing-type-hint", msgs)

    def test_full_hints_pass(self):
        code = """
def my_func(x: int) -> int:
    return x
"""
        msgs = run_checker(DesignChecker, code)
        self.assertEqual(msgs, [])

    def test_method_self_cls_exempt(self):
        code = """
class MyClass:
    def method(self, x: int) -> int:
        return x

    @classmethod
    def clsmethod(cls, y: str) -> str:
        return y
"""
        msgs = run_checker(DesignChecker, code)
        self.assertEqual(msgs, [])

    def test_varargs_kwargs(self):
        code = """
def func(*args, **kwargs) -> None:
    pass
"""
        msgs = run_checker(DesignChecker, code)
        self.assertIn("missing-type-hint", msgs)
        # Should have 2 messages for args and kwargs
        self.assertEqual(len([m for m in msgs if m == "missing-type-hint"]), 2)

    def test_varargs_kwargs_with_hints(self):
        code = """
def func(*args: str, **kwargs: int) -> None:
    pass
"""
        msgs = run_checker(DesignChecker, code)
        # Some versions of python/astroid might handle this differently,
        # but let's see what our checker does.
        self.assertEqual(msgs, [])

if __name__ == "__main__":
    unittest.main()
