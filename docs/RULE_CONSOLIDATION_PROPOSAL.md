# Rule Consolidation: Single Source of Truth & Unified Rule Model

This document answers your questions and proposes a concrete path to consolidate rule metadata and behavior, and to codify the discipline so it doesn’t regress.

**Canonical source:** Everything that **can** be in `rule_registry.yaml` **should** be there — static strings (with formatting rules), static strings, bools, and other hard-coded rule metadata. The runtime registry is **loaded from that file**. Adding or changing a rule **starts there**. Code only consumes the loaded registry; it does not define parallel lists, sets, or dicts of rule codes/symbols/fixable/comment_only/display names.

**Generalization:** For the same pattern applied beyond rules (cars, recipes, people, config, feature flags, etc.) and for detecting architectural entropy in forms we haven’t anticipated, see [ARCHITECTURAL_ENTROPY.md](ARCHITECTURAL_ENTROPY.md).

---


## 1. Why expose both `TransformationPlan` and `CSTTransformer`?

**Current state**

- `FixerGatewayProtocol.apply_fixes(file_path, fixes: list[SourceCodeFix])` — domain type is intentionally vague (`SourceCodeFix` is an empty protocol).
- **LibCSTFixerGateway** implements it as `fixes: list[Union[cst.CSTTransformer, TransformationPlan]]` and, for each item, does: if it’s a `TransformationPlan` → `_plan_to_transformer(plan)`; else use the object as a `CSTTransformer`.
- **ApplyFixesUseCase** gets `rule.fix(violation)` (typed in `BaseRule` as `Optional[CSTTransformer]`) but in practice domain rules return `TransformationPlan` (or `list[TransformationPlan]`). The use case appends those to a list and passes it to the gateway. So at runtime the list is effectively `list[TransformationPlan | cst.CSTTransformer]`.

**Why two levels exist**

- **Historical:** The protocol and use case were written when “fix” meant “return a LibCST transformer.” Domain was later refactored so rules return **TransformationPlan** (domain entity, no LibCST in domain). The gateway was updated to accept **both** so existing call paths didn’t have to change and so any leftover “raw transformer” path still worked.
- **No strong design reason** to keep accepting raw `CSTTransformer` at the gateway boundary. It was convenience/backward compatibility.

**Proposal: plans only at the boundary**

- **CSTTransformers should always be wrapped in a plan**, even when it’s “one transformer.”
- **Gateway:** Change signature to `apply_fixes(self, file_path: str, fixes: list[TransformationPlan]) -> bool`. Inside the gateway, **only** do `transformer = self._plan_to_transformer(plan)` and run that. No `Union`, no `isinstance(fix, TransformationPlan)` branch.
- **Use case:** Have `_collect_transformers_from_rules` (and any similar logic) build `list[TransformationPlan]`. If a rule today returned a raw `CSTTransformer`, either:
  - That rule is refactored to return a `TransformationPlan` (e.g. a new factory like `TransformationPlan.from_transformer(transformer)` if we ever need it), or
  - We introduce a single plan type that means “apply this pre-built transformer” (e.g. `TransformationType.APPLY_TRANSFORMER` with params holding a reference) and use it only inside infrastructure.
- **Result:** One level of abstraction at the boundary: “list of plans.” The gateway’s job is “interpret plans and turn them into LibCST transforms.” No dual API.

---

## 2. How many places redefine codes/strings? Single DTO + container

**Count of “rule config” definitions**

