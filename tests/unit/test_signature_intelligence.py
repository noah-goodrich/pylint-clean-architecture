import astroid

from excelsior_architect.infrastructure.gateways.astroid_gateway import AstroidGateway

gateway = AstroidGateway()
get_return_type_qname = gateway.get_node_return_type_qname
get_return_type_qname_from_expr = gateway.get_return_type_qname_from_expr


def test_simple_protocol_inference() -> None:
    code: str = """
from typing import Protocol, Optional
class Config(Protocol):
    def get_env(self, key: str) -> Optional[str]: ...

def test(c: Config):
    account: str = c.get_env("ACCOUNT")
    res: str = account.strip()
    res.lower()
"""
    module = astroid.parse(code)
    func = module.body[2]  # test()

    # account = c.get_env("ACCOUNT")
    # This works because get_env has a hint in the Protocol
    call_node = func.body[0].value
    assert get_return_type_qname(call_node) == "builtins.str"

    # res = account.strip()
    # This returns None because strip() is a builtin without a hint in this context
    # and account's source is uninferable.
    strip_node = func.body[1].value
    assert get_return_type_qname(strip_node) == "builtins.str"

    # However, get_return_type_qname_from_expr(res) would work because of the hint.


def test_bool_op_or_inference() -> None:
    code: str = """
from typing import Protocol, Optional
class Config(Protocol):
    def get_env(self, key: str) -> Optional[str]: ...

def test(c: Config, account: Optional[str] = None):
    val: str = account or c.get_env("ACCOUNT")
    res: str = val.strip()
    res.lower()
"""
    module = astroid.parse(code)
    func = module.body[2]  # test()

    # account or c.get_env("ACCOUNT")
    bool_op = func.body[0].value
    assert get_return_type_qname_from_expr(bool_op) == "builtins.str"

    # res = val.strip()
    strip_node = func.body[1].value
    assert get_return_type_qname(strip_node) == "builtins.str"


def test_builtin_constructor_inference() -> None:
    code: str = "x = str(123)"
    module = astroid.parse(code)
    call_node = module.body[0].value
    assert get_return_type_qname(call_node) == "builtins.str"


def test_union_unpacking() -> None:
    code: str = """
from typing import Protocol, Union

class API(Protocol):
    def fetch(self) -> Union[int, None]: ...

def test(api: API):
    res = api.fetch()
"""
    module = astroid.parse(code)
    func = module.body[2]
    call_node = func.body[0].value
    assert get_return_type_qname(call_node) == "builtins.int"


def test_list_base_type() -> None:
    code: str = """
from typing import Protocol, List

class API(Protocol):
    def get_list(self) -> List[str]: ...

def test(api: API):
    res = api.get_list()
"""
    module = astroid.parse(code)
    func = module.body[2]
    call_node = func.body[0].value
    # Currently we return the base type if it's not Optional/Union
    assert get_return_type_qname(call_node) == "builtins.list"
