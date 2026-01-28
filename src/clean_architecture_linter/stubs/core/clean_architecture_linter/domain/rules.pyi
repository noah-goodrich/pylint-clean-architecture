# EXCELSIOR CORE STUB: clean_architecture_linter.domain.rules
# Attribute resolution for Violation and related types. No nominal guessing.

class Violation:
    code: str
    message: str
    location: str
    fixable: bool
    fix_failure_reason: str | None
    is_comment_only: bool
