"""Unit tests for InitializeGraphUseCase."""
from unittest.mock import MagicMock

from excelsior_architect.use_cases.initialize_graph import InitializeGraphUseCase


def test_execute_loads_patterns_and_calls_add_strategy():
    """execute reads patterns CSV via filesystem and calls gateway.add_strategy per row."""
    gateway = MagicMock()
    filesystem = MagicMock()
    patterns_csv = "design_patterns_tree.csv"
    patterns_content = "ID,Pattern,Rationale,Violations,Implementation\n"
    patterns_content += "R1,Repository,Centralize data,W9004,W9001\n"
    filesystem.read_text.side_effect = lambda p: patterns_content if p == patterns_csv else "Code,Name\nW9004,I/O in domain\n"

    use_case = InitializeGraphUseCase(gateway=gateway, filesystem=filesystem)
    use_case.execute(patterns_csv, ["violations.csv"])

    gateway.add_strategy.assert_called()
    call = gateway.add_strategy.call_args_list[0]
    assert call.kwargs["strat_id"] == "R1"
    assert call.kwargs["pattern"] == "Repository"
    assert call.kwargs["codes"] == ["W9004"]


def test_execute_ensures_violations_from_each_csv():
    """execute reads each violations CSV and calls ensure_violation per row."""
    gateway = MagicMock()
    filesystem = MagicMock()
    patterns_content = "ID,Pattern,Rationale,Violations,Implementation\n"
    violations_content = "Code,Name\nW9004,I/O in domain\nW9001,Layer violation\n"
    def read_text(path: str) -> str:
        return patterns_content if path == "design_patterns_tree.csv" else violations_content

    filesystem.read_text.side_effect = read_text

    use_case = InitializeGraphUseCase(gateway=gateway, filesystem=filesystem)
    use_case.execute("design_patterns_tree.csv", ["v1.csv", "v2.csv"])

    assert gateway.ensure_violation.call_count >= 2
    codes = [c[1]["code"] for c in gateway.ensure_violation.call_args_list]
    assert "W9004" in codes
    assert "W9001" in codes
