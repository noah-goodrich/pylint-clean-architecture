import unittest
from unittest.mock import MagicMock, patch

import astroid
from astroid import nodes

from clean_architecture_linter.checks.contracts import ContractChecker
from clean_architecture_linter.config import ConfigurationLoader
from tests.linter_test_utils import MockLinter, run_checker


class TestContractChecker(unittest.TestCase):
    def setUp(self):
        from clean_architecture_linter.di.container import ExcelsiorContainer
        ExcelsiorContainer.reset()
        ConfigurationLoader._instance = None
        self.loader = ConfigurationLoader()
        self.linter = MockLinter()

        self.mock_python_gateway = MagicMock()
        # Default behavior: Not an exception, not infrastructure by default
        self.mock_python_gateway.is_exception_node.return_value = False
        self.mock_python_gateway.get_node_layer.return_value = None
        self.mock_python_gateway.is_protocol_node.return_value = False

        self.checker = ContractChecker(self.linter, python_gateway=self.mock_python_gateway)

    def test_domain_protocol_check(self):
        """Test detection of Domain Protocols."""
        code = """
from typing import Protocol

class UserProtocol(Protocol):
    def save(self): ...

class OtherProtocol:
    pass
        """
        self.mock_python_gateway.get_node_layer.return_value = "Domain"
        msgs = run_checker(ContractChecker, code, "src/domain/protocols.py", python_gateway=self.mock_python_gateway)
        self.assertEqual(msgs, [])

    def test_missing_protocol_violation(self):
        """Test W9201 when protocol inheritance is missing in Infrastructure."""
        code = """
class UserRepository:
    def save(self): ...
        """
        self.mock_python_gateway.get_node_layer.return_value = "Infrastructure"
        msgs = run_checker(ContractChecker, code, "src/infrastructure/repositories.py", python_gateway=self.mock_python_gateway)
        self.assertIn("contract-integrity-violation", msgs)


    def test_exemptions_exceptions(self):
        """Test W9201 exemptions for Exceptions."""
        code = """
class MyError(Exception):
    pass
        """
        self.mock_python_gateway.get_node_layer.return_value = "Infrastructure"
        self.mock_python_gateway.is_exception_node.return_value = True
        msgs = run_checker(ContractChecker, code, "src/infrastructure/errors.py", python_gateway=self.mock_python_gateway)
        self.assertEqual(msgs, [])

    def test_concrete_method_stub_w9202(self):
        """Test W9202: Concrete method stub."""
        code = """
class A:
    def work(self):
        pass
    def work_ellipsis(self):
        ...
    def work_none(self):
        return None
        """
        msgs = run_checker(ContractChecker, code, python_gateway=self.mock_python_gateway)
        self.assertEqual(len(msgs), 3, f"Expected 3 stubs, found {len(msgs)}: {msgs}")

    def test_stub_exemptions(self):
        """Test exemptions for W9202 (abstract, private, protocol)."""
        code = """
from abc import abstractmethod
from typing import Protocol

class MyProto(Protocol):
    def proto_method(self): ...

class MyBase:
    @abstractmethod
    def abstract_one(self):
        pass

class Impl(MyBase):
    def _private(self):
        pass
        """
        # MyProto should be detected as protocol, and Impl as standard class
        # We need is_protocol_node to return true for MyProto node
        def is_protocol_side_effect(node):
            return node.name == "MyProto"
        self.mock_python_gateway.is_protocol_node.side_effect = is_protocol_side_effect
        msgs = run_checker(ContractChecker, code, python_gateway=self.mock_python_gateway)
        self.assertEqual(msgs, [])


    def test_is_stub_logic(self):
        """Direct unit test of _is_stub for complex cases."""
        pass_node = astroid.extract_node("def f(): pass")
        self.assertTrue(self.checker._is_stub(pass_node))

        sneaky = astroid.extract_node(
            """
        def f():
            if False:
                pass
            return None
        """
        )
        self.assertTrue(self.checker._is_stub(sneaky))

        real = astroid.extract_node("def f(): return 1")
        self.assertFalse(self.checker._is_stub(real))

        real_side_effect = astroid.extract_node(
            """
        def f():
            print("doing something")
            return None
        """
        )
        self.assertFalse(self.checker._is_stub(real_side_effect))


if __name__ == "__main__":
    unittest.main()
