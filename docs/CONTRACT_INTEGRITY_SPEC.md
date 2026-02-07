# Contract Integrity Specification (W9201)

## Purpose

Define when Infrastructure classes MUST inherit from Domain Protocols vs when they are internal implementation details that don't require protocols.

## Core Principle

**Protocols exist for CONSUMERS, not PRODUCERS.**

- If Domain/UseCase layers depend on it → REQUIRES Protocol
- If only Infrastructure layer uses it → INTERNAL (no protocol required)

## Decision Rules (Priority Order)

### Rule 1: Explicit Configuration (Highest Priority)

Classes can be explicitly marked in `pyproject.toml`:

```toml
[tool.clean-arch.contract_integrity]
# Explicitly require protocol (overrides all other rules)
require_protocol = [
    "MyService",
    "MyAdapter"
]

# Explicitly mark as internal (overrides all other rules)
internal_implementation = [
    "MyHelper",
    "MyUtility"
]
```

**Rationale:** Project-specific overrides for genuine edge cases.

**Test:** Check configuration is honored regardless of other rules.

**⚠️ CRITICAL WARNING - AI Agent Guidance:**

These lists are **last resort overrides ONLY**. They must NOT be used to bypass architectural issues.

**AI Agents MUST:**
1. **Never add to these lists** without explicit user approval
2. **Always fix the architectural issue first** (add protocol, fix design)
3. **Only suggest adding to list** if:
   - Architectural fix is impossible (framework limitation)
   - User has explicitly approved the specific exception
   - Thorough explanation of why protocol can't be added is provided

**Examples of CORRECT vs INCORRECT use:**

❌ **INCORRECT**: Adding to list to avoid work
```toml
internal_implementation = ["MyService"]  # Just avoiding protocol creation
```

✅ **CORRECT**: Framework limitation
```toml
# LibCST dictates structure, swapping implementations not possible
internal_implementation = ["CustomCSTTransformer"]
```

✅ **CORRECT**: Genuinely internal
```toml
# Only used within single module, never crosses layers
internal_implementation = ["_InternalCache"]
```

**User must review and approve** any additions to these lists.

---

### Rule 2: Framework Extensions (Auto-Detect)

Classes that inherit from framework base classes are INTERNAL.

**Auto-detected patterns:**
- `cst.CSTTransformer` (LibCST)
- `pylint.checkers.BaseChecker` (Pylint)
- `ast.NodeVisitor` (Python AST)
- Any class with `@dataclass` decorator

**Rationale:** Framework dictates structure; not swappable.

**Test:** Verify classes inheriting from these are marked internal.

```python
# INTERNAL - Framework extension
class MyTransformer(cst.CSTTransformer):
    pass
```

---

### Rule 3: Data Structures (Auto-Detect)

Pure data structures don't need protocols.

**Auto-detected patterns:**
- Inherits from `TypedDict`
- Inherits from `NamedTuple`
- Has `@dataclass` decorator (framework extension)

**Rationale:** Data has no behavior to abstract.

**Test:** Verify these classes are marked internal.

**WARNING:** Do NOT rely on naming conventions (e.g., `*Row`, `*Entry`). They are too easily broken. Use explicit type inheritance or explicit configuration instead.

```python
# INTERNAL - Data structure (TypedDict)
class FileResultRow(TypedDict):
    file: str
    count: int

# INTERNAL - Dataclass
@dataclass
class UserData:
    name: str
    age: int
```

---

### Rule 4: Private/Internal Classes (Auto-Detect)

Classes marked private or internal are INTERNAL.

**Auto-detected patterns:**
- Class name starts with `_` (Python ubiquitous convention - widely enforced)
- Decorated with custom `@internal` decorator (explicit marker)

**Rationale:** `_` prefix is Python's universal convention for private members. `@internal` is explicit intent.

**Test:** Verify private classes are marked internal.

**WARNING:** Do NOT rely on naming suffixes like `*Helper`, `*Utils`, `*Utility`. They are conventions, not guarantees. Use `_` prefix or `@internal` decorator for clarity.

```python
# INTERNAL - Private class (ubiquitous Python convention)
class _TokenParser:
    pass

# INTERNAL - Explicit internal marker
@internal
class TemporaryHelper:
    pass
```

---

### Rule 5: DI Container Registry (Auto-Detect)

Classes returned by DI container methods REQUIRE protocols.

**Auto-detected:**
- Any class returned by `ExcelsiorContainer.get_*()` methods
- Any class in container's return type annotations

