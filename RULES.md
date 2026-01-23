# 🛡️ Excelsior v2: Architectural Autopilot Rules

This catalog details all the rules enforced by `pylint-clean-architecture` (Excelsior), along with examples of "Bad" code and the corresponding "Clean Fix".

## Boundary Rules (W90xx)

### W9001: Illegal Dependency
**Message:** Illegal Dependency: %s layer is imported by %s layer.
**Clean Fix:** Invert dependency using an Interface/Protocol in the Domain layer.

**Bad:**
```python
# use_cases/process_order.py
from infrastructure.db import Database # Inner layer importing Outer layer
```

**Clean:**
```python
# domain/protocols.py
class OrderRepository(Protocol): ...

# use_cases/process_order.py
from domain.protocols import OrderRepository # Intra/Inner layer import
```

### W9003: Protected Member Access
**Message:** Access to protected member "%s" from outer layer.
**Clean Fix:** Expose public Interface or Use Case.

**Bad:**
```python
# use_case.py calling infrastructure
client._connect()
```

**Clean:**
```python
# infrastructure/client.py
def connect(self):
    self._connect()

# use_case.py
client.connect()
```

### W9004: Forbidden I/O in Domain/UseCase
**Message:** Forbidden I/O access (%s) in %s layer.
**Clean Fix:** Move logic to Infrastructure and inject via a Domain Protocol.

**Bad:**
```python
# domain/user.py
import requests

def update_user(self):
    requests.post(...)
```

**Clean:**
```python
# domain/protocols.py
class UserNotifier(Protocol):
    def notify(self): ...

# domain/user.py
def update_user(self, notifier: UserNotifier):
    notifier.notify()
```

### W9005: Delegation Anti-Pattern
**Message:** Delegation Anti-Pattern: %s.
**Clean Fix:** Implement logic in the delegate or use a Map/Dictionary lookup.

**Bad:**
```python
if action == "SAVE":
    return repo.save(user)
elif action == "DELETE":
    return repo.delete(user)
```

**Clean:**
```python
# Use a Strategy or Command pattern
handler = self.handlers.get(action)
return handler.execute(user)
```

### W9006: Law of Demeter
**Message:** Law of Demeter: Chain access (%s) exceeds one level.
**Clean Fix:** Add a method to the immediate object that performs the operation.

**Bad:**
```python
user.address.coordinates.lat # Three levels of nesting
```

**Clean:**
```python
user.get_latitude()
```

### W9007: Naked Return
**Message:** Naked Return: %s returned from Repository.
**Clean Fix:** Map the raw object to a Domain Entity before returning.

### W9009: Missing Abstraction
**Message:** Missing Abstraction: %s holds reference to %s.
**Clean Fix:** Replace the raw object with a Domain Entity or Value Object.

### W9010: God File Violation
**Message:** God File detected: %s.
**Clean Fix:** Split into separate files. A file should not contain multiple 'Heavy' components or mixed layers.

### W9011: Deep Structure Violation
**Message:** Deep Structure violation: Module '%s' in project root.
**Clean Fix:** Move to a sub-package (e.g., `core/`, `gateways/`).

### W9012: Defensive None Check
**Message:** Defensive None Check: '%s' checked for None in %s layer.
**Clean Fix:** Ensure the value is validated before entering core logic. Validation belongs in the Interface layer.

### W9013: Illegal I/O Operation (The Silent Core Rule)
**Message:** Illegal I/O Operation: '%s' called in silent layer '%s'.
**Clean Fix:** Delegate I/O to an Interface/Port (e.g., `TelemetryPort`).

**Bad:**
```python
# domain/user.py
def deactivate(self):
    print(f"Deactivating user {self.id}") # Illegal I/O in Domain
    self.is_active = False
```

**Clean:**
```python
# domain/protocols.py
class TelemetryPort(Protocol):
    def log_event(self, msg: str): ...

# domain/user.py
def deactivate(self, telemetry: TelemetryPort):
    telemetry.log_event(f"Deactivating user {self.id}")
    self.is_active = False
```

### W9015: Missing Type Hint
**Message:** Missing Type Hint: %s in %s signature.
**Clean Fix:** Add explicit type hints to all parameters and the return value.

## Testing Rules (W91xx)

### W9101: Fragile Test Mocks
**Message:** Fragile Test: %d mocks exceed limit of 4.
**Clean Fix:** Use a single Fake or Stub implementation of a Protocol rather than mocking many individual methods.

### W9102: Private Method Test
**Message:** Testing private method: %s.
**Clean Fix:** Test the public API method that calls this private method.

## Contract Rules (W92xx)

### W9201: Contract Integrity
**Message:** Infrastructure class %s must inherit from a Domain Protocol.
**Clean Fix:** Define a Protocol in Domain and inherit from it.

### W9202: Concrete Method Stub
**Message:** Concrete Method Stub: Method %s is a stub.
**Clean Fix:** Implement the method or remove it if not needed.

## DI Rules (W93xx)

### W9301: DI Violation
**Message:** DI Violation: %s instantiated directly in UseCase.
**Clean Fix:** Pass the dependency as an argument to __init__.

## Immutability Rules (W96xx)

### W9601: Domain Immutability
**Message:** Domain Immutability Violation: Attribute assignment in Domain layer.
**Clean Fix:** Use dataclasses with `frozen=True` or `namedtuples`.

## Anti-Bypass Guard (W95xx)

### W9501: Anti-Bypass Violation
**Message:** Anti-Bypass Violation: %s detected.
**Clean Fix:** Justify with '# JUSTIFICATION: <reason>' or resolve the architectural issue.
