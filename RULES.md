# 🛡️ Excelsior v2: Architectural Autopilot Rules

This catalog details all the rules enforced by `excelsior-architect` (Excelsior), along with examples of "Bad" code and the corresponding "Clean Fix".

**Rule Count:** 35 rules (30 violations + 5 pattern suggestions)

- **Boundary Rules (W90xx):** 20 rules enforcing Clean Architecture layer boundaries and design principles
- **Testing Rules (W91xx):** 2 rules for test quality and coupling
- **Contract Rules (W92xx):** 2 rules for Domain/Infrastructure contracts
- **DI Rules (W93xx):** 2 rules for dependency injection
- **Anti-Bypass (W95xx):** 1 rule preventing architectural workarounds
- **Immutability (W96xx):** 1 rule for Domain immutability
- **Pattern Suggestions (W904x):** 5 informational suggestions (not violations)

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

### W9014: UI Concern in Domain
**Message:** UI concern (%s) in Domain layer.
**Clean Fix:** Move UI logic to Interface layer; inject display port to Domain.

**Bad:**
```python
# domain/report.py
def format_output(self):
    return f"\033[32m{self.status}\033[0m"  # ANSI codes in Domain
```

**Clean:**
```python
# domain/protocols.py
class DisplayPort(Protocol):
    def colorize(self, text: str, color: str) -> str: ...

# domain/report.py
def format_output(self, display: DisplayPort):
    return display.colorize(self.status, "green")
```

### W9015: Missing Type Hint
**Message:** Missing Type Hint: %s in %s signature.
**Clean Fix:** Add explicit type hints to all parameters and the return value.

**Bad:**
```python
def process_order(order_id, customer):
    return {"status": "processed"}
```

**Clean:**
```python
def process_order(order_id: str, customer: Customer) -> dict[str, str]:
    return {"status": "processed"}
```

### W9016: Any Type Hint
**Message:** Banned Any type: %s.
**Clean Fix:** Use specific types; create a Protocol if needed.

**Bad:**
```python
from typing import Any

def process_data(data: Any) -> Any:
    return data.transform()
```

**Clean:**
```python
# domain/protocols.py
class Transformable(Protocol):
    def transform(self) -> dict[str, str]: ...

# use_cases/processor.py
def process_data(data: Transformable) -> dict[str, str]:
    return data.transform()
```

### W9017: Layer Integrity
**Message:** Layer integrity: unmapped file in src/ %s.
**Clean Fix:** Map the file to a layer in configuration or move to appropriate package.

### W9018: No Top-Level Functions
**Message:** No top-level functions: %s.
**Clean Fix:** Move functions into classes. Only `__main__.py` and `checker.py` may have top-level functions.

**Bad:**
```python
# domain/helpers.py
def calculate_total(items):  # Top-level function
    return sum(item.price for item in items)
```

**Clean:**
```python
# domain/calculator.py
class OrderCalculator:
    @staticmethod
    def calculate_total(items: list[Item]) -> Decimal:
        return sum(item.price for item in items)
```

### W9019: Unstable Dependency
**Message:** Uninferable dependency: create stubs/%s.pyi.
**Clean Fix:** Create type stubs for external dependencies to enable type checking.

### W9020: Global State
**Message:** Global state: use of 'global %s' not allowed.
**Clean Fix:** Use dependency injection; pass state through constructors or method arguments.

**Bad:**
```python
_cache = {}

def update_cache(key, value):
    global _cache  # Global state
    _cache[key] = value
```

**Clean:**
```python
class CacheService:
    def __init__(self):
        self._cache: dict[str, Any] = {}

    def update(self, key: str, value: Any) -> None:
        self._cache[key] = value
```

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

## Architectural Quality (W903x)

### W9030: Architectural Entropy
**Message:** Scatter: %s in %d files.
**Clean Fix:** Consolidate duplicate identifiers into a single canonical location.

**Bad:**
```python
# services/auth.py
VALID_ROLES = ["admin", "user", "guest"]

# services/permissions.py
VALID_ROLES = ["admin", "user", "guest"]  # Duplicate
```

**Clean:**
```python
# domain/constants.py
VALID_ROLES = ["admin", "user", "guest"]

# services/auth.py
from domain.constants import VALID_ROLES

# services/permissions.py
from domain.constants import VALID_ROLES
```

### W9032: Method Complexity
**Message:** Method '%s' has cyclomatic complexity %d (threshold %d).
**Clean Fix:** Extract logic into smaller, focused methods.

**Bad:**
```python
def process_order(self, order):
    if order.priority == "high":
        if order.items:
            for item in order.items:
                if item.stock > 0:
                    # Complex nested logic...
                    pass
    # Cyclomatic complexity > 10
```

**Clean:**
```python
def process_order(self, order: Order) -> None:
    if not self._should_process(order):
        return
    self._allocate_inventory(order)
    self._calculate_shipping(order)

def _should_process(self, order: Order) -> bool:
    return order.priority == "high" and order.items
```

### W9033: Interface Segregation
**Message:** Protocol '%s' has %d methods (limit %d). Consider splitting into focused sub-protocols.
**Clean Fix:** Split large protocols into smaller, focused interfaces.

**Bad:**
```python
class UserRepository(Protocol):
    def create(self, user: User) -> User: ...
    def update(self, user: User) -> User: ...
    def delete(self, user_id: str) -> None: ...
    def find_by_id(self, user_id: str) -> User: ...
    def find_by_email(self, email: str) -> User: ...
    def list_all(self) -> list[User]: ...
    def search(self, query: str) -> list[User]: ...
    def count(self) -> int: ...
    # 8+ methods - too many!
```

