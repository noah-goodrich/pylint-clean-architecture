"""Design pattern glossary for docs and ELI5 mode. Pure domain data, no I/O."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PatternDefinition:
    """Structured explanation of a design pattern for docs and ELI5."""
    name: str
    eli5: str
    description: str
    when_to_use: str
    before_example: str
    after_example: str
    references: tuple[str, ...]


# Minimal glossary: Adapter, Facade, Strategy (used by DesignPatternDecisionTree)
PATTERN_GLOSSARY: dict[str, PatternDefinition] = {
    "adapter": PatternDefinition(
        name="Adapter",
        eli5="A class that translates one interface into another so your core code doesn't depend on the real implementation.",
        description="Adapter pattern: wrap an external or incompatible interface behind a domain Protocol so Domain/UseCase depend on the protocol, not the concrete class.",
        when_to_use="When Domain or UseCase would otherwise import or call infrastructure (I/O, framework) directly.",
        before_example="domain/use_case.py imports requests and calls requests.get(...)",
        after_example="Domain defines HttpPort protocol; infrastructure implements HttpAdapter; use_case receives HttpPort in __init__.",
        references=("https://refactoring.guru/design-patterns/adapter",),
    ),
    "facade": PatternDefinition(
        name="Facade",
        eli5="A single class that hides a bunch of steps behind one simple method.",
        description="Facade pattern: provide a unified interface to a set of interfaces in a subsystem. Callers use the facade instead of reaching through multiple objects.",
        when_to_use="When you have chained access (Law of Demeter) or a God class coordinating many dependencies.",
        before_example="obj.repo.session.query(Model).filter(...).first()",
        after_example="obj.repo.find_by_id(id)  # repo encapsulates the chain",
        references=("https://refactoring.guru/design-patterns/facade",),
    ),
    "strategy": PatternDefinition(
        name="Strategy",
        eli5="Swap behavior by passing in a different implementation instead of using if/elif.",
        description="Strategy pattern: define a family of algorithms (Protocol), encapsulate each one, and make them interchangeable.",
        when_to_use="When you have conditional logic that selects behavior (if type A do X, if type B do Y).",
        before_example="if config.backend == 'sql': ... elif config.backend == 'api': ...",
        after_example="backend: StoragePort injected; backend.save(data)",
        references=("https://refactoring.guru/design-patterns/strategy",),
    ),
}
