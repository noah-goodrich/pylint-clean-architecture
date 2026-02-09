from excelsior_architect.use_cases.initialize_graph import InitializeGraphUseCase
from excelsior_architect.infrastructure.gateways.kuzu_gateway import KuzuGraphGateway


def bootstrap_sae():
    """
    Initializes the Strategic Architecture Engine Brain for local execution.
    Hydrates the graph with master registries for Excelsior, MyPy, and Ruff.
    """
    gateway = KuzuGraphGateway()
    init_use_case = InitializeGraphUseCase(gateway)

    # Base resource path
    data_dir = "src/excelsior_architect/resources/data"

    # The Design Patterns Tree is the strategic core
    patterns_csv = f"{data_dir}/DESIGN_PATTERNS_TREE.csv"

    # We load all three violation registries to ensure the graph
    # can map signals from every tool to the strategic patterns.
    violation_registries = [
        f"{data_dir}/EXCELSIOR_VIOLATIONS.csv",
        f"{data_dir}/MYPY_VIOLATIONS.csv",
        f"{data_dir}/RUFF_VIOLATIONS.csv"
    ]

    for registry in violation_registries:
        init_use_case.execute(
            violations_csv=registry,
            patterns_csv=patterns_csv
        )

    print("SAE Knowledge Graph Hydrated Successfully with all registries.")
