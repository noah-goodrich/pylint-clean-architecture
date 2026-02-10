# SAE Strategic Architecture Engine – Implementation Plan

This document is the single source of truth for the Strategic Architecture Engine (SAE) work. It merges implementation phases with testing requirements, deprecation/removal, and the final green-state criteria.

---

## Current state (summary)

- **Protocols**: `GraphGatewayProtocol` and `SAEBootstrapperProtocol` exist; `query_recommended_strategies` returns `list[RecommendedStrategy]` but `RecommendedStrategy` is not defined (only in TYPE_CHECKING import from entities).
- **Kuzu gateway**: Implemented; returns `List[Dict]`; needs to return `list[RecommendedStrategy]`. Bootstrapper uses wrong CSV filenames (uppercase vs actual lowercase in `resources/data/`).
- **GraphIngestor**: Uses concrete gateways; missing `Path` import; hard-coded layer heuristic; assumes `Violation.node_name` (does not exist—use `node`).
- **GenerateBlueprintUseCase**: Only accepts `storage`; does not use graph or ingestor. Must be refactored to single path: ingest → query graph → synthesize.
- **CLI/DI**: `init` and `blueprint` reference `deps.sae_bootstrapper`, `deps.graph_gateway`, `deps.graph_ingestor` but these are not in `CLIDependencies` or container—runtime `AttributeError`.
- **No SAETranslator**; no `TransformationContext` for blueprint-driven surgery.

---

## Implementation phases

### Phase 1: Types and protocols

- Add **RecommendedStrategy** TypedDict: `pattern`, `rationale`, `affected_files`, `violations`, `score` (in `domain/sae_entities.py` or `domain/entities.py`). Use it in `GraphGatewayProtocol.query_recommended_strategies()`.
- Protocol: `add_dependency(symbol_name, dep_name)` (2 args); gateway may keep optional `dep_type` as implementation detail.

### Phase 2: Knowledge graph gateway

- **Kuzu gateway**: `query_recommended_strategies` returns `list[RecommendedStrategy]`; map rows to TypedDict; normalize list columns.
- **Bootstrapper**: Use filenames matching `resources/data/`: `design_patterns_tree.csv`, `excelsior_violations.csv`, `mypy_violations.csv`, `ruff_violations.csv`. Use package resources or config for base path where possible.
- **InitializeGraphUseCase**: Accept `GraphGatewayProtocol`; parse `Implementation` into list of steps (split comma, strip). Fix violation merge to use gateway API if needed (no direct `conn.execute` for Violation if protocol hides it—else keep in concrete gateway).

### Phase 3: Metrics-aware ingestor

- **GraphIngestor**: Depend on `GraphGatewayProtocol` and `AstroidProtocol`; add `LayerRegistry` and use `resolve_layer("", file_path, None)` for layer; add `from pathlib import Path`; derive symbol from `Violation.node` (e.g. `node.name`) or accept handover DTO `(code, symbol_name, message, path)`.

### Phase 4: Blueprint use case and SAE Translator

- **GenerateBlueprintUseCase**: Add `graph_gateway`, `ingestor`, `telemetry`; flow: load handover → build violation list for ingest → run ingestor → query strategies → synthesize blueprints → write BLUEPRINT.md. Load strategy_tree via `importlib.resources` or storage.
- **SAETranslator** (new `domain/services/sae_translator.py`): `TransformationContext` type; `translate_blueprint_to_contexts(diagnosis) -> list[TransformationContext]`; domain-only, no LibCST/Kùzu.

### Phase 5: CLI and DI

- **CLIDependencies**: Add `graph_gateway`, `graph_ingestor`, `sae_bootstrapper`.
- **Container**: Register `KuzuGraphGateway`, `GraphIngestor`, bootstrapper wrapper; add `get_graph_gateway()`, `get_graph_ingestor()`, `get_sae_bootstrapper()`.
- **__main__.py**: Pass new deps into `CLIDependencies`. Remove any direct `from ... bootstrapper import bootstrap_sae` in CLI.

### Phase 6: Verify and tests

- Verify command unchanged unless adding graph-based entropy score later.
- See **Test requirements and coverage** below.

