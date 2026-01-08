# Clean Architecture Linter Rules

This catalog details all the rules enforced by `pylint-clean-architecture`, along with examples of "Bad" code and the corresponding "Clean Fix".

## Boundary Rules (W90xx)

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

### W9010: Illegal Dependency
**Message:** Illegal Dependency: %s layer cannot import from %s layer.
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

## Testing Rules (W91xx)

### W9101: Fragile Test Mocks
**Message:** Fragile Test: %d mocks exceed limit of 4.
**Clean Fix:** Use a single Fake or Stub implementation of a Protocol rather than mocking many individual methods.

**Bad:**
```python
def test_complex_flow(mocker):
    m1 = mocker.patch("...")
    m2 = mocker.patch("...")
    m3 = mocker.patch("...")
    m4 = mocker.patch("...")
    m5 = mocker.patch("...")
    # ...
```

**Clean:**
```python
class FakeRepository:
    # ... implementation ...

def test_complex_flow():
    repo = FakeRepository()
    # ...
```

### W9102: Private Method Test
**Message:** Testing private method: %s.
**Clean Fix:** Test the public API method that calls this private method.

**Bad:**
```python
def test_internal_logic():
    service._calculate_tax()
```

**Clean:**
```python
def test_public_api():
    # Implicitly tests _calculate_tax
    service.process_order()
```

## Contract Rules (W92xx)

### W9201: Contract Integrity
**Message:** Infrastructure class %s must inherit from a Domain Protocol.
**Clean Fix:** Define a Protocol in Domain and inherit from it.

**Bad:**
```python
# infrastructure/repo.py
class UserRepository: # implicit implementation
    def save(self, user): ...
```

**Clean:**
```python
# domain/protocols.py
class UserRepository(Protocol):
    def save(self, user): ...

# infrastructure/repo.py
class SqlUserRepository(UserRepository):
    def save(self, user): ...
```

### W9202: Concrete Method Stub
**Message:** Concrete Method Stub: Method %s is a stub.
**Clean Fix:** Implement the method or remove it if not needed.

## DI Rules (W93xx)

### W9301: DI Violation
**Message:** DI Violation: %s instantiated directly in UseCase.
**Clean Fix:** Pass the dependency as an argument to __init__.

**Bad:**
```python
class UseCase:
    def __init__(self):
        self.repo = SqlRepository()
```

**Clean:**
```python
class UseCase:
    def __init__(self, repo: UserRepository):
        self.repo = repo
```

## Immutability Rules (W94xx)

### W9401: Domain Mutability
**Message:** Domain Mutability Violation: Class %s must be immutable.
**Clean Fix:** Add (frozen=True) to the @dataclass decorator.

**Bad:**
```python
@dataclass
class UserEntity:
    id: str
```

**Clean:**
```python
@dataclass(frozen=True)
class UserEntity:
    id: str
```

## Anti-Bypass Guard (W95xx)

### W9501: Anti-Bypass Violation
**Message:** Anti-Bypass Violation: %s detected.
**Clean Fix:** Justify with '# JUSTIFICATION: <reason>' or resolve the architectural issue.

**Bad:**
```python
# pylint: disable=too-many-locals
def complex_func(): ...
```

**Clean:**
```python
# JUSTIFICATION: Complex legacy formula requires many local vars.
# pylint: disable=too-many-locals
def complex_func(): ...
```

## Snowflake Governance (W96xx)

### W9601: Select Star
**Message:** Select Star Violation: 'SELECT *' detected.
**Clean Fix:** List all required columns explicitly.

### W9602: Gold Layer View
**Message:** Gold Layer View Warning.
**Clean Fix:** Materialize the view or use a Dynamic Table.

### W9603: Gold Schema Evolution
**Message:** Gold Layer Schema Evolution.
**Clean Fix:** Disable auto-evolution and manage schema migrations explicitly.
