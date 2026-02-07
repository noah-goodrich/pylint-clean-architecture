# Contract Integrity Quick Reference

## When Does a Class Need a Protocol?

### ✅ YES - Requires Protocol

1. **Explicitly configured** in `pyproject.toml`:
   ```toml
   [tool.clean-arch.contract_integrity]
   require_protocol = ["MyClass"]
   ```

2. **Returned by DI Container**:
   ```python
   def get_my_service(self) -> MyServiceProtocol:  # Must have protocol
       return MyService()
   ```

3. **Imported by Domain/UseCase**:
   ```python
   # In domain/
   from infrastructure.services.my_service import MyService  # ❌ BAD
   from domain.protocols import MyServiceProtocol  # ✅ GOOD
   ```

4. **Protocol Exists**: If `MyServiceProtocol` exists, `MyService` must inherit it

5. **In Key Directories** (default):
   - `infrastructure/services/`
   - `infrastructure/adapters/`
   - `infrastructure/gateways/`

### ❌ NO - Internal Implementation

1. **Explicitly configured**:
   ```toml
   [tool.clean-arch.contract_integrity]
   internal_implementation = ["MyHelper"]
   ```

2. **Framework Extension**:
   - Inherits from `cst.CSTTransformer`
   - Inherits from `pylint.checkers.BaseChecker`
   - Has `@dataclass` decorator

3. **Data Structure**:
   - Inherits from `TypedDict` or `NamedTuple`
   - Has `@dataclass` decorator

4. **Private/Internal**:
   - Name starts with `_` (ubiquitous Python convention)
   - Has `@internal` decorator (explicit marker)

5. **Other Infrastructure** (default): Classes not in services/adapters/gateways/

## Configuration Example

```toml
[tool.clean-arch.contract_integrity]
# ⚠️ USER APPROVAL REQUIRED FOR ANY ADDITIONS ⚠️
# These are LAST RESORT overrides - fix architecture first!
require_protocol = []  # Rarely needed - user must approve each addition
internal_implementation = []  # Use sparingly - user must approve each addition

# Extend framework detection (optional)
framework_base_classes = ["myframework.Base"]  # Add project-specific frameworks

# Toggle auto-detection (optional, defaults shown)
enable_di_container_detection = true
enable_cross_layer_detection = true
enable_protocol_exists_detection = true

# Directory defaults (optional, defaults shown)
services_require_protocol = true
adapters_require_protocol = true
gateways_require_protocol = true
other_require_protocol = false
```

## Decision Flowchart

```
1. Explicitly configured? → Use config (USER MUST APPROVE)
   ↓ No
2. Framework extension (CST, Pylint)? → Internal
   ↓ No
3. Data structure (TypedDict, NamedTuple, @dataclass)? → Internal
   ↓ No
4. Private/internal (_ prefix, @internal)? → Internal
   ↓ No
5. Returned by DI container? → Requires Protocol
   ↓ No
6. Imported by Domain/UseCase? → Requires Protocol
   ↓ No
7. Matching protocol exists? → Requires Protocol
   ↓ No
8. In services/adapters/gateways/? → Requires Protocol
   Otherwise → Internal
```

## Violation Message Format

```
W9201: Contract Integrity Violation: Class 'MyService' in infrastructure 
layer must inherit from Domain Protocol.

Reason: Default for services/ directory (Rule 8)
Override: Add 'MyService' to [tool.clean-arch.contract_integrity.internal_implementation]
```

## Testing Your Configuration

```bash
# Check specific class
excelsior check --explain-contract MyService

# Show all internal classes
excelsior check --show-internal

# Validate configuration
excelsior validate-config
```

## Common Scenarios

### Scenario: CST Transformer Needs Injection
```toml
# Unusual: Transformer needs to be swappable
require_protocol = ["MySpecialTransformer"]
```

### Scenario: Service is Genuinely Internal  
```toml
# ⚠️ Only if: truly internal, never crosses layers, user approved
internal_implementation = ["_InternalLogCache"]
```

**Better solution**: Use `_` prefix in class name instead of configuration.

### Scenario: TypedDict Used Across Layers
```python
# ❌ Don't do this - use proper domain entities
class UserData(TypedDict):  # Shouldn't cross layers
    pass

# ✅ Do this instead
@dataclass
class User:  # Proper domain entity
    pass
```