| Location | What’s defined | Overlap with others |
|---------|----------------|---------------------|
| **use_cases/checks/structure.py** | `self.msgs` (W9010, W9011, W9017, W9018, W9020): Pylint message tuple (template, symbol, description) | Same codes as elsewhere |
| **use_cases/checks/boundaries.py** | `self.msgs` (W9003, W9004) | Same codes |
| **use_cases/checks/patterns.py** | `self.msgs` (W9005, W9006, W9019) | Same codes |
| **use_cases/checks/design.py** | `self.msgs` (W9012, W9007, W9009, W9013, W9015, W9016) | Same codes |
| **use_cases/checks/contracts.py** | `self.msgs` (W9201, etc.) | Same codes |
| **use_cases/checks/immutability.py** | `self.msgs` (domain-immutability, W9601) | Same codes |
| **use_cases/checks/dependencies.py** | `self.msgs` (W9001) | Same codes |
| **use_cases/checks/di.py** | `self.msgs` (W9301) | Same codes |
| **use_cases/checks/bypass.py** | `self.msgs` (W9501) | Same codes |
| **use_cases/checks/testing.py** | `self.msgs` (testing rules) | Same codes |
| **excelsior_adapter.py** | `get_fixable_rules()` list; `is_comment_only_rule()` set; `w_to_string` dict; `fallback` manual instructions | Same codes in 4 shapes |
| **violation_bridge.py** | `comment_only_rules` set | Same set as adapter’s comment-only |
| **governance_comments.py** | `_EXCELSIOR_RULE_NAMES` / `RULE_NAME_MAP`: W* and clean-arch-* → display name | Same codes, display names only |
| **rule_registry.yaml** | excelsior.* entries: short_description, manual_instructions, proactive_guidance | Same codes, richer guidance |

So we have **at least 14+ places** that define or re-derive rule codes, string keys, fixable vs comment-only, display names, and messages. That’s the “exhausting to find where a given error code is defined” problem.

**Proposal: one DTO, one container, one place**

- **DTO (e.g. `ExcelsiorRuleMetadata` or `RuleDefinition`):**
  - `code: str` (e.g. `"W9010"`)
  - `symbol: str` (e.g. `"clean-arch-god-file"`) — Pylint symbol
  - `display_name: str` (e.g. `"God File"`)
  - `message_template: str` (for Pylint `msgs` tuple)
  - `description: str` (short, for docs/help)
  - `fixable: bool`
  - `comment_only: bool`
  - Optional: `manual_instructions: str` (or key into registry)

- **Container (e.g. `RuleRegistry` or `ExcelsiorRuleRegistry`):**
  - Holds all `RuleDefinition` (or equivalent) in one structure.
  - **Get by code:** `get_by_code("W9010")` → definition.
  - **Get by symbol:** `get_by_symbol("clean-arch-god-file")` → same definition.
  - **Dict-like:** e.g. `registry["W9010"]`, `registry.by_code`, `registry.by_symbol`.
  - **List-like:** iterate over all rules, filter fixable/comment-only, etc.
  - **Single load:** From one source (e.g. `rule_registry.yaml` plus a small code-side list for Pylint-specific fields like message_template, or one canonical Python module that builds the container from YAML + code).

- **Single source: rule_registry.yaml**
  - **Everything that CAN be in the YAML SHOULD be.** Static strings (message templates, display names, manual_instructions, proactive_guidance), bools (fixable, comment_only), symbols, codes, and formatting rules. The file is the **canonical** definition; no parallel definitions in Python.
  - **Load, don’t define.** One loader (e.g. in infrastructure) reads `rule_registry.yaml` and builds the in-memory container (DTOs keyed by code/symbol). Domain defines the DTO and the **interface** for “give me rule metadata”; infrastructure implements “load from YAML” and injects the container. If we need a new field (e.g. `message_template` for Pylint), add it to the YAML schema and the loader; do not add a separate Python dict elsewhere.
  - **Add/change a rule = edit YAML first.** New rule: add an entry to `rule_registry.yaml` (code, symbol, display_name, message_template, fixable, comment_only, manual_instructions, etc.). Then wire the Rule class and checker to the registry. Do not add the same rule code to a list in the adapter, a set in the bridge, and a dict in governance_comments.

