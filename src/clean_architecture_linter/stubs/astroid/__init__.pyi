# EXCELSIOR STUB: astroid
# Provides type hints for the untyped astroid package.
# Only covers types actually used in this codebase.


from astroid import nodes as nodes

# Re-export commonly used node types at module level
from astroid.nodes import (
    Arguments as Arguments,
)
from astroid.nodes import (
    Assign as Assign,
)
from astroid.nodes import (
    AssignAttr as AssignAttr,
)
from astroid.nodes import (
    AssignName as AssignName,
)
from astroid.nodes import (
    Attribute as Attribute,
)
from astroid.nodes import (
    Call as Call,
)
from astroid.nodes import (
    ClassDef as ClassDef,
)
from astroid.nodes import (
    Const as Const,
)
from astroid.nodes import (
    FunctionDef as FunctionDef,
)
from astroid.nodes import (
    Global as Global,
)
from astroid.nodes import (
    If as If,
)
from astroid.nodes import (
    Import as Import,
)
from astroid.nodes import (
    ImportFrom as ImportFrom,
)
from astroid.nodes import (
    Module as Module,
)
from astroid.nodes import (
    Name as Name,
)
from astroid.nodes import (
    NodeNG as NodeNG,
)
from astroid.nodes import (
    Return as Return,
)
from astroid.nodes import (
    Subscript as Subscript,
)

# Exceptions
class InferenceError(Exception): ...
class AstroidBuildingError(Exception): ...

# Sentinel for failed inference
class _Uninferable:
    def __bool__(self) -> bool: ...
    def __repr__(self) -> str: ...

Uninferable: _Uninferable

# Manager singleton
class AstroidManager:
    prefer_stubs: bool
    def clear_cache(self) -> None: ...
    def ast_from_module_name(self, module_name: str) -> Module: ...

MANAGER: AstroidManager
