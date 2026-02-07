# EXCELSIOR STUB: astroid.nodes
# Node types used by pylint checkers

from collections.abc import Iterator
from typing import Any

class NodeNG:
    """Base class for all AST nodes."""
    lineno: int
    col_offset: int
    parent: NodeNG | None

    def qname(self) -> str: ...
    def root(self) -> Module: ...
    def frame(self) -> FunctionDef | Module | ClassDef: ...
    def infer(self) -> Iterator[Any]: ...
    def statement(self) -> NodeNG: ...
    def scope(self) -> NodeNG: ...

    def nodes_of_class(
        self, klass: type | tuple[type, ...], skip_klass: type | tuple[type, ...] | None = None
    ) -> Iterator[NodeNG]: ...


class Module(NodeNG):
    name: str
    file: str
    body: list[NodeNG]

    def absolute_import_activated(self) -> bool: ...
    def lookup(self, name: str) -> tuple[str, list[NodeNG]]: ...


class ClassDef(NodeNG):
    name: str
    body: list[NodeNG]
    bases: list[NodeNG]
    decorators: Decorators | None
    locals: dict[str, list[NodeNG]]  # THE TRUTH: .locals is a dict

    def ancestors(self) -> Iterator[ClassDef]: ...
    def mro(self) -> list[ClassDef]: ...
    def mymethods(self) -> list[FunctionDef]: ...
    def igetattr(self, name: str) -> Iterator[Any]: ...


class FunctionDef(NodeNG):
    name: str
    body: list[NodeNG]
    args: Arguments
    returns: NodeNG | None
    decorators: Decorators | None

    def is_method(self) -> bool: ...
    def igetattr(self, name: str) -> Iterator[Any]: ...


class AsyncFunctionDef(FunctionDef):
    ...


class Arguments(NodeNG):
    args: list[AssignName]
    defaults: list[NodeNG]
    kwonlyargs: list[AssignName]
    kw_defaults: list[NodeNG | None]
    annotations: list[NodeNG | None]
    posonlyargs: list[AssignName]
    vararg: str | None
    kwarg: str | None

    def find_argname(
        self, argname: str) -> tuple[int | None, AssignName | None]: ...


class Decorators(NodeNG):
    nodes: list[NodeNG]


class Call(NodeNG):
    func: NodeNG
    args: list[NodeNG]
    keywords: list[Keyword]


class Keyword(NodeNG):
    arg: str | None
    value: NodeNG


class Assign(NodeNG):
    targets: list[NodeNG]
    value: NodeNG


class AugAssign(NodeNG):
    target: NodeNG
    value: NodeNG
    op: str


class AnnAssign(NodeNG):
    target: NodeNG
    annotation: NodeNG
    value: NodeNG | None
    simple: int


class AssignName(NodeNG):
    name: str

    def lookup(self, name: str) -> tuple[str, list[NodeNG]]: ...


class AssignAttr(NodeNG):
    attrname: str
    expr: NodeNG


class Attribute(NodeNG):
    attrname: str
    expr: NodeNG


class Name(NodeNG):
    name: str

    def lookup(self, name: str) -> tuple[str, list[NodeNG]]: ...


class Const(NodeNG):
    value: Any


class Subscript(NodeNG):
    value: NodeNG
    slice: NodeNG


class If(NodeNG):
    test: NodeNG
    body: list[NodeNG]
    orelse: list[NodeNG]


class Return(NodeNG):
    value: NodeNG | None


class Global(NodeNG):
    names: list[str]


class Import(NodeNG):
    names: list[tuple[str, str | None]]


class ImportFrom(NodeNG):
    modname: str | None
    names: list[tuple[str, str | None]]
    level: int


class For(NodeNG):
    target: NodeNG
    iter: NodeNG
    body: list[NodeNG]
    orelse: list[NodeNG]


class While(NodeNG):
    test: NodeNG
    body: list[NodeNG]
    orelse: list[NodeNG]


