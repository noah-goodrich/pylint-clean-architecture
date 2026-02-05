# Architectural Entropy: Detecting and Preventing Scatter and Drift

This document generalizes beyond Excelsior’s “rules” to **any** concept (rules, cars, recipes, people, config, feature flags, etc.) that can scatter across the codebase with redefinitions, conflicts, and drift. It describes how to **detect** and **prevent** this kind of architectural entropy even when the entropy takes forms we haven’t fully anticipated and appears at different layers.

---

## 1. What is architectural entropy?

**Entropy** here means: a **concept** that should have one clear definition or one canonical source is instead **spread across multiple places**, with redefinitions, possible conflicts, and no single place to add or change it.

- **Rules:** Rule codes, symbols, fixable/comment_only, display names in checkers, adapters, bridge, governance_comments, YAML — “where do I add W9010?” has many answers.
- **Cars:** Car types, attributes (make, model, trim), validation rules in API layer, domain entities, config, UI labels — “where do I add a new trim?” in 4 files.
- **Recipes:** Recipe tags, dietary flags, units, categories in backend, frontend, DB schema, API docs — “where do I add gluten-free?” scattered.
- **People:** Person attributes, roles, permissions in auth service, user service, UI, config — same role name defined in 3 places.
- **Config / feature flags:** Same setting or flag redefined in env, YAML, code defaults, tests — “where do I change the timeout?” is ambiguous.

The **pattern** is always the same: **one concept, many definition sites**. No single source of truth. “Add or change X” has multiple plausible answers. Tactical “add it here for now” decisions accumulate until the refactor is large.

**Layers:** Entropy can appear in domain (entities redefined), use cases (flows duplicated), infrastructure (config in many places), interface (copy/strings scattered), or across layers (same concept defined in domain and infra and UI). The principle is the same regardless of layer.

---

## 2. The invariant that holds for any concept

**For every concept C that has a schema or a set of instances:**

1. **Single source of truth:** There is **one** canonical place where C is defined or loaded from (one file, one module, one table, one registry). All consumers **read** from that place; they do not redefine C or extend it in place.
2. **Add/change in one place:** “Add a new instance of C” or “change an attribute of C” has **one** obvious answer: edit the canonical source (or the single loader that builds from it).
3. **No parallel definitions:** No second list, dict, set, or config block elsewhere that duplicates or extends the same concept “for convenience.”

This invariant is **concept-agnostic**. It applies to rules, cars, recipes, people, config, feature flags, API contracts, UI copy — anything that has a schema or a set of instances and that could otherwise be redefined in multiple places.

---

## 3. Why entropy happens (and keeps happening)

- **Tactical shortcuts:** “We need X; the fastest place to add it is here.” So we add it in the adapter, then later in the bridge, then in governance — each time “here” is a different file.
- **Requirements morph:** New needs (fixable, comment_only, display name) appear; each gets a new list or dict in “the obvious place” instead of extending the canonical source.
- **Layers and ownership:** Domain has “Car”; API has “car response”; UI has “car labels.” Without a rule, each layer defines its own shape and they drift.
- **Deferred refactors:** “We’ll keep the old structure for now and add the new thing here.” “For now” becomes permanent; then we add more “here”s.
- **No mechanical check:** Nothing fails when a second definition site appears, so the pattern repeats until someone notices the refactor has become large.

So: **entropy is predictable**. The same forces (speed, convenience, layer boundaries, deferred work) will push any concept toward scatter unless we explicitly prevent it.

---

## 4. How to solve for it in the future (general)

### 4.1 Design: one canonical source per concept

- **Identify concepts that have a schema or a set of instances.** Examples: rules, car types, recipe tags, person roles, feature flags, API error codes, UI copy keys.
- **For each concept, designate one canonical source.** That might be:
  - A file (YAML, JSON, TOML) loaded at startup — e.g. `rule_registry.yaml`, `car_definitions.yaml`, `recipe_tags.yaml`.
  - A single module or package that “owns” the concept — e.g. `domain.car` with `Car` entity and `CarRegistry` built from one load path.
  - A single table or service in a DB — e.g. “car_types” table; all consumers read from it.
