"""
Pylint plugin entry point.
"""

from pylint.lint import PyLinter

from clean_architecture_linter.domain.constants import EXCELSIOR_BANNER
from clean_architecture_linter.domain.protocols import AstroidProtocol, PythonProtocol
from clean_architecture_linter.infrastructure.di.container import ExcelsiorContainer
from clean_architecture_linter.interface.reporter import CleanArchitectureSummaryReporter
from clean_architecture_linter.use_cases.checks.boundaries import (
    ResourceChecker,
    VisibilityChecker,
)
from clean_architecture_linter.use_cases.checks.bypass import BypassChecker
from clean_architecture_linter.use_cases.checks.contracts import ContractChecker
from clean_architecture_linter.use_cases.checks.dependencies import DependencyChecker
from clean_architecture_linter.use_cases.checks.design import DesignChecker
from clean_architecture_linter.use_cases.checks.di import DIChecker
from clean_architecture_linter.use_cases.checks.immutability import ImmutabilityChecker
from clean_architecture_linter.use_cases.checks.patterns import CouplingChecker, PatternChecker
from clean_architecture_linter.use_cases.checks.structure import ModuleStructureChecker
from clean_architecture_linter.use_cases.checks.testing import TestingChecker


def register(linter: PyLinter) -> None:
    """Register checkers."""
    print(EXCELSIOR_BANNER)

    # Get gateways once for injection
    container = ExcelsiorContainer.get_instance()
    python_gateway: PythonProtocol = container.get("PythonGateway")
    ast_gateway: AstroidProtocol = container.get("AstroidGateway")

    linter.register_checker(VisibilityChecker(linter))
    linter.register_checker(ResourceChecker(linter, python_gateway=python_gateway))
    linter.register_checker(ContractChecker(linter, python_gateway=python_gateway))
    linter.register_checker(DependencyChecker(linter, python_gateway=python_gateway))
    linter.register_checker(DesignChecker(linter, ast_gateway=ast_gateway))
    linter.register_checker(CouplingChecker(linter, ast_gateway=ast_gateway, python_gateway=python_gateway))
    linter.register_checker(PatternChecker(linter))
    linter.register_checker(TestingChecker(linter))
    linter.register_checker(ImmutabilityChecker(linter, python_gateway=python_gateway))
    linter.register_checker(BypassChecker(linter))
    linter.register_checker(DIChecker(linter, ast_gateway=ast_gateway, python_gateway=python_gateway))
    linter.register_checker(ModuleStructureChecker(linter))

    # Register reporter
    linter.register_reporter(CleanArchitectureSummaryReporter)