class Try(NodeNG):
    body: list[NodeNG]
    handlers: list[ExceptHandler]
    orelse: list[NodeNG]
    finalbody: list[NodeNG]


class ExceptHandler(NodeNG):
    type: NodeNG | None
    name: AssignName | None
    body: list[NodeNG]


class With(NodeNG):
    items: list[tuple[NodeNG, AssignName | None]]
    body: list[NodeNG]


class Expr(NodeNG):
    value: NodeNG


class Compare(NodeNG):
    left: NodeNG
    ops: list[tuple[str, NodeNG]]


class BoolOp(NodeNG):
    op: str
    values: list[NodeNG]


class UnaryOp(NodeNG):
    op: str
    operand: NodeNG


class BinOp(NodeNG):
    op: str
    left: NodeNG
    right: NodeNG


class Dict(NodeNG):
    items: list[tuple[NodeNG, NodeNG]]


class List(NodeNG):
    elts: list[NodeNG]


class Set(NodeNG):
    elts: list[NodeNG]


class Tuple(NodeNG):
    elts: list[NodeNG]


class Lambda(NodeNG):
    args: Arguments
    body: NodeNG


class IfExp(NodeNG):
    test: NodeNG
    body: NodeNG
    orelse: NodeNG


class Comprehension(NodeNG):
    target: NodeNG
    iter: NodeNG
    ifs: list[NodeNG]
    is_async: bool


class ListComp(NodeNG):
    elt: NodeNG
    generators: list[Comprehension]


class SetComp(NodeNG):
    elt: NodeNG
    generators: list[Comprehension]


class DictComp(NodeNG):
    key: NodeNG
    value: NodeNG
    generators: list[Comprehension]


class GeneratorExp(NodeNG):
    elt: NodeNG
    generators: list[Comprehension]


class Yield(NodeNG):
    value: NodeNG | None


class YieldFrom(NodeNG):
    value: NodeNG


class Await(NodeNG):
    value: NodeNG


class Starred(NodeNG):
    value: NodeNG


class FormattedValue(NodeNG):
    value: NodeNG
    conversion: int
    format_spec: NodeNG | None


class JoinedStr(NodeNG):
    values: list[NodeNG]


class Pass(NodeNG):
    ...


class Break(NodeNG):
    ...


class Continue(NodeNG):
    ...


class Raise(NodeNG):
    exc: NodeNG | None
    cause: NodeNG | None


class Assert(NodeNG):
    test: NodeNG
    fail: NodeNG | None


class Delete(NodeNG):
    targets: list[NodeNG]


class DelName(NodeNG):
    name: str


class DelAttr(NodeNG):
    attrname: str
    expr: NodeNG


class Slice(NodeNG):
    lower: NodeNG | None
    upper: NodeNG | None
    step: NodeNG | None


class Index(NodeNG):
    value: NodeNG


class ExtSlice(NodeNG):
    dims: list[NodeNG]


class Match(NodeNG):
    subject: NodeNG
    cases: list[MatchCase]


class MatchCase(NodeNG):
    pattern: NodeNG
    guard: NodeNG | None
    body: list[NodeNG]


class MatchValue(NodeNG):
    value: NodeNG


class MatchAs(NodeNG):
    pattern: NodeNG | None
    name: AssignName | None


class MatchOr(NodeNG):
    patterns: list[NodeNG]


class MatchSequence(NodeNG):
    patterns: list[NodeNG]


class MatchMapping(NodeNG):
    keys: list[NodeNG]
    patterns: list[NodeNG]
    rest: AssignName | None


class MatchClass(NodeNG):
    cls: NodeNG
    patterns: list[NodeNG]
    kwd_attrs: list[str]
    kwd_patterns: list[NodeNG]


class MatchStar(NodeNG):
    name: AssignName | None


class NamedExpr(NodeNG):
    target: AssignName
    value: NodeNG
