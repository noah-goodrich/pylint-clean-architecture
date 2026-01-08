"""
Pylint plugin entry point.
"""

from pylint.lint import PyLinter

from clean_architecture_linter.checks.boundaries import (
    ResourceChecker,
    VisibilityChecker,
)
from clean_architecture_linter.checks.bypass import BypassChecker
from clean_architecture_linter.checks.contracts import ContractChecker
from clean_architecture_linter.checks.dependencies import DependencyChecker
from clean_architecture_linter.checks.design import DesignChecker
from clean_architecture_linter.checks.di import DIChecker
from clean_architecture_linter.checks.immutability import ImmutabilityChecker
from clean_architecture_linter.checks.patterns import CouplingChecker, PatternChecker
from clean_architecture_linter.checks.testing import TestingChecker
from clean_architecture_linter.reporter import CleanArchitectureSummaryReporter


def register(linter: PyLinter) -> None:
    """Register checkers."""
    linter.register_checker(VisibilityChecker(linter))
    linter.register_checker(ResourceChecker(linter))
    linter.register_checker(ContractChecker(linter))
    linter.register_checker(DependencyChecker(linter))
    linter.register_checker(DesignChecker(linter))
    linter.register_checker(CouplingChecker(linter))
    linter.register_checker(PatternChecker(linter))
    linter.register_checker(TestingChecker(linter))
    linter.register_checker(ImmutabilityChecker(linter))
    linter.register_checker(BypassChecker(linter))
    linter.register_checker(DIChecker(linter))

    # Optional extensions
    # pylint: disable=import-outside-toplevel
    from clean_architecture_linter.config import ConfigurationLoader
    from clean_architecture_linter.checks.snowflake import SnowflakeGovernanceChecker

    # pylint: enable=import-outside-toplevel

    config = ConfigurationLoader()
    if "snowflake" in config.enabled_extensions:
        linter.register_checker(SnowflakeGovernanceChecker(linter))

    # Register reporter
    linter.register_reporter(CleanArchitectureSummaryReporter)
