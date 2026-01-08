import unittest
from unittest.mock import MagicMock, patch
from astroid import nodes
import astroid
from clean_architecture_linter.config import ConfigurationLoader
from clean_architecture_linter.checks.contracts import ContractChecker
from clean_architecture_linter.layer_registry import LayerRegistry
from tests.linter_test_utils import run_checker, MockLinter


class TestContractChecker(unittest.TestCase):

    def setUp(self):
        ConfigurationLoader._instance = None
        self.loader = ConfigurationLoader()
        self.linter = MockLinter()
        self.checker = ContractChecker(self.linter)

    def test_domain_protocol_check(self):
        """Test detection of Domain Protocols."""
        code = """
from typing import Protocol

class UserProtocol(Protocol):
    def save(self): ...

class OtherProtocol:
    pass
        """
        msgs = run_checker(ContractChecker, code, "src/domain/protocols.py")
        self.assertEqual(msgs, [])

    def test_missing_protocol_violation(self):
        """Test W9201 when protocol inheritance is missing in Infrastructure."""
        code = """
class UserRepository:
    def save(self): ...
        """
        msgs = run_checker(ContractChecker, code, "src/infrastructure/repositories.py")
        self.assertIn("contract-integrity-violation", msgs)

    def test_exemptions_base_classes(self):
        """Test W9201 exemptions for Base classes."""
        code = """
class BaseRepository:
    pass
class RepositoryBase:
    pass
        """
        msgs = run_checker(ContractChecker, code, "src/infrastructure/repositories.py")
        self.assertEqual(msgs, [])

    def test_exemptions_exceptions(self):
        """Test W9201 exemptions for Exceptions."""
        code = """
class MyError(Exception):
    pass
        """
        msgs = run_checker(ContractChecker, code, "src/infrastructure/errors.py")
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
        msgs = run_checker(ContractChecker, code)
        self.assertEqual(msgs.count("concrete-method-stub"), 3)

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
        msgs = run_checker(ContractChecker, code)
        self.assertEqual(msgs, [])

    @patch(
        "clean_architecture_linter.checks.contracts.ContractChecker._is_domain_protocol"
    )
    @patch("clean_architecture_linter.checks.contracts.get_node_layer")
    def test_extra_public_method_violation(self, mock_layer, mock_is_proto):
        """Test W9201: Public method not in Protocol."""

        mock_layer.return_value = "Infrastructure"

        node = MagicMock(spec=nodes.ClassDef)
        node.name = "UserRepository"

        # Configure methods correctly
        # When node.methods() is called, return our method mocks
        method_save = MagicMock(spec=nodes.FunctionDef)
        method_save.name = "save"

        method_extra = MagicMock(spec=nodes.FunctionDef)
        method_extra.name = "extra_method"

        node.methods.return_value = [method_save, method_extra]

        # Mock ancestor (Protocol)
        proto = MagicMock()
        proto.name = "UserProtocol"

        # Protocol has 'save' but NOT 'extra_method'
        proto_save = MagicMock(spec=nodes.FunctionDef)
        proto_save.name = "save"

        # proto.methods is called by _get_protocol_methods
        proto.methods.return_value = [proto_save]

        node.ancestors.return_value = [proto]

        # Mock _is_domain_protocol to return True for our proto
        mock_is_proto.side_effect = lambda x: x == proto

        self.checker.visit_classdef(node)

        # Verify
        self.assertEqual(len(self.linter.messages), 1)
        self.assertIn("contract-integrity-violation", self.linter.messages)
        # MockLinter discards args, so we can't check for 'extra_method' string

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
