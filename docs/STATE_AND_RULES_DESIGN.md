# State and Rules: Why Some Rules Don't Fit BaseRule

This doc explains why some domain rules (like `TestingCouplingRule`) don't use the standard `BaseRule` interface, what "state" means here, and two ways to design them—with examples, trade-offs, and a recommendation.

---

## Part 1: The Problem (Explain Like I'm 10)

### The tree walk

Imagine Pylint is walking through your code like a guard in a building:

1. **Enter a room** (e.g. a function) → `visit_functiondef` runs.
2. **Look around inside** (expressions, calls, etc.) → `visit_call`, `visit_assign`, etc.
3. **Leave the room** → `leave_functiondef` runs.

The guard only gets these callbacks in that order. So the **checker** (the thing Pylint talks to) is the one that "knows" where we are in the tree and in what order things happened.

### What we need to remember (state)

For the **testing** rule we care about two things **per test function**:

1. **Which function we're in** — "Are we inside a `test_*` function right now?"
2. **How many mocks we've seen in that function** — "So far in this test we've seen 3 `Mock()` / `patch()` calls."

When we **leave** the test function, we need to say: "If we saw more than 4 mocks, report W9101 (fragile test)." So we have to **remember** (hold state):

- `current_function` — the `test_foo` we're inside (or `None` if we're not in a test).
- `mock_count` — how many mock calls we've seen in that test so far.

The rule logic is: "Given this call node and the fact we're in `current_function`, is it a mock? Given we're leaving `current_function` and we had `mock_count` mocks, do we report W9101?"

### Why the state can't hide inside the rule

If we put `current_function` and `mock_count` **inside** the rule:

- The **checker** would still have to call the rule in the right order (visit function → visit calls → leave function), because **Pylint only talks to the checker**, not the rule.
- So the checker would do: "I'm entering a test function → tell the rule to set current_function. I'm visiting a call → ask the rule if it's a mock and to increment. I'm leaving → ask the rule if we exceeded the limit."
- That means the **rule** would have to have methods like `set_current_function`, `increment_mock_count`, etc. The rule would become **stateful**: it would hold hidden state that changes over time.
- Then testing the rule gets weird: you have to "play" a whole visit sequence to put the rule in the right state before testing one behavior. And if two tests share the same rule instance, they can step on each other's state.

So: **the checker is the only one that gets the visit/leave callbacks in order, so it's the natural place to hold "where we are" and "how many mocks so far."** The rule can stay **stateless**: it only needs to answer "given this node and this context (current_function, mock_count), what violations do you see?" Then the checker owns the state and passes it in as arguments. The rule never remembers anything between calls.

**Summary (ELI10):** The guard (checker) walks the building (AST) and gets "entered a room" / "left the room" events. So the guard has to remember "which room I'm in" and "how many mocks in this room." If the rule tried to remember that, the guard would still have to tell it every time—and then the rule would be holding secret state that's hard to test. So we keep the state in the checker and pass it into the rule each time.

---

## Part 2: What State the Checker Holds (Testing Example)

For **CleanArchTestingChecker** (W9101, W9102), the checker holds:

| State | Type | Meaning |
|-------|------|--------|
| `_current_function` | `Optional[FunctionDef]` | The `test_*` function we're inside; `None` when not in a test. |
| `_mock_count` | `int` | Number of Mock/MagicMock/patch calls seen in the current test function. |

**When it changes:**

- **visit_functiondef**: If the function is `test_*`, set `_current_function = node` and `_mock_count = 0`. Otherwise `_current_function` stays (e.g. `None`).
- **visit_call**: Ask the rule `record_mock_only(node, _current_function)`; if True, `_mock_count += 1`. Then ask `record_call(node, _current_function)` and report any W9102 violations.
- **leave_functiondef**: Ask the rule `leave_functiondef(_current_function, _mock_count)`; report any W9101 violations. Then set `_current_function = None`.

