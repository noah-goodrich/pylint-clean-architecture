# EXCELSIOR CORE STUB: Astroid Nodes
# Absolute Truth for attribute resolution. No nominal guessing.
# (Violation lives in stubs/core/clean_architecture_linter/domain/rules.pyi)

class NodeNG:
    def qname(self) -> str: ...
    @property
    def lineno(self) -> int: ...
    @property
    def col_offset(self) -> int: ...

class ClassDef(NodeNG):
    name: str
    locals: dict[str, list[NodeNG]]  # THE TRUTH: .locals is a dict

class FunctionDef(NodeNG):
    name: str
