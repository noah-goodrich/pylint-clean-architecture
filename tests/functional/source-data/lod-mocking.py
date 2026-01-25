from typing import Any
from unittest.mock import MagicMock


def testing_mock_exemption() -> None:
    mock: Any = MagicMock()
    # Allowed: unittest.mock/pytest chains are always exempt
    # We use Any here because MagicMock is dynamic
    _res: Any = mock.return_value.some_method().nested_call()