The **rule** never reads or writes that state; the checker passes `_current_function` and `_mock_count` (or their effects) as arguments. So the rule stays stateless and easy to test.

---

## Part 3: Solution 1 — State Stays in Checker, Passed as Arguments (Current Pattern)

**Idea:** The checker owns all state. The rule is a stateless bag of functions: every method receives everything it needs (current node + any context) and returns violations or a simple result (e.g. "was this a mock?"). No protocol required beyond "these are the methods the checker will call."

### Example (conceptual)

**Checker (owns state, drives the walk):**

```python
class CleanArchTestingChecker(BaseChecker):
    def __init__(self, ...):
        self._testing_rule = TestingCouplingRule()
        self._current_function: Optional[astroid.nodes.FunctionDef] = None
        self._mock_count: int = 0

    def visit_functiondef(self, node):
        tracked = self._testing_rule.record_functiondef(node)
        self._current_function = tracked
        if tracked is not None:
            self._mock_count = 0

    def visit_call(self, node):
        if self._testing_rule.record_mock_only(node, self._current_function):
            self._mock_count += 1
        for v in self._testing_rule.record_call(node, self._current_function):
            self.add_message(v.code, node=v.node, args=v.message_args or ())

    def leave_functiondef(self, node):
        for v in self._testing_rule.leave_functiondef(
            self._current_function, self._mock_count
        ):
            self.add_message(...)
        self._current_function = None
```

**Rule (stateless; only receives context as arguments):**

```python
class TestingCouplingRule:
    def record_functiondef(self, node) -> Optional[FunctionDef]:
        """Return node if test_* function, else None. Caller sets current_function and mock_count."""
        if getattr(node, "name", "").startswith("test_"):
            return node
        return None

    def record_call(self, node, current_function: Optional[FunctionDef]) -> list[Violation]:
        """Return W9102 violations for private method calls. Uses current_function only to know 'we're in a test'."""
        if not current_function:
            return []
        # ... inspect node, return violations

    def record_mock_only(self, node, current_function: Optional[FunctionDef]) -> bool:
        """Return True if call is Mock/MagicMock/patch. Caller increments mock_count."""
        ...

    def leave_functiondef(
        self, current_function: Optional[FunctionDef], mock_count: int
    ) -> list[Violation]:
        """Return W9101 violations if mock_count > limit. Caller sets current_function=None after."""
        if current_function and mock_count > 4:
            return [Violation(...)]
        return []
```

**Characteristics:**

- State lives only in the checker; rule has no instance state for the walk.
- Rule methods are pure in the sense of "same inputs → same outputs"; easy to unit test by passing different `current_function` / `mock_count`.
- No formal protocol: the checker just calls the methods it needs. The rule doesn't implement `BaseRule` because it doesn't have a single `check(node)`; it has multiple entry points (record_*, leave_*).

---

## Part 4: Solution 2 — Separate Protocol for Stateful (Visit/Leave) Rules