**Clean:**
```python
class UserReader(Protocol):
    def find_by_id(self, user_id: str) -> User: ...
    def find_by_email(self, email: str) -> User: ...
    def search(self, query: str) -> list[User]: ...

class UserWriter(Protocol):
    def create(self, user: User) -> User: ...
    def update(self, user: User) -> User: ...
    def delete(self, user_id: str) -> None: ...
```

### W9034: Constructor Injection
**Message:** Parameter '%s' in %s.__init__ is typed to concrete '%s'. Prefer a Protocol.
**Clean Fix:** Type constructor parameters to Protocols, not concrete classes.

**Bad:**
```python
class OrderProcessor:
    def __init__(self, repo: SqlOrderRepository):  # Concrete type
        self._repo = repo
```

**Clean:**
```python
# domain/protocols.py
class OrderRepository(Protocol):
    def save(self, order: Order) -> None: ...

# use_cases/processor.py
class OrderProcessor:
    def __init__(self, repo: OrderRepository):  # Protocol type
        self._repo = repo
```

### W9035: Exception Hygiene
**Message:** Bare 'except:' catches all; use 'except Exception:' and re-raise or handle explicitly.
**Clean Fix:** Use specific exception types and always re-raise or log.

**Bad:**
```python
try:
    result = dangerous_operation()
except:  # Bare except - swallows everything
    pass
```

**Clean:**
```python
try:
    result = dangerous_operation()
except ValueError as e:
    logger.error(f"Invalid value: {e}")
    raise
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    raise
```

## Pattern Suggestions (W904x - INFO level)

These are informational suggestions, not violations. They recommend design patterns when certain code patterns are detected.

### W9041: Builder Pattern Suggestion
**Message:** __init__ of '%s' has %d parameters; consider Builder pattern.
**Suggestion:** For classes with 6+ constructor parameters, use a Builder to improve readability.

**Current:**
```python
class Report:
    def __init__(self, title, author, date, format, recipients, cc, bcc, priority):
        # 8 parameters - hard to read
        pass
```

**Consider:**
```python
class ReportBuilder:
    def with_title(self, title: str) -> ReportBuilder: ...
    def with_author(self, author: str) -> ReportBuilder: ...
    def build(self) -> Report: ...

report = ReportBuilder().with_title("Q4").with_author("Alice").build()
```

### W9042: Factory Pattern Suggestion
**Message:** if/elif instantiating different classes (%s); consider Factory.
**Suggestion:** Use a Factory when you have conditional instantiation logic.

**Current:**
```python
if report_type == "pdf":
    return PDFReport(data)
elif report_type == "html":
    return HTMLReport(data)
elif report_type == "csv":
    return CSVReport(data)
```

**Consider:**
```python
class ReportFactory:
    _creators = {
        "pdf": PDFReport,
        "html": HTMLReport,
        "csv": CSVReport,
    }

    def create(self, report_type: str, data: dict) -> Report:
        creator = self._creators.get(report_type)
        if not creator:
            raise ValueError(f"Unknown type: {report_type}")
        return creator(data)
```

### W9043: Strategy Pattern Suggestion
**Message:** if/elif chain with %d branches selecting behavior; consider Strategy pattern.
**Suggestion:** Replace conditional algorithm selection with Strategy pattern.

**Current:**
```python
def calculate_shipping(self, method: str, weight: float) -> Decimal:
    if method == "standard":
        return weight * Decimal("5.00")
    elif method == "express":
        return weight * Decimal("15.00")
    elif method == "overnight":
        return weight * Decimal("25.00")
```

**Consider:**
```python
class ShippingStrategy(Protocol):
    def calculate(self, weight: float) -> Decimal: ...

class StandardShipping(ShippingStrategy):
    def calculate(self, weight: float) -> Decimal:
        return weight * Decimal("5.00")

strategies = {
    "standard": StandardShipping(),
    "express": ExpressShipping(),
}
```

### W9044: State Pattern Suggestion
**Message:** Repeated conditionals on '%s' in %d methods; consider State pattern.
**Suggestion:** When multiple methods check the same state attribute, use State pattern.

**Current:**
```python
class Order:
    def approve(self):
        if self.status == "pending":
            # approve logic
        elif self.status == "approved":
            raise InvalidStateError()

    def cancel(self):
        if self.status == "pending":
            # cancel logic
        elif self.status == "shipped":
            raise InvalidStateError()
```

**Consider:**
```python
class OrderState(Protocol):
    def approve(self, order: Order) -> None: ...
    def cancel(self, order: Order) -> None: ...

class PendingState(OrderState):
    def approve(self, order: Order) -> None:
        order.state = ApprovedState()
```

### W9045: Facade Pattern Suggestion
**Message:** Method '%s' calls %d distinct dependency objects; consider Facade.
**Suggestion:** When a method orchestrates 5+ dependencies, create a Facade.

**Current:**
```python
def process_order(self, order_id: str):
    user = self.user_service.get_user(order_id)
    inventory = self.inventory_service.check(order_id)
    payment = self.payment_service.process(order_id)
    shipping = self.shipping_service.calculate(order_id)
    notification = self.notification_service.send(order_id)
    # Using 5+ dependencies
```

**Consider:**
```python
class OrderFacade:
    def __init__(self, user_svc, inv_svc, pay_svc, ship_svc, notif_svc):
        # Bundle related services
        pass

    def process_complete_order(self, order_id: str) -> OrderResult:
        # Simplified interface
        pass
```

## Anti-Bypass Guard (W95xx)

### W9501: Anti-Bypass Violation
**Message:** Anti-Bypass Violation: %s detected.
**Clean Fix:** Justify with '# JUSTIFICATION: <reason>' or resolve the architectural issue.
