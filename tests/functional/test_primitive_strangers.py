from excelsior_architect.domain.config import ConfigurationLoader
from excelsior_architect.infrastructure.gateways.astroid_gateway import AstroidGateway
from excelsior_architect.infrastructure.gateways.python_gateway import PythonGateway
from excelsior_architect.infrastructure.services.stub_authority import StubAuthority
from excelsior_architect.use_cases.checks.patterns import CouplingChecker
from tests.linter_test_utils import run_checker

ast_gateway = AstroidGateway()
python_gateway = PythonGateway()
stub_resolver = StubAuthority()
config_loader = ConfigurationLoader({}, {})


def test_str_startswith_on_hinted_stranger_passes() -> None:
    code: str = """
def get_it() -> str:
    return "hello"

def check():
    val: str = get_it()
    if val.startswith("h"):
        return True
    return False
"""
    messages = run_checker(
        CouplingChecker,
        code,
        ast_gateway=ast_gateway,
        python_gateway=python_gateway,
        stub_resolver=stub_resolver,
        config_loader=config_loader,
        registry={},
    )
    assert "law-of-demeter" not in messages


def test_str_split_on_hinted_stranger_passes() -> None:
    code: str = """
def get_it() -> str:
    return "a,b,c"

def check():
    val: str = get_it()
    parts = val.split(",")
    return parts[0]
"""
    messages = run_checker(
        CouplingChecker,
        code,
        ast_gateway=ast_gateway,
        python_gateway=python_gateway,
        stub_resolver=stub_resolver,
        config_loader=config_loader,
        registry={},
    )
    assert "law-of-demeter" not in messages


def test_str_split_chain_on_hinted_stranger_passes() -> None:
    code: str = """
def get_path() -> str:
    return "/path/to/file"

def check():
    p: str = get_path()
    if "tests" in p.split("/"):
        return True
    return False
"""
    messages = run_checker(
        CouplingChecker,
        code,
        ast_gateway=ast_gateway,
        python_gateway=python_gateway,
        stub_resolver=stub_resolver,
        config_loader=config_loader,
        registry={},
    )
    assert "law-of-demeter" not in messages


def test_path_read_text_splitlines_passes() -> None:
    """Verify Path('file').read_text().splitlines() is allowed (StdLib exemption)."""
    code: str = """
from pathlib import Path
def process():
    lines = Path('file.txt').read_text().splitlines()
    return lines
"""
    messages = run_checker(
        CouplingChecker,
        code,
        ast_gateway=ast_gateway,
        python_gateway=python_gateway,
        stub_resolver=stub_resolver,
        config_loader=config_loader,
        registry={},
    )
    assert "law-of-demeter" not in messages