**Idea:** Separate the one-and-done **check** protocol from the **fix** protocol from the **multi-step** protocol. Keep `BaseRule` as Checkable + Fixable for one-shot fixable rules. Introduce **StatefulRule** for rules that participate in a **multi-step visit/leave** flow and receive **context from the checker** (so the rule still doesn't hold the state; the protocol just names the contract).

### Implemented protocols (in `domain/rules/__init__.py`)

```python
from typing import Protocol, Optional
import astroid

class StatefulRule(Protocol):
    """
    Rule that is driven by the checker across visit/leave callbacks.
    Checker holds state; rule receives it as arguments. Rule remains stateless.
    """
    code: str  # or multiple codes, e.g. code_mocks, code_private
    description: str

    # The checker calls these in order during the AST walk.
    # State (current_function, mock_count, etc.) is always passed in by the checker.

    def record_functiondef(self, node: astroid.nodes.NodeNG) -> Optional[astroid.nodes.FunctionDef]:
        """Return node if this starts a tracked scope (e.g. test_*); else None."""
        ...

    def record_call(
        self,
        node: astroid.nodes.NodeNG,
        current_function: Optional[astroid.nodes.FunctionDef],
    ) -> list[Violation]:
        """Called for each Call inside the scope. Return violations (e.g. W9102)."""
        ...

    def record_mock_only(
        self,
        node: astroid.nodes.NodeNG,
        current_function: Optional[astroid.nodes.FunctionDef],
    ) -> bool:
        """Return True if this call counts as a mock (caller increments count)."""
        ...

    def leave_functiondef(
        self,
        current_function: Optional[astroid.nodes.FunctionDef],
        mock_count: int,
    ) -> list[Violation]:
        """Called when leaving the scope. Return violations (e.g. W9101)."""
        ...
```

**Checkable**, **Fixable**, **StatefulRule**, and **BaseRule** are defined in `domain/rules/__init__.py`. `TestingCouplingRule` conforms to **StatefulRule** (structural subtyping; no explicit inheritance needed). The **checker** still holds state and passes it in; the protocol doesn't add state to the rule, it just documents the **API** that stateful rules expose so that:

- New stateful rules (e.g. module structure, Demeter) can be written to the same or a related contract.
- Type checkers and IDEs know what methods the checker can call.
- It's explicit that these rules are "visit/leave driven" rather than "single check(node)".

**Characteristics:**

- Clear split: **Checkable** = one-shot `check(node)`; **Fixable** = optional fix capability; **StatefulRule** = visit/leave API with context passed in; **BaseRule** = Checkable + Fixable for backward compatibility.
- State still lives in the checker; the protocol only describes the rule's interface.
- Slightly more boilerplate (defining and maintaining the protocol), but better discoverability and consistency for all stateful rules.

---

## Part 5: Key Differences and Pros/Cons

| Aspect | Solution 1 (State as args, no protocol) | Solution 2 (StatefulRule protocol) |
|--------|----------------------------------------|-------------------------------------|
| **Where state lives** | Checker | Checker (same) |
| **Rule stateful?** | No | No |
| **Formal contract** | None; checker just calls what it needs | Protocol documents visit/leave API |
| **Fits BaseRule?** | No (different entry points) | No (same) |
| **Testability** | Same: pass in context, assert on violations/return values | Same |
| **Discoverability** | You have to read the checker to see what the rule must implement | Protocol is the single place that describes the contract |
| **New stateful rules** | Copy pattern from existing checker/rule | Implement StatefulRule (or a variant) and match checker to it |
| **Type checking** | Rule is "any object with these methods" | Rule is explicitly StatefulRule |

**Pros of Solution 1:**

- No extra types or files; minimal ceremony.
- Already what we do today; no migration.

**Cons of Solution 1:**

- No single place that says "this is what a stateful rule looks like"; easy for the next stateful rule to drift (e.g. different method names or signatures).

**Pros of Solution 2:**

- One clear contract for "rules that need visit/leave and context from the checker."
- Easier to add new stateful rules and to keep checkers aligned (same method names, same meaning of arguments).
- Type checker can enforce that the rule implements the protocol.

**Cons of Solution 2:**

- Need to define and maintain the protocol (and possibly variants if e.g. module structure has a different set of methods).
- Slightly more upfront work.

---

## Part 6: Recommendation

**Recommendation: adopt Solution 2 (a dedicated protocol for stateful rules), while keeping state in the checker and passing it as arguments.**

Reasons:

1. **State must stay in the checker** either way—because Pylint’s visit/leave order is only visible there. So we don’t change who holds state; we only make the rule’s API explicit.
2. We already have **several** stateful rules (TestingCoupling, LawOfDemeter, ModuleStructure, DesignRule). A shared protocol gives them a common shape and prevents each one from inventing slightly different method names or signatures.
3. **BaseRule** stays the single contract for "one node → violations" rules. Stateful rules get their own contract instead of pretending to be BaseRule or living as ad-hoc objects.
4. The protocol is **small and stable**: a few methods with clear names and "context passed in by checker." Adding it is low cost; maintaining it is mostly "new stateful rules implement this."

**Concrete steps:**

1. Add a `StatefulRule` (or `VisitLeaveRule`) protocol in `domain/rules/__init__.py` (or a small `stateful_rule.py`) that describes the TestingCoupling-style API (record_functiondef, record_call, record_mock_only, leave_functiondef, etc.). If one protocol can’t cover ModuleStructure or Demeter, use a base protocol plus rule-specific methods, or a small family of protocols.
2. Make `TestingCouplingRule` implement that protocol (formally or via typing).
3. Optionally, migrate `ModuleStructureRule` and/or `LawOfDemeterRule` to the same or a related protocol so that "stateful rule" has a single, documented shape across the codebase.

That way we keep "state in the checker, rule stateless and testable," and we make the design explicit and consistent instead of hidden in ad-hoc rule implementations.

---

## Part 7: Three Protocols (Checkable, Fixable, StatefulRule)

We separate the **one-and-done check** protocol from the **fix** protocol from the **multi-step** protocol so that no rule is forced to implement what it doesn’t support. Not all rules are fixable; some are multi-step, others are not.

### The three protocols

| Protocol | Purpose | What it requires |
|----------|--------|------------------|
| **Checkable** | One-and-done check | `code`, `description`, `check(node) -> list[Violation]`. No fix required. |
| **Fixable** | Optional fix capability | `fix_type`, `fix(violation)`, `get_fix_instructions(violation)`. Only for rules that support auto-fix or instructions. |
| **StatefulRule** | Multi-step visit/leave | Checker holds state; rule has `record_*`, `leave_*` (and related) methods with context passed in. Describes the testing-coupling style API. |

- **BaseRule** = **Checkable + Fixable** combined. Use for one-shot rules that are also fixable (e.g. DomainImmutabilityRule, MissingTypeHintRule). Prefer implementing Checkable and Fixable separately when a rule is only checkable or only fixable.

### How rules compose

A rule implements one or more of the protocols:

| Rule type | Implements | Example |
|-----------|------------|--------|
| Check-only | Checkable | DelegationRule, VisibilityRule, ResourceRule, EntropyRule, DIRule, LayerDependencyRule |
| Check + fix | Checkable + Fixable (or BaseRule) | DomainImmutabilityRule, MissingTypeHintRule, governance rules |
| Multi-step only | StatefulRule | TestingCouplingRule |
| Multi-step + fix | StatefulRule + Fixable | (Future, if needed) |

Checkers and the fix pipeline call only what a rule implements: if it’s Checkable, call `check(node)`; if it’s Fixable, call `fix()` / `get_fix_instructions()`; if it’s StatefulRule, call `record_*` / `leave_*` with context from the checker.

### Where they live

- **Checkable**, **Fixable**, **StatefulRule**, and **BaseRule** are defined in `src/excelsior_architect/domain/rules/__init__.py`.
- **StatefulRule** currently describes the testing-coupling API (record_functiondef, record_call, record_mock_only, check_private_method, leave_functiondef). Other stateful rules (e.g. ModuleStructureRule, LawOfDemeterRule in demeter.py) have different method sets and do not yet inherit a protocol; they can get their own protocols or variants later.

### Explicit protocol inheritance

Rule classes now explicitly inherit from the protocol they implement:

| Protocol | Rules |
|----------|--------|
| **Checkable** | DelegationRule, EntropyRule, VisibilityRule, ResourceRule, ContractIntegrityRule, ConcreteMethodStubRule, LayerDependencyRule, DIRule |
| **BaseRule** | DomainImmutabilityRule, MissingTypeHintRule, LawOfDemeterRule (governance_comments), GenericGovernanceCommentRule |
| **StatefulRule** | TestingCouplingRule |
| **(none yet)** | LawOfDemeterRule (demeter.py), ModuleStructureRule, DesignRule — different API; protocols TBD |