- **All consumers only read.** Adapters, services, UI, and other layers **load** or **query** the canonical source; they do not maintain a parallel list, dict, or config of the same concept.
- **Add/change starts at the canonical source.** Document it: “To add a new rule, edit rule_registry.yaml.” “To add a new car type, edit car_definitions.yaml (or the Car admin).” So “where do I add X?” has one answer.

This is the **registry pattern** (or “single source of truth”) applied to any concept. It doesn’t matter whether the concept is “rules” or “cars”; the structure is the same: one place that defines or loads the concept, everyone else reads.

### 4.2 Detection: catch entropy before it gets large

We may not know in advance **which** concept will scatter or **what** form the scatter will take. So detection should be **concept-agnostic** where possible, and **configurable** where we do know the concept.

**A. Concept-agnostic signals (any project)**

1. **Same identifier in multiple “definition” contexts.**
   If the same string or symbol (e.g. `"W9010"`, `"sedan"`, `"gluten-free"`) appears in more than one file as part of a **definition** (e.g. inside a list, set, dict, enum, or config block that clearly “defines” instances of something), that’s a scatter signal.
   **Mechanism:** Grep or AST scan for literals that look like “instance IDs” (e.g. `W9\d{3}`, known enum-like names). Allowlist the canonical source and the loader. Flag any other file that contains the same literal in a definition-like context (e.g. inside `{`, `[`, or key-value block).
   **Parameterize:** Allow the team to register “concepts” (e.g. rule codes, car type IDs, recipe tags) and allowlists (files that may define them). Run in CI; fail or warn when a concept appears in a non-allowlisted file in a definition context.

2. **Definition-count growth.**
   For a given concept, count how many files contain something that **looks like** a definition of that concept (e.g. a dict keyed by concept IDs, a list of concept constants).
   **Mechanism:** After you consolidate to one canonical source, that count should be 1 (or 2 if you have YAML + loader). Track the count over time (e.g. weekly or per release). If it increases, investigate.
   **Parameterize:** Define “concept” by a pattern (e.g. dict keys matching `W9xxx`, or files containing “car_type” and a collection literal). No need to know every possible concept; start with the ones you care about and add more as you find new scatter.

3. **“Where do I add X?” has multiple answers.**
   If the team or an AI can reasonably add “a new rule” or “a new car type” in 2+ places (e.g. adapter and bridge and governance), the design has already drifted.
   **Mechanism:** Document the canonical source for each concept. In PR reviews and onboarding, ask: “Where would you add a new [rule | car type | recipe tag]?” If the answer isn’t unique, treat that as a process failure and fix the design or the docs.

4. **Deferred decisions that never get revisited.**
   “We’ll add it here for now” and “we’ll unify later” become permanent if not tracked.
   **Mechanism:** Decision log or ADR: when we make a deliberate shortcut (e.g. “keep checker fat, Rule.check() no-op for now”), record it with a follow-up or tech-debt item. Periodically review: “We said we’d do X later; did we?” If we keep deferring and adding features elsewhere, that’s entropy.

**B. Concept-specific checks (when we know the concept)**

- **Registry completeness:** Every **instance** of the concept that appears in code (e.g. every rule code, every car type ID) must exist in the canonical source. Script: extract instances from code (e.g. all `"W9xxx"` strings); extract instances from the canonical source (e.g. keys in rule_registry.yaml). If code references an instance not in the canonical source, fail.
- **Schema consistency:** If the concept has a schema (e.g. Rule has code, symbol, fixable, comment_only), ensure the canonical source defines that schema and all consumers read it. No consumer should redefine the schema (e.g. its own list of “fixable” rule codes).

**C. Layers**