---

## Test requirements and coverage

- **Coverage**: Keep `--cov-fail-under=80`. All new/updated SAE code must be covered.
- **Unit tests**:
  - **Domain**: RecommendedStrategy/SAE entities; GraphIngestor (mocked protocol, layer, symbol); SAETranslator (translate_blueprint_to_contexts, ≥2 patterns).
  - **Infrastructure**: KuzuGraphGateway (query_recommended_strategies shape, temp DB or mock); bootstrapper (injectable paths).
  - **Use cases**: InitializeGraphUseCase (mocked gateway); GenerateBlueprintUseCase (mocked storage, graph, ingestor; assert BLUEPRINT.md).
  - **CLI/DI**: Extend `_make_mock_deps()` with graph_gateway, graph_ingestor, sae_bootstrapper; test init calls `sae_bootstrapper.bootstrap()`, blueprint builds use case; container get_* for SAE.
- **Integration**: At least one functional/slow test: init → check → blueprint in temp project; assert BLUEPRINT.md under `.excelsior`.
- **Green bar**: `PYTHONPATH=src pytest -m "not slow"` (and optional `pytest -m slow`), coverage ≥ 80%, no new Ruff/Mypy/Excelsior regressions.

---

## Deprecation and removal

- **Remove**: (1) Any direct `from ... bootstrapper import bootstrap_sae` in CLI—use only `deps.sae_bootstrapper.bootstrap()`. (2) GenerateBlueprintUseCase YAML-only branch—single path using graph_gateway and ingestor. (3) Hard-coded `open("src/.../strategy_tree.yaml")`—use `importlib.resources` or storage.
- **Keep**: DesignPatternRecommendation; strategy_tree.yaml and design_patterns_tree.csv (different roles).
- **Cleanup**: Remove dead code from old blueprint path; run full Ruff, Mypy, Excelsior and fix regressions.

---

## Final green state (success criteria)

Done when:

1. **Full flow**: `excelsior init` → `excelsior check` → `excelsior blueprint` runs without errors (e.g. on excelsior-architect or bait project).
2. **Tests**: `PYTHONPATH=src pytest` with `--cov-fail-under=80`; optional `pytest -m slow`.
3. **Lint and types**: Ruff, Pylint, Mypy pass.
4. **No broken/deprecated paths**: CLIDependencies and container provide graph_gateway, graph_ingestor, sae_bootstrapper; single graph-based blueprint flow; no direct bootstrap_sae in CLI.
5. **Docs**: README or COMMANDS.md updated for init (SAE hydration), blueprint, optional fix --strategy auto.

---

## File checklist

| Phase | File | Action |
|-------|------|--------|
| 1 | domain/sae_entities.py | Add RecommendedStrategy TypedDict |
| 1 | domain/protocols.py | Import RecommendedStrategy from sae_entities |
| 2 | infrastructure/gateways/kuzu_gateway.py | Return list[RecommendedStrategy]; fix add_strategy steps type |
| 2 | infrastructure/bootstrapper.py | Correct CSV filenames; optional resource path |
| 2 | use_cases/initialize_graph.py | GraphGatewayProtocol; parse Implementation steps |
| 3 | domain/services/graph_ingestor.py | Protocols, LayerRegistry, Path, symbol from node/DTO |
| 4 | domain/services/sae_translator.py | New; TransformationContext + translate_blueprint_to_contexts |
| 4 | use_cases/generate_blueprint.py | graph_gateway, ingestor, telemetry; ingest→query→synthesize |
| 5 | interface/cli.py | Add SAE deps to CLIDependencies; remove direct bootstrap_sae if present |
| 5 | infrastructure/di/container.py | Register gateway, ingestor, bootstrapper; get_* |
| 5 | __main__.py | Pass SAE deps into CLIDependencies |
| 6 | tests/unit/... | New tests per Test requirements; extend test_cli, test_container |
| 6 | docs/COMMANDS.md or README | Update for init, blueprint, fix --strategy auto |

See also: [SAE_PLAN_ADDENDUM.md](SAE_PLAN_ADDENDUM.md) for the original detailed addendum text.
