"""
Pylint plugin entry point - composition root for the checker plugin.
Lives in infrastructure as it creates the container and wires dependencies.
"""

from pylint.lint import PyLinter

from excelsior_architect.domain.constants import EXCELSIOR_BANNER
from excelsior_architect.infrastructure.di.container import ExcelsiorContainer
from excelsior_architect.interface.reporter import CleanArchitectureSummaryReporter
from excelsior_architect.use_cases.checks.boundaries import (
    IllegalIOCallChecker,
    ResourceChecker,
    UIConcernChecker,
    VisibilityChecker,
)
from excelsior_architect.use_cases.checks.bypass import BypassChecker
from excelsior_architect.use_cases.checks.contracts import ContractChecker
from excelsior_architect.use_cases.checks.dependencies import DependencyChecker
from excelsior_architect.use_cases.checks.design import DesignChecker
from excelsior_architect.use_cases.checks.design_quality import DesignQualityChecker
from excelsior_architect.use_cases.checks.di import DIChecker
from excelsior_architect.use_cases.checks.entropy import EntropyChecker
from excelsior_architect.use_cases.checks.immutability import ImmutabilityChecker
from excelsior_architect.use_cases.checks.patterns import CouplingChecker, PatternChecker
from excelsior_architect.use_cases.checks.pattern_suggestions import PatternSuggestionChecker
from excelsior_architect.use_cases.checks.structure import ModuleStructureChecker
from excelsior_architect.use_cases.checks.testing import CleanArchTestingChecker


def register(linter: PyLinter) -> None:
    """Register checkers."""
    print(EXCELSIOR_BANNER)

    container = ExcelsiorContainer.get_instance()
    config_loader = container.get_config_loader()
    python_gateway = container.get_python_gateway()
    ast_gateway = container.get_astroid_gateway()
    stub_resolver = container.get_stub_authority()
    registry = container.get_guidance_service().get_registry()

    linter.register_checker(VisibilityChecker(
        linter, config_loader=config_loader, registry=registry))
    linter.register_checker(ResourceChecker(
        linter, python_gateway=python_gateway, config_loader=config_loader, registry=registry))
    linter.register_checker(IllegalIOCallChecker(
        linter, python_gateway=python_gateway, config_loader=config_loader, registry=registry))
    linter.register_checker(UIConcernChecker(
        linter, python_gateway=python_gateway, config_loader=config_loader, registry=registry))
    linter.register_checker(ContractChecker(
        linter, python_gateway=python_gateway, config_loader=config_loader, registry=registry))
    linter.register_checker(DependencyChecker(
        linter, python_gateway=python_gateway, config_loader=config_loader, registry=registry))
    linter.register_checker(DesignChecker(
        linter, ast_gateway=ast_gateway, config_loader=config_loader, registry=registry))
    linter.register_checker(DesignQualityChecker(
        linter, config_loader=config_loader, registry=registry))
    linter.register_checker(
        PatternSuggestionChecker(linter, registry=registry))
    linter.register_checker(
        CouplingChecker(
            linter,
            ast_gateway=ast_gateway,
            python_gateway=python_gateway,
            stub_resolver=stub_resolver,
            config_loader=config_loader,
            registry=registry,
        )
    )
    linter.register_checker(PatternChecker(linter, registry=registry))
    linter.register_checker(CleanArchTestingChecker(linter, registry=registry))
    linter.register_checker(ImmutabilityChecker(
        linter, python_gateway=python_gateway, config_loader=config_loader, registry=registry))
    linter.register_checker(BypassChecker(linter, registry=registry))
    linter.register_checker(
        DIChecker(
            linter,
            ast_gateway=ast_gateway,
            python_gateway=python_gateway,
            config_loader=config_loader,
            registry=registry,
        )
    )
    linter.register_checker(ModuleStructureChecker(
        linter, config_loader=config_loader, registry=registry))
    linter.register_checker(EntropyChecker(linter, registry=registry))

    # Register reporter
    linter.register_reporter(CleanArchitectureSummaryReporter)
