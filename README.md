# Clean Architecture Linter Plugin

A generic Pylint plugin designed to enforce Clean Architecture constraints, design patterns, and solid coding principles.

## Clean Architecture Resources

For a deeper understanding of Clean Architecture principles, please refer to:
- [The Clean Architecture (Uncle Bob)](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Clean Architecture in Python (Book)](https://www.packetpub.com/product/clean-architecture-in-python/9781788835824) (Reference)

![Clean Architecture Diagram](https://blog.cleancoder.com/uncle-bob/images/2012-08-13-the-clean-architecture/CleanArchitecture.jpg)

## Features

- **W9003**: Protected Member Access (Visibility contracts).
- **W9004**: Abstract Resource Access Bans (e.g., no DB in Domain).
- **W9005**: Delegation Anti-Pattern detection.
- **W9006**: Law of Demeter violations.
- **W9007**: Naked Return checks (Decoupling).
- **W9008**: Unused parameter enforcement in abstract layers.

## Rules & Examples

### W9003: Protected Member Access
Accessing `_protected` members from outside their defining class/scope is forbidden.

**❌ Bad:**
```python
# In module: services.py
from domain import entity

def process():
    user = entity.User()
    print(user._password_hash) # Violation!
```

**✅ Good:**
```python
# In module: services.py
def process():
    user = entity.User()
    print(user.get_password_hash()) # Use public interface
```

### W9004: Abstract Resource Access Violation
Layers not explicitly allowed to access resources (DB, Network) cannot make direct calls to them.

**❌ Bad (in Domain Layer):**
```python
# snowfort/shared/user.py
import requests

def get_user_data(id):
    return requests.get(f"api/users/{id}") # Violation: Domain cannot access network!
```

**✅ Good:**
```python
# snowfort/shared/user.py
# Define an interface instead
class UserRepository:
    def get_user(self, id): pass

# Implementation in Infrastructure layer handled via dependency injection
```

### W9005: Delegation Anti-Pattern
Flags methods that do nothing but delegate to another method depending on a simple condition.

**❌ Bad:**
```python
def handle_request(type):
    if type == 'A':
        return handler_a()
    elif type == 'B':
        return handler_b()
    # Violation: Just a switch statement delegating execution.
```

**✅ Good:**
```python
# Use a Dictionary mapping or Strategy pattern
handlers = {'A': handler_a, 'B': handler_b}
def handle_request(type):
    return handlers[type]()
```

### W9006: Law of Demeter Violation
Avoid long chains of object access (more than one dot).

**❌ Bad:**
```python
def get_zip(order):
    return order.customer.address.zip_code # Violation: specific knowledge of internal structure
```

**✅ Good:**
```python
def get_zip(order):
    return order.get_customer_zip_code() # Delegated method
```

### W9007: Naked Return Violation
Abstract/Domain layers should return Entities or Value Objects, not raw database cursors or HTTP responses.

**❌ Bad:**
```python
def get_users():
    return db.cursor().fetchall() # Violation: Returning raw DB rows
```

**✅ Good:**
```python
def get_users():
    rows = db.cursor().fetchall()
    return [User(row) for row in rows] # Return Domain Entities
```

### W9008: Unused Parameters in Interfaces
Abstract methods or interfaces should not define parameters they don't intend to use or enforce.

**❌ Bad:**
```python
def update(self, user_id, force=False):
    # 'force' is never used in this implementation logic
    self.repo.save(user_id)
```

## Configuration

Configure via `pyproject.toml`:

```toml
[tool.clean-architecture-linter]
visibility_enforcement = true

[[tool.clean-architecture-linter.layers]]
name = "Domain"
module = "myproject.domain"
allowed_resources = []
```