- Entropy can appear in **domain** (e.g. Car entity redefined in two modules), **use cases** (e.g. “validate recipe” logic in 3 places), **infrastructure** (e.g. config in env, YAML, and code), or **interface** (e.g. labels in 5 components).
- The **same invariant** applies per layer or cross-layer: for concept C, one canonical source; everyone else reads.
- Detection can be **per-concept** (“rule codes only in rule_registry.yaml”) or **per-layer** (“all config in this layer comes from config.yaml”). What matters is: we know what “one place” means for each concept we care about, and we check that we don’t create a second place.

### 4.3 Process and discipline

- **Document the invariant:** “For concept C, the single source of truth is X. All consumers read from X. Do not add parallel definitions elsewhere.” Put it in .cursorrules, ARCHITECTURE, or a per-concept README.
- **Onboarding / PR checklist:** “Adding a new [rule | car type | recipe tag | …]? Add it to [canonical source]. Do not add to [other places].”
- **Automate what we can:** Single-source check + registry-completeness (or schema-consistency) in CI. Scatter metric or definition-count over time.
- **Review deferred decisions:** Use a decision log or ADR so “we’ll do it later” doesn’t silently become “forever.”

---

## 5. Anticipating the unanticipated

We won’t always know **in advance** which concept will scatter or what it will look like. So:

1. **Start with the concepts you already know.** Rules, config, feature flags, API contracts — designate a canonical source and a simple check (e.g. “rule codes only in rule_registry.yaml”).
2. **Use generic signals.** “Same identifier in multiple definition contexts” and “definition-count growth” don’t require knowing the concept name; they only require a way to recognize “this looks like a definition” (e.g. dict/list/enum of string literals). Run a broad check (e.g. “any string literal that looks like an ID appearing in 2+ files in a collection”) and investigate; that can surface new concepts that are starting to scatter.
3. **Make the “one place” pattern the default.** When introducing a **new** concept (cars, recipes, people), default to: “we will have one canonical source (file, module, or service) and all consumers will read from it.” Don’t wait for scatter to appear; design for single source from the start.
4. **When you find new scatter, add it to the list.** If you discover that “recipe tags” or “person roles” have drifted, add them to your concept list and to your allowlist/checks. Over time, the set of concepts you monitor grows, and the chance of catching entropy early increases.

---

## 6. Summary

- **Architectural entropy** = one concept, many definition sites; redefinitions, conflicts, “where do I add X?” has multiple answers. It can affect rules, cars, recipes, people, config, feature flags, etc., at any layer.
- **Invariant:** For every concept C, one canonical source; all consumers read; add/change in one place; no parallel definitions.
- **Solve:** Design one canonical source per concept (registry pattern); detect scatter with concept-agnostic signals (same identifier in multiple definition contexts, definition-count growth, “where do I add X?” multiple answers, deferred decisions never revisited) and optional concept-specific checks (registry completeness, schema consistency); document the invariant and automate checks in CI; review deferred decisions.
- **Unanticipated forms:** Start with known concepts; use generic signals to spot new scatter; default to “one canonical source” for new concepts; when you find new scatter, add it to the monitored set.

That way we don’t depend on having foreseen every kind of entropy; we depend on a **reusable pattern** (single source per concept) and **generic plus configurable detection** so we can catch and correct scatter early, whatever the concept or layer.

---

## 7. Excelsior rules (this project)

For **Excelsior rule metadata** (codes, symbols, display names, message templates, fixable, comment_only), the **canonical source** is:

- **`src/clean_architecture_linter/infrastructure/resources/rule_registry.yaml`**

One entry per rule, keyed by code (e.g. `excelsior.W9010`). GuidanceService resolves by code or symbol so callers can use either; no duplicate symbol-keyed entries in the YAML. All consumers (adapters, violation bridge, governance comments, checkers) read from the registry. Adding a rule = add/update YAML first, then wire in code. See `.cursorrules` and `docs/RULE_CONSOLIDATION_PROPOSAL.md` for the consolidation design.

---

## 7. Excelsior rules (this project)

Rule metadata single source: `src/clean_architecture_linter/infrastructure/resources/rule_registry.yaml`. One entry per rule by code; GuidanceService resolves by code or symbol. See `.cursorrules` and `docs/RULE_CONSOLIDATION_PROPOSAL.md`.
