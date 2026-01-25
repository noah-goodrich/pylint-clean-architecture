from clean_architecture_linter.checks.patterns import CouplingChecker
from clean_architecture_linter.infrastructure.gateways.astroid_gateway import AstroidGateway
from clean_architecture_linter.infrastructure.gateways.python_gateway import PythonGateway
from tests.linter_test_utils import run_checker

ast_gateway = AstroidGateway()
python_gateway = PythonGateway()

def test_str_startswith_on_hinted_stranger_passes():
    code = """
def get_it() -> str:
    return "hello"

def check():
    val: str = get_it()
    if val.startswith("h"):
        return True
    return False
"""
    messages = run_checker(CouplingChecker, code, ast_gateway=ast_gateway, python_gateway=python_gateway)
    assert "law-of-demeter" not in messages


def test_str_split_on_hinted_stranger_passes():
    code = """
def get_it() -> str:
    return "a,b,c"

def check():
    val: str = get_it()
    parts = val.split(",")
    return parts[0]
"""
    messages = run_checker(CouplingChecker, code, ast_gateway=ast_gateway, python_gateway=python_gateway)
    assert "law-of-demeter" not in messages


def test_str_split_chain_on_hinted_stranger_passes():
    code = """
def get_path() -> str:
    return "/path/to/file"

def check():
    p: str = get_path()
    if "tests" in p.split("/"):
        return True
    return False
"""
    messages = run_checker(CouplingChecker, code, ast_gateway=ast_gateway, python_gateway=python_gateway)
    assert "law-of-demeter" not in messages


def test_path_read_text_splitlines_passes():
    """Verify Path('file').read_text().splitlines() is allowed (StdLib exemption)."""
    code = """
from pathlib import Path
def process():
    lines = Path('file.txt').read_text().splitlines()
    return lines
"""
    messages = run_checker(CouplingChecker, code, ast_gateway=ast_gateway, python_gateway=python_gateway)
    assert "law-of-demeter" not in messages
