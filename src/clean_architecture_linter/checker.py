from pylint.lint import PyLinter
from clean_architecture_linter.checks.visibility import VisibilityChecker
from clean_architecture_linter.checks.resources import ResourceChecker
from clean_architecture_linter.checks.patterns import DelegationChecker
from clean_architecture_linter.checks.coupling import DemeterChecker
from clean_architecture_linter.checks.design import DesignChecker

def register(linter: PyLinter) -> None:
    """Register checkers."""
    linter.register_checker(VisibilityChecker(linter))
    linter.register_checker(ResourceChecker(linter))
    linter.register_checker(DelegationChecker(linter))
    linter.register_checker(DemeterChecker(linter))
    linter.register_checker(DesignChecker(linter))
