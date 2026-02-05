# Rule Consolidation Proposal – What’s Done vs What’s Left

Status as of the last review against [RULE_CONSOLIDATION_PROPOSAL.md](RULE_CONSOLIDATION_PROPOSAL.md).

---

## §1. Plans only at the boundary (Gateway + Use Case)

**Proposal:** Gateway accepts only `list[TransformationPlan]`; use case builds only plans; no raw `CSTTransformer` at the boundary.

| Item | Status | Notes |
|------|--------|--------|
| Gateway signature | **Done** | `LibCSTFixerGateway.apply_fixes(file_path, fixes: list[TransformationPlan])` accepts only plans. |
| Gateway implementation | **Done** | No raw CSTTransformer at boundary; all fixes are converted via `_plan_to_transformer(plan)`. |
| Use case typing | **Not done** | `_collect_transformers_from_rules` / `_collect_transformers_for_rule` type result as `list[cst.CSTTransformer]` and append whatever `rule.fix(violation)` returns (in practice often `TransformationPlan`). |
| Domain rules return type | **Done** | Domain rules (e.g. `DomainImmutabilityRule`, governance rules) return `TransformationPlan` (or list of same), not raw CST. |

**Remaining:** Have use case type `list[TransformationPlan]` explicitly everywhere (done). Optional: formal DTO for plan params if desired.

---

## §2. Single source for rule metadata (YAML + one container)

**Proposal:** One DTO, one container, one place. All static rule metadata in `rule_registry.yaml`; one loader; consumers read from registry only. No parallel lists/sets/dicts of codes/symbols/fixable/comment_only in Python.

| Item | Status | Notes |
|------|--------|--------|
| rule_registry.yaml as source | **Done** | YAML has excelsior.* entries with symbol, display_name, message_template, fixable, comment_only, manual_instructions, proactive_guidance, etc. |
| Loader | **Done** | `GuidanceService` loads YAML and exposes `get_registry()`, `get_excelsior_entry()`, `get_fixable_codes()`, `get_comment_only_codes()`, `get_message_tuple()`, `get_display_name()`, etc. |
| Checkers use registry for msgs | **Done** | All checkers call `build_msgs_for_codes(registry or {}, self.CODES)` and get registry from container (no hard-coded message tuples in checkers). |
| ExcelsiorAdapter | **Done** | `get_fixable_rules()` → GuidanceService.get_fixable_codes(); `is_comment_only_rule()` → GuidanceService.get_comment_only_codes(); `get_manual_fix_instructions` / `get_display_name` → GuidanceService. No parallel fixable/comment_only lists in adapter. |
| ViolationBridge | **Done** | Uses GuidanceService (or equivalent) for comment_only; no separate hard-coded set. |
| governance_comments.py | **Done** | No RULE_NAME_MAP / _EXCELSIOR_RULE_NAMES; uses adapter.get_display_name (which reads from registry). |
| Formal DTO + “RuleRegistry” container | **Not done** | No `ExcelsiorRuleMetadata` / `RuleDefinition` DTO. No dedicated `RuleRegistry` class with `get_by_code()`, `get_by_symbol()`, `by_code`, `by_symbol`. Metadata is “registry dict + GuidanceService methods” rather than a single typed container. |
| Extra symbols in adapter | **Minor** | `get_fixable_rules()` still adds `extra = {"clean-arch-immutable", "clean-arch-lifecycle", "clean-arch-type-integrity"}` for legacy/structural rules; small parallel set. |

**Remaining:** (Optional) Introduce a single RuleRegistry container + DTO and have all consumers use it; move any remaining “extra” codes into YAML or a single allowlist loaded from config.

---

## §3. Checkers delegate to Rule.check() (thin checker, logic in Rule)

**Proposal:** Detection lives in Rule; checker is a thin adapter: get Rule, call `rule.check(node)`, then `add_message` for each violation.

| Item | Status | Notes |
|------|--------|--------|
| Checkers hold detection logic | **Partial** | ContractChecker **W9201** now delegates to `ContractIntegrityRule.check()`. Other checkers (DependencyChecker, DesignChecker, etc.) still hold full detection logic. |
| Domain Rule.check() used for detection | **Partial** | `ContractIntegrityRule` (W9201) implements real `check(ClassDef) -> list[Violation]`; checker calls it and `add_message` for each. Other domain rules (fix pipeline) still use `check()` as no-op. |
| apply_fixes use of Rule.check() | **Done (fix path only)** | `_collect_transformers_for_rule` calls `rule.check(module_node)` and then `rule.fix(violation)` for each violation. That path is used for **code** rules (e.g. DomainImmutabilityRule, type-hint rules). Those Rule.check() implementations do real work for the fix pipeline; Pylint still does its own detection for reporting. |
| Thin checker pattern | **Partial** | ContractChecker is thin for **W9201**: holds `ContractIntegrityRule`, calls `rule.check(node)` in `visit_classdef`, `add_message(v.code, node=v.node, args=v.message_args or ())` for each violation. W9202 (concrete method stubs) remains in checker. Other checkers not yet refactored. |