- **Use everywhere**
  - **Checkers (structure, boundaries, patterns, design, etc.):** Don’t hold their own `self.msgs` dict. They get the message template (and symbol) from the container by code (or symbol). So each checker does something like: `msg = registry.get_by_code("W9010"); self.msgs = {msg.code: (msg.message_template, msg.symbol, msg.description)}` or, better, one shared “build msgs for these codes” from the container.
  - **excelsior_adapter:** `get_fixable_rules()` → `registry.fixable_codes()` (or iterate and filter). `is_comment_only_rule(code)` → `registry.get_by_code(code).comment_only`. `get_manual_fix_instructions(rule_code)` → already delegated to GuidanceService; GuidanceService can key off the same registry (or YAML keyed by code/symbol).
  - **violation_bridge:** `_is_comment_only_rule(rule_code)` → use the same container (injected or global registry).
  - **governance_comments:** `RULE_NAME_MAP` and any `_EXCELSIOR_RULE_NAMES` → replaced by `registry.by_code` / `registry.by_symbol` for display names.

So: **one DTO, one container, one logical place** (domain interface + infrastructure load from YAML/code). All other files **use** that container instead of redefining lists/sets/dicts.

---

## 3. Why wasn’t “check + fix in the Rule” done before? And finishing the refactor

**Why check stayed in “checkers” and fix in “Rule”**