**Rationale:** Container manages cross-layer dependencies.

**Test:** Inspect container class, verify all returned types have protocols.

```python
# REQUIRES PROTOCOL - Returned by container
class ExcelsiorContainer:
    def get_audit_service(self) -> AuditTrailServiceProtocol:
        return AuditTrailService()  # Must implement protocol
```

---

### Rule 6: Cross-Layer Usage (Static Analysis)

Classes imported by Domain or UseCase layers REQUIRE protocols.

**Detection:**
1. Find all imports in `domain/` and `use_cases/` directories
2. Check if they import from `infrastructure/`
3. If yes, the imported class REQUIRES protocol

**Rationale:** Direct cross-layer dependency violation.

**Test:** Parse imports, verify infrastructure classes used by domain have protocols.

```python
# In domain/rules/my_rule.py
from infrastructure.services.my_service import MyService  # ❌ VIOLATION

# Should be:
from domain.protocols import MyServiceProtocol  # ✅ CORRECT
```

---

### Rule 7: Protocol Already Exists (Auto-Detect)

If a protocol already exists with matching name, class REQUIRES it.

**Detection:**
1. Class name is `FooService`
2. Check if `FooServiceProtocol` exists in `domain/protocols.py`
3. If yes, class MUST inherit from it

**Rationale:** Protocol was created for a reason.

**Test:** For each service, check if protocol exists and inheritance is correct.

```python
# Protocol exists in domain/protocols.py
class FooServiceProtocol(Protocol):
    def do_something(self) -> None: ...

# REQUIRES PROTOCOL - Matching protocol exists
class FooService:  # ❌ Should inherit FooServiceProtocol
    pass
```

---

### Rule 8: Default (Lowest Priority)

If none of the above rules apply:

**Infrastructure Services (in `infrastructure/services/`):**
- REQUIRE protocols by default
- Can be overridden by explicit configuration

**Infrastructure Adapters (in `infrastructure/adapters/`):**
- REQUIRE protocols by default
- Can be overridden by explicit configuration

**Infrastructure Gateways (in `infrastructure/gateways/`):**
- REQUIRE protocols by default
- Can be overridden by explicit configuration

**Other Infrastructure classes:**
- INTERNAL by default
- Can be overridden by explicit configuration

**Rationale:** Conservative default for key directories.

**Test:** Verify default behavior for different directory locations.

---

## Decision Algorithm

```python
def requires_protocol(cls: ClassDef) -> tuple[bool, str]:
    """
    Returns: (requires_protocol: bool, reason: str)
    """
    # Rule 1: Explicit configuration (HIGHEST PRIORITY - use sparingly!)
    if cls.name in config.require_protocol:
        return (True, "Explicitly marked as requiring protocol (Rule 1)")
    if cls.name in config.internal_implementation:
        return (False, "Explicitly marked as internal (Rule 1)")
    
    # Rule 2: Framework extensions (actual inheritance check)
    if inherits_from_framework(cls):
        return (False, "Framework extension (Rule 2 - auto-detected)")
    
    # Rule 3: Data structures (actual type inheritance check)
    if is_typed_dict_or_named_tuple(cls):
        return (False, "Data structure: TypedDict/NamedTuple (Rule 3 - auto-detected)")
    if has_dataclass_decorator(cls):
        return (False, "Data structure: @dataclass (Rule 3 - auto-detected)")
    
    # Rule 4: Private/internal classes (ubiquitous Python convention)
    if cls.name.startswith("_"):
        return (False, "Private class: _ prefix (Rule 4 - Python convention)")
    if has_internal_decorator(cls):
        return (False, "Internal class: @internal decorator (Rule 4 - explicit)")
    
    # Rule 5: DI container registry
    if returned_by_container(cls):
        return (True, "Returned by DI container (Rule 5 - auto-detected)")
    
    # Rule 6: Cross-layer usage
    if imported_by_domain_or_usecase(cls):
        return (True, "Imported by Domain/UseCase (Rule 6 - auto-detected)")
    
    # Rule 7: Protocol exists
    if matching_protocol_exists(cls):
        return (True, "Matching protocol exists (Rule 7 - auto-detected)")
    
    # Rule 8: Default by location
    if cls.file.startswith("infrastructure/services/"):
        return (True, "Default for services/ directory (Rule 8)")
    if cls.file.startswith("infrastructure/adapters/"):
        return (True, "Default for adapters/ directory (Rule 8)")
    if cls.file.startswith("infrastructure/gateways/"):
        return (True, "Default for gateways/ directory (Rule 8)")
    
    return (False, "Default for other infrastructure/ classes (Rule 8)")
```

