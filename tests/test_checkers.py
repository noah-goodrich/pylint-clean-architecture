from clean_architecture_linter.checks.boundaries import ResourceChecker, VisibilityChecker
from clean_architecture_linter.checks.contracts import ContractChecker
from clean_architecture_linter.checks.design import DesignChecker
from clean_architecture_linter.checks.patterns import PatternChecker, CouplingChecker
from clean_architecture_linter.checks.testing import TestingChecker
from clean_architecture_linter.config import ConfigurationLoader

from linter_test_utils import run_checker


class TestAllCheckers:
    def test_resource_checker(self):
        code = "import os\ndef execute(): os.remove('foo')"
        msgs = run_checker(ResourceChecker, code, "use_cases/test.py")
        assert "clean-arch-resources" in msgs

    def test_delegation_checker(self):
        code = """
        def check(a):
            if a == 'x':
                return do_x()
            elif a == 'y':
                return do_y()
            else:
                return do_z()
        """
        msgs = run_checker(PatternChecker, code)
        assert "clean-arch-delegation" in msgs

    def test_design_checker(self):
        code = "def get_data(): return Cursor()"
        msgs = run_checker(DesignChecker, code)
        assert "naked-return-violation" in msgs

    def test_test_coupling_checker(self):
        code = "def test_foo(): sut._private()"
        msgs = run_checker(TestingChecker, code)
        assert "private-method-test" in msgs

        code = """
        def test_heavy():
            patch('a'); patch('b'); patch('c'); patch('d'); patch('e')
        """
        msgs = run_checker(TestingChecker, code)
        assert "fragile-test-mocks" in msgs

    def test_visibility_checker(self):

        code = "class A: \n def call(self, other): return other._secret"
        msgs = run_checker(VisibilityChecker, code)
        assert "clean-arch-visibility" in msgs

    def test_config_layer_resolution(self):

        loader = ConfigurationLoader()

        # Test convention-based
        layer = loader.get_layer_for_module("any", "src/myapp/use_cases/apply.py")
        assert layer == "UseCase"

        # Test explicit override
        loader._config = {"layers": [{"name": "Custom", "module": "my_special"}]}  # pylint: disable=protected-access
        layer = loader.get_layer_for_module("my_special.logic")
        assert layer == "Custom"

    def test_contract_checker(self):

        # Protocols skipped
        code = "from typing import Protocol\nclass I(Protocol):\n def run(self): ..."
        msgs = run_checker(ContractChecker, code)
        assert len(msgs) == 0

        # Regular classes without protocols collected DO flag if they are stubs
        code = "class A: \n def public(self): pass"
        msgs = run_checker(ContractChecker, code)
        assert "concrete-method-stub" in msgs

    def test_contract_checker_stubs(self):

        # Simple stub
        code = "class A:\n def work(self): pass"
        msgs = run_checker(ContractChecker, code)
        assert "concrete-method-stub" in msgs

        # Sneaky return stub
        code = "class A:\n def work(self): return None"
        msgs = run_checker(ContractChecker, code)
        assert "concrete-method-stub" in msgs

        # Sneaky nested branch stub
        code = "class A:\n def work(self):\n  if False:\n   pass\n  return None"
        msgs = run_checker(ContractChecker, code)
        assert "concrete-method-stub" in msgs

        # Valid implementation
        code = "class A:\n def work(self):\n  print('real work')\n  return True"
        msgs = run_checker(ContractChecker, code)
        assert "concrete-method-stub" not in msgs
