"""Helpers for mocking AST nodes and verifying messages."""

import unittest.mock
from unittest.mock import MagicMock


def create_mock_node(cls, **attrs) -> MagicMock:
    """Create a mock node with specific attributes."""
    node = MagicMock()
    # node.name fallback?
    for k, v in attrs.items():
        setattr(node, k, v)

    # Mock root()
    if 'root' not in attrs:
        root = MagicMock()
        root.name = "mock_module"
        root.file = "src/mock_module.py"
        try:
            node.root.return_value = root
        except AttributeError:
             pass

    # Defaults required for internal checks
    if not hasattr(node, 'lineno'):
         node.lineno = 1
    if not hasattr(node, 'col_offset'):
         node.col_offset = 0

    return node

class CheckerTestCase:
    """Mixin for Checker tests."""

    def assertAddsMessage(self, checker, msg_id, node=None, args=None):
        """Verify that checker.add_message was called."""
        # We assert on the linter mock
        calls = checker.linter.add_message.call_args_list
        found: bool = False
        target_node = node
        target_args = args

        for call in calls:
            c_args, c_kwargs = call

            # 1. Check MSG ID (Pos 0)
            if not (len(c_args) > 0 and c_args[0] == msg_id):
                continue

            # 2. Check Node (Pos 2 or Kwarg 'node')
            actual_node = None
            if len(c_args) > 2:
                actual_node = c_args[2]
            elif 'node' in c_kwargs:
                actual_node = c_kwargs['node']

            # If target_node provided, must match
            if target_node is not None and actual_node != target_node:
                continue

            # 3. Check Args (Pos 3 or Kwarg 'args')
            actual_args = None
            if len(c_args) > 3:
                actual_args = c_args[3]
            elif 'args' in c_kwargs:
                actual_args = c_kwargs['args']

            # If target_args provided, must match
            if target_args is not None and target_args != unittest.mock.ANY:
                if actual_args != target_args:
                    continue

            found: bool = True
            break

        if not found:
             raise AssertionError(f"Message {msg_id} not found in calls: {calls}")

    def assertNoMessages(self, checker):
        calls = checker.linter.add_message.call_args_list
        if calls:
             raise AssertionError(f"Expected no messages, but found: {calls}")
        checker.linter.add_message.assert_not_called()