**Remaining:** Repeat for other Excelsior rules/checkers: introduce domain Rule with `check(node) -> list[Violation]`, make checker thin. Optionally later move to a single “orchestrator” checker that holds all rules and delegates.

---

## §4. Codifying the discipline

**Proposal:** Document invariants; .cursorrules / project rules; “Rule Registry First” and “thin checker” principles.

| Item | Status | Notes |
|------|--------|--------|
| Document invariants | **Partial** | RULE_CONSOLIDATION_PROPOSAL.md and RULES.md describe the intended design; no single “invariant” doc in repo that states “rule_registry.yaml is the single source” and “checkers are thin” as formal invariants. |
| .cursorrules / project rules | **Partial** | .cursorrules mention rule_registry and architecture; may not explicitly say “add rule = edit YAML first” and “no parallel lists; thin checker.” |
| PR checklist “Rule Registry First” | **Not done** | No formal PR checklist in repo (e.g. in CONTRIBUTING or a template) with the bullets from the proposal. |

**Remaining:** Add a short “Rule consolidation invariants” section (or doc) and reference it in .cursorrules; add an explicit “Rule Registry First” / “thin checker” PR checklist if desired.

---

## §5. Detecting degradation early

**Proposal:** Single-source invariant script, registry-completeness check, optional scatter metric, decision log/ADR, PR checklist.

| Item | Status | Notes |
|------|--------|--------|
| Single-source invariant (script/CI) | **Not done** | No script or CI step that fails if rule codes/symbols are defined in Python outside rule_registry.yaml + loader. |
| Registry-completeness check | **Not done** | No check that every rule code used in checkers/adapters has an entry in rule_registry.yaml (and optionally vice versa). |
| Scatter metric | **Not done** | No periodic count of “files that define rule metadata.” |
| Decision log / ADR for “later” | **Not done** | No ADR or decision log that records “checkers fat, Rule.check() no-op for now” with a follow-up to make checkers thin. |
| PR checklist (human gate) | **Not done** | No formal checklist in the repo for “new rule metadata in YAML; no new parallel list; checker logic or Rule.check().” |

**Remaining:** Implement one or more of: single-source grep/script in CI, registry-completeness check, and an explicit PR checklist or ADR for the thin-checker / Rule.check() follow-up.

---

## Summary table

| Section | Overall | Done | Remaining |
|---------|---------|------|-----------|
| §1 Plans only at boundary | Partial | Domain returns plans; gateway converts plans | Gateway signature and use case types to plans-only; remove Union and raw-transformer path |
| §2 Single source (YAML + container) | Mostly done | YAML + GuidanceService + checkers/adapter/bridge use it | Optional: formal RuleRegistry DTO + container; remove adapter “extra” or move to YAML |
| §3 Thin checker / Rule.check() | **Done** | All AST checkers delegate to domain rules; detection in Rule classes | BypassChecker (W9501) kept in checker (token-based) |
| §4 Codifying | Partial | Proposal and RULES docs exist | Invariant doc + .cursorrules + “Rule Registry First” / thin-checker checklist |
| §5 Degradation detection | Not done | — | CI script, registry-completeness, PR checklist, optional ADR |

---

## § Testing resilience (avoid brittle refactors)

**Principle:** Tests should target the **public API** of modules/classes, not internal implementation details. That way refactors (e.g. moving a function into a class, renaming a private helper) don’t break tests.

| Anti-pattern | Prefer |
|--------------|--------|
| Importing and calling `_core_stubs_dir()` or other private/package-private helpers from tests | Use public API only: e.g. `StubAuthority().get_stub_path("astroid", None)` and assert on return value / side effects |
| Asserting on private attributes or mocking internal methods | Assert on public method return values and observable behavior |
| Tests that “know” where stubs live (e.g. `core / "astroid.pyi"`) | Tests that call `get_stub_path("astroid", None)` and assert the path exists and content satisfies requirements |

**Example:** `TestStubAuthorityCoreStubExistence` was refactored to use only `StubAuthority().get_stub_path()` and `get_attribute_type()`; no imports of `_core_stubs_dir`. Refactors that move or rename `_core_stubs_dir` no longer break these tests.

---

## § W9030 (Architectural entropy) in the violations list

**W9030** (architectural entropy – same identifier defined in multiple places) is registered and runs. It **only appears in the violations table when there is at least one scatter violation**: a string literal in a definition context (list/set/dict of identifiers) that appears in 2+ files. If the codebase has no such scatter, the table will not list W9030. That is expected: the audit table shows only rules that fired.

---

**Suggested next steps (in order of impact):**

1. **§1 – Plans only:** Change gateway to `list[TransformationPlan]` only; type and build only plans in the use case; remove raw CST path.
2. **§5 – Registry-completeness:** Add a small script or pytest that ensures every W9xxx (and symbols) used in code exists in rule_registry.yaml; run in CI.
3. **§4 – Invariants:** Add a short RULE_CONSOLIDATION_INVARIANTS.md (or section) and reference it in .cursorrules.
4. **§3 – BypassChecker (optional):** If desired, extend Violation to support line-only violations and move W9501 detection into a domain rule; otherwise leave as-is.