---

## Configuration Schema

```toml
[tool.clean-arch.contract_integrity]

# Explicit overrides (highest priority)
require_protocol = [
    "SpecialService",
    "CustomAdapter"
]

internal_implementation = [
    "HelperClass",
    "UtilityClass"
]

# Framework patterns (can extend defaults)
framework_base_classes = [
    "cst.CSTTransformer",
    "pylint.checkers.BaseChecker",
    "ast.NodeVisitor",
    "custom.BaseFramework"  # Add project-specific
]

# Private class detection (minimal, ubiquitous Python conventions only)
allow_private_prefix = true  # Detect _ prefix (default: true)
allow_internal_decorator = true  # Detect @internal (default: true)

# Auto-detection toggles
enable_di_container_detection = true
enable_cross_layer_detection = true
enable_protocol_exists_detection = true

# Default behavior by directory
services_require_protocol = true   # infrastructure/services/
adapters_require_protocol = true   # infrastructure/adapters/
gateways_require_protocol = true   # infrastructure/gateways/
other_require_protocol = false     # Other infrastructure/
```

---

## Traceability

Each violation message includes the decision reason:

```
W9201: Contract Integrity Violation: Class 'MyService' in infrastructure 
layer must inherit from a Domain Protocol.
Reason: Default for services directory
To override: Add 'MyService' to [tool.clean-arch.contract_integrity.internal_implementation]
```

---

## Testing Strategy

### 1. Unit Tests for Each Rule

```python
def test_rule_1_explicit_require_protocol():
    """Verify explicit configuration is honored."""
    config = {"require_protocol": ["MyService"]}
    cls = create_class("MyService")
    assert requires_protocol(cls, config) == (True, "Explicitly marked...")

def test_rule_2_framework_extension():
    """Verify framework extensions are internal."""
    cls = create_class("MyTransformer", bases=["cst.CSTTransformer"])
    assert requires_protocol(cls, {}) == (False, "Framework extension...")

# ... test for each rule
```

### 2. Integration Tests

```python
def test_full_decision_tree():
    """Test complete decision algorithm with real examples."""
    # Test data structure in services/ (Rule 3 overrides Rule 8)
    # Test DI container return (Rule 5)
    # Test cross-layer import (Rule 6)
```

### 3. Regression Tests

```python
def test_known_good_examples():
    """Test against known correct examples from codebase."""
    assert requires_protocol("AuditTrailService") == True
    assert requires_protocol("FileResultRow") == False
    assert requires_protocol("AddImportTransformer") == False
```

---

## Documentation for Developers

### Quick Reference Card

**Need Protocol?** Check this flowchart:

1. ⚙️ Explicit config? → Follow config
2. 🔧 Framework extension (CST, Pylint)? → NO protocol
3. 📦 Data structure (TypedDict, Row)? → NO protocol
4. 🔒 Private/helper (_Name, *Helper)? → NO protocol
5. 💉 Returned by DI container? → YES protocol
6. ⬆️ Imported by Domain/UseCase? → YES protocol
7. 📋 Matching protocol exists? → YES protocol
8. 📁 In services/adapters/gateways/? → YES protocol
9. 📁 Other infrastructure? → NO protocol

### Override Examples

```toml
# My transformer needs injection (unusual)
require_protocol = ["MySpecialTransformer"]

# My service is just a helper (unusual)
internal_implementation = ["SimpleHelperService"]
```

---

## Benefits

1. **Clear Rules:** 8 priority-ordered rules, not subjective
2. **Traceable:** Each decision includes reason + override path
3. **Testable:** Each rule has unit tests
4. **Flexible:** Explicit config overrides for edge cases
5. **Discoverable:** Violation messages explain reasoning
6. **Maintainable:** Central spec document + tests
7. **Consistent:** Same logic for AI and humans

---

## Implementation Checklist

- [ ] Update `contract_integrity.py` rule with new logic
- [ ] Add configuration schema to `domain/config.py`
- [ ] Create detection utilities (framework check, data check, etc.)
- [ ] Add unit tests for each rule
- [ ] Add integration tests for full algorithm
- [ ] Update violation messages to include reason
- [ ] Document in ARCHITECTURE_PRINCIPLES.md
- [ ] Add examples to .cursorrules

---

## Version History

- v1.0 (2026-02-05): Initial specification
