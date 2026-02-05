# Excelsior: Proactive Generation Guidance

When editing or generating Python in this repo, follow the **proactive guidance** so code passes Excelsior (and ruff, import-linter, mypy, pylint) with fewer violations.

## Where to Look

- **Summary:** [docs/GENERATION_GUIDANCE.md](docs/GENERATION_GUIDANCE.md) — architecture, types, style, and a short "before you submit" checklist.
- **Full registry:** [docs/excelsior_prompts.yaml](docs/excelsior_prompts.yaml) — every rule has `proactive_guidance` (how to write code that complies) and `manual_instructions` (how to fix a violation). Key format: `{linter}.{rule_code}` (e.g. `mypy.type-arg`, `excelsior.W9006`).

## Rules of Thumb

1. **Architecture:** Dependencies point inward. Domain has no I/O. Use constructor injection and Protocols. No Law of Demeter (one dot: `friend.do_thing()`, not `friend.thing.do_action()`). Domain entities immutable; no `Any`.
2. **Types:** Annotate every function (params + return) and non-obvious variables. Use full generics: `dict[str, int]`, `list[str]`, `Optional[str]`. Match protocol/override signatures exactly.
3. **Style (Ruff):** No mutable defaults; no unused args (remove or `_arg`); keep functions small and argument count low.
4. **Contracts:** Respect `[tool.importlinter]`; do not import from forbidden layers.

When fixing a **specific violation** after `excelsior check`, use the registry: look up `{linter}.{code}` and apply `manual_instructions` (or the handover JSON’s `manual_instructions`, which should align with the registry).
