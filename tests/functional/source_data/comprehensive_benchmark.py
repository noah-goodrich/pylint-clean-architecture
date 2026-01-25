"""Comprehensive Benchmark for Clean Architecture Violations."""

from typing import Any

# W9001: Illegal Dependency (Assuming we are Domain/UseCase and importing Infrastructure like SQLAlchemy)
# But we can't easily import non-existent modules. We'll use a mocked infrastructure name if config allows simulation.
# Or better, we define classes that simulate it.

class InternalObj:
    _protected = "I am secret"  # W9003 target

class Stranger:
    def call_me(self):
        pass

class Manager:
    stranger = Stranger()

class DomainEntity:
    pass

class Repository:
    def get_data(self) -> Any:  # W9016: Banned Any
        # W9007: Naked Return (returning raw I/O or None without Entity)
        return None

class BadUseCase:
    """Uses forbidden things."""

    def __init__(self, repo: Any): # W9016
        self.repo = repo
        # W9009: Missing Abstraction (References detailed infra if we had proper types)
        self.session = "SQLAlchemy Session"

    def execute(self, params): # W9015: Missing Type Hint
        # W9012: Defensive None Check
        if params is None:
            raise ValueError("No params")

        # W9006: Law of Demeter (a.b.c())
        mgr = Manager()
        mgr.stranger.call_me()

        # W9003: Protected Member Access
        obj = InternalObj()
        print(obj._protected)

        # W9005: Delegation Anti-Pattern
        if params == "A":
            return self.do_a()
        elif params == "B":
            return self.do_b()

    def do_a(self): pass
    def do_b(self): pass

# W9010: Mixed Layers (God File) - Defining Infrastructure here too
class PostgresAdapter:
    def connect(self):
        # W9013: Illegal I/O (Silent Layer) - but this is Adapter so technically ok if layer detection works.
        # But if we treat this file as UseCase, it's bad.
        print("Connecting...")

# W9011: Deep Structure - This file is in tests/functional/source_data/, so it might trigger if treated as root.