- **Faster/simpler at the time:** Pylint already had a working checker model (visit_*, add_message). Moving all that logic into new “Rule” classes would have meant either (1) rewriting every checker as a Rule subclass with a `check(module_node)` that duplicates the astroid traversal, or (2) keeping the checker and having it call into a Rule. Option (1) was a large refactor; option (2) would have required the checker to hold a reference to the Rule and call `rule.check(node)` per node, which wasn’t done. So the path taken was: leave detection in the existing Pylint checkers; add **Rule** classes that only do **fix** and have **check** as a no-op (violations come from Pylint). That minimized change and got “fix” behind a unified Rule interface.
- **Result:** “Check” lives in use_cases/checks/* (Pylint checkers); “fix” lives in domain/rules/*. So the **behavior** of a rule is split: “whether it fires” is in one place, “what to do when it fires” in another. That’s why it feels like “rules are the core but their handling is spread everywhere.”

**What we should do**

- **Unify in the Rule:** For each Excelsior rule, the goal is one place that defines both:
  - **check(node)** — returns `list[Violation]`
  - **fix(violation)** — returns `Optional[TransformationPlan]` (or list of same)

- **Two ways to get there**
  1. **Checkers delegate to Rule.check:**
     Checker stays as the Pylint hook (it has to register with Pylint and call `add_message`). But the **logic** of “is this a violation?” moves into the Rule. So the checker’s `visit_*` becomes thin: get the corresponding Rule instance, call `violations = rule.check(module_node)` (or pass current node), and for each violation call `self.add_message(rule.symbol, node=..., args=...)`. So “behavior” lives in Rule; checker is a thin adapter.
  2. **Remove checkers and drive detection from Rule definitions:**
     Pylint would need a single “orchestrator” checker that (1) has the list of Rules, (2) visits the tree once (or per node type), (3) calls each Rule’s `check(module_node)` (or node-scoped API), (4) translates Violations to `add_message`. That’s a bigger change but gives “one place per rule: the Rule class.”

- **Recommendation:** Start with (1): keep Pylint checkers as the registration layer, but **move the detection logic** from checker into Rule. So each Rule implements `check(module_node) -> list[Violation]` with the same logic that currently lives in the checker. Checkers become thin: “for each Rule, run rule.check(module), then add_message for each violation.” That unifies “what this rule means” in the Rule class; we can later consider (2) if we want to drop multiple checker classes entirely.

- **Fix side:** We already have Rule.fix() returning TransformationPlan. Gateway should accept only plans (see §1). So the only cleanup is ensuring **all** fix paths go through plans and that the use case only collects plans.

---

## 4. Codifying so it doesn’t happen again

**Principles to codify**

1. **rule_registry.yaml is the single source of truth for rule metadata**
   Everything that can be static (codes, symbols, display names, message templates, fixable, comment_only, manual_instructions, proactive_guidance) lives in `rule_registry.yaml`. One loader builds the in-memory registry. No parallel lists, sets, or dicts in adapters, checkers, or governance_comments.

2. **One Rule, one place**
   For each Excelsior rule, a single Rule class owns both **check** (detection) and **fix** (resolution). Checkers remain as **thin wrappers** that delegate to `Rule.check()` and map Violations to Pylint `add_message()`.

3. **Fixes are always plans**
   The fix pipeline and the gateway speak only in `TransformationPlan`. No raw `CSTTransformer` at the use-case/gateway boundary.

**Ways to enforce**

- **.cursorrules / project rules:** “Rule metadata: single source is rule_registry.yaml. All static strings, bools, and formatting for rules live there. Adding a rule = add/update YAML first, then wire in code. Do not add parallel lists (fixable, comment_only, display names) in Python; load from registry.” “Checkers are thin: they delegate detection to Rule.check(). Do not add substantial ‘is this a violation?’ logic in a checker; move it into the Rule.”
- **Docs:** “Rule authoring: New rule = one entry in rule_registry.yaml + one Rule class (check + fix). Load metadata from registry; do not duplicate codes/symbols elsewhere.”
- **Lint/script:** See §5 for mechanical checks that detect drift early.

---

## 5. Detecting this kind of degradation early

The current technical debt came from a **series of small decisions** that accumulated: keep checkers fat and Rule.check() a no-op for speed; then add metadata (fixable, comment_only, display names) as requirements morphed; each addition went into “the obvious place” (adapter, bridge, governance_comments) instead of a single source. By the time the pattern was visible, the refactor had become large. This section is about **how to spot the same kind of degradation early** so we can correct course before it gets that far.

**What “degradation” looks like here**

- **Concept scatter:** The same concept (e.g. “rule W9010” or “comment-only rules”) is defined or used in multiple unrelated files for the same purpose. One place is the canonical source; the rest are drift.
- **Tactical shortcuts that become structure:** A decision like “keep checker logic where it is, make Rule.check() a no-op” is fine as a **temporary** tradeoff. It becomes degradation when we never revisit it and then add **more** features (fixable list, comment_only set, display names) in other files instead of extending the canonical place.
- **“Where do I add X?” has multiple answers:** If adding “is W9010 fixable?” can reasonably go in the adapter, the bridge, or a constants file, the design has already drifted. There should be **one** place (rule_registry.yaml + loader).

**Signals that degradation is starting again**

1. **Same identifier in 2+ places:** A rule code (e.g. `"W9010"`) or symbol (`"clean-arch-god-file"`) appears in more than one file with the same role (e.g. “list of fixable rules” in adapter and “list of comment-only” in bridge). After consolidation, the only allowed occurrences are: (a) rule_registry.yaml, (b) the single loader, (c) code that **reads** from the registry (e.g. `registry.get_by_code("W9010")`). Any new hard-coded list/set/dict of rule codes outside YAML + loader is a signal.
2. **New “list of rules” in a new place:** Someone adds “we need X for rules” and introduces a new dict/set/list in an adapter, checker, or service instead of adding a field to the YAML and loading it. That’s the “tacking on” pattern.
3. **Fat checker, no-op Rule:** If a checker contains non-trivial “is this a violation?” logic and the corresponding Rule.check() returns `[]`, we’ve repeated the original tradeoff. The intended state is: checker is thin, Rule.check() holds the logic.
4. **Registry completeness:** Every rule code that appears in checkers or adapters (e.g. in a loop or a conditional) should have an entry in rule_registry.yaml. If we add a rule code in code but not in YAML, that’s drift.

**Concrete detection mechanisms**

1. **Single-source invariant (script or CI)**
   - **Rule:** Rule codes and symbols (e.g. `W9\d{3}`, `clean-arch-*`) may appear in: (1) `rule_registry.yaml`, (2) the single registry loader, (3) code that only **reads** from the registry (e.g. `registry.get_by_code(...)`).
   - **Check:** Grep (or AST scan) for string literals matching rule codes/symbols. Allowlist: `rule_registry.yaml`, the loader module, and optionally test fixtures. Fail or warn if the same code/symbol appears in another file as part of a **definition** (e.g. inside a list/set/dict literal that is clearly “list of fixable rules”).
   - **Outcome:** Prevents “one more list” from being added in the adapter or bridge. Run in CI or pre-commit.

2. **Registry-completeness check**
   - **Rule:** Every Excelsior rule code used in the codebase (checkers, adapters, bridge) must have an entry in rule_registry.yaml.
   - **Check:** Extract rule codes from the YAML (e.g. from `excelsior.*` keys). Extract rule codes from Python (e.g. strings in checkers/adapters that look like W9xxx or clean-arch-*). If code references a rule code that has no YAML entry, fail. If YAML has an entry that nothing references, warn (optional).
   - **Outcome:** “Add a rule” has one obvious first step: add to YAML. New rule code in code without YAML → caught immediately.

3. **Scatter metric (optional, periodic)**
   - **Rule:** The number of files that **define** (not just read) rule-related metadata should stay at 1 (the YAML file; the loader is “definition” of the in-memory shape).
   - **Check:** Count files that contain both (a) a rule-code-like string and (b) a structure that looks like a definition (e.g. list/set/dict of such strings). After consolidation, that count should be 0 in Python (only YAML + loader). Run weekly or per release; if the count increases, investigate.
   - **Outcome:** Early warning that “we’re defining the same thing in another file again.”

4. **Decision log / ADR for tradeoffs**
   - **Rule:** When we make a deliberate tradeoff that defers work (e.g. “keep checker fat for now, add Rule.check() later”), record it in a short ADR or decision log with a follow-up or “tech debt” item.
   - **Check:** Periodic review (e.g. retro or quarterly): “We said we’d do X later; did we?” If we keep deferring and adding features elsewhere, that’s a signal.
   - **Outcome:** Makes deferred refactors visible so they don’t become permanent structure.

5. **PR checklist: “Rule Registry First”**
   - For any PR that adds or touches rule codes/symbols/fixable/comment_only/display names:
     - [ ] New or changed rule metadata is in `rule_registry.yaml` (not only in Python).
     - [ ] No new parallel list/set/dict of rule codes in adapter, checker, bridge, or governance_comments.
     - [ ] If adding checker logic that decides “is this a violation?”, is the same logic (or delegation to Rule.check()) in the Rule class?
   - **Outcome:** Human gate that reinforces “YAML first, load everywhere; thin checker.”

**Codifying the discipline (summary)**

- **Document the invariant:** “Rule metadata lives in rule_registry.yaml. The loader is the only place that builds the in-memory registry from that file. All consumers read from the registry. No duplicate definitions in Python.”
- **Document the intended shape:** “Checkers are thin: they call Rule.check(module_node) and map Violations to add_message(). Detection logic lives in Rule.check().”
- **Automate what we can:** Single-source script + registry-completeness check in CI. Scatter metric or PR checklist for the rest.
- **Review deferred decisions:** Use a decision log or ADR so “we’ll do it later” doesn’t silently become “forever.”

That way we don’t rely only on “someone noticing” the refactor got big; we have **signals and checks** that fire when the same pattern starts again.

---

**Summary**

- **rule_registry.yaml:** Everything that can be (static strings, bools, formatting) lives there. One loader; all code loads from the registry. Add/change a rule = edit YAML first.
- **Checkers:** Remain as thin wrappers that delegate to Rule.check(); detection lives in the Rule.
- **Plans only:** Gateway and use case speak only TransformationPlan.
- **Degradation detection:** Single-source invariant + registry-completeness in CI; scatter metric or PR checklist; decision log for “later” tradeoffs. Catch “same concept in multiple places” and “fat checker + no-op Rule” before the refactor grows large.

If you want, next step can be a **concrete implementation plan** (e.g. Phase 1: YAML schema + loader + wire one consumer; Phase 2: migrate all metadata into YAML and remove parallel definitions; Phase 3: gateway plans-only; Phase 4: move checker logic into Rule.check()), or we can refine any of the above first.
