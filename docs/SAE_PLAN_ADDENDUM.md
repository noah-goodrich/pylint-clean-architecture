# SAE Plan Addendum: Tests, Coverage, Deprecation, and Final Green State

Merge or append this into the main SAE implementation plan.

---

## Test requirements and coverage

- **Coverage policy**: Project enforces `--cov-fail-under=80` (pyproject.toml). New and modified SAE code must be covered so the overall suite stays at or above 80%; no new modules or use cases left uncovered.

- **Unit tests (new or extended)**:
  - **Domain**
    - **RecommendedStrategy / SAE entities**: Test TypedDict shape and any factory/validation used by the gateway.
    - **GraphIngestor** (e.g. `tests/unit/domain/services/test_graph_ingestor.py`): Test `ingest_project` with mocked `GraphGatewayProtocol` and `AstroidProtocol`; assert `add_artifact` / `add_symbol` / `add_violation` calls with correct layer (via mocked LayerRegistry or inline heuristic), and symbol derivation from node or from handover DTO (code, symbol_name, message).
    - **SAETranslator** (`tests/unit/domain/services/test_sae_translator.py`): Test `translate_blueprint_to_contexts` for at least two patterns (e.g. Adapter, Strategy); assert output list length and required fields in each TransformationContext.
  - **Infrastructure**
    - **KuzuGraphGateway** (`tests/unit/infrastructure/gateways/test_kuzu_gateway.py`): Test `query_recommended_strategies` return type and shape (list of RecommendedStrategy with pattern, rationale, affected_files, violations, score); use an in-memory or temp-dir DB so tests are deterministic, or mock at protocol boundary in use case tests.
    - **Bootstrapper**: Test that bootstrap (or the wrapper calling InitializeGraphUseCase) runs without error with a temp CSV dir and does not require real package resources if paths are injectable.
  - **Use cases**
    - **InitializeGraphUseCase**: Test execute with mocked GraphGatewayProtocol; assert add_strategy / violation merge calls and step parsing from CSV.
    - **GenerateBlueprintUseCase**: Test execute with mocked storage (handover JSON), graph_gateway (return predefined list[RecommendedStrategy]), and ingestor (verify ingest_project called with expected root and violation list); assert BLUEPRINT.md content written via storage and return value.
  - **CLI / DI**
    - **CLIDependencies**: Extend `_make_mock_deps()` in `tests/unit/interface/test_cli.py` to include `graph_gateway`, `graph_ingestor`, `sae_bootstrapper` so existing CLI tests do not break. Add a test that `init` invokes `sae_bootstrapper.bootstrap()` and that `blueprint` builds GenerateBlueprintUseCase with the new deps (e.g. mock execute and assert call).
    - **Container**: Test that container registers and returns graph_gateway, graph_ingestor, sae_bootstrapper and that get_graph_gateway / get_graph_ingestor / get_sae_bootstrapper return the same instances when used by init and blueprint.

- **Integration / functional**:
  - Add at least one functional or slow-marked test: run `excelsior init` then `excelsior check` then `excelsior blueprint` in a temp project and assert BLUEPRINT.md exists under .excelsior and contains expected sections (or "No systemic …" when no violations). This guards the full flow.

- **Final green bar**: All tests must pass (`PYTHONPATH=src pytest -m "not slow"` and optionally `pytest -m slow`), coverage ≥ 80%, and no linter/mypy regressions.

---

## Deprecation and removal

- **Functionally deprecated (remove or replace)**  
  - **Direct bootstrap import in CLI**: If any code path still does `from ... bootstrapper import bootstrap_sae` and calls `bootstrap_sae()` inside the CLI, remove it. The only supported path is `deps.sae_bootstrapper.bootstrap()`.  
  - **GenerateBlueprintUseCase without graph/ingestor**: The current use case that only reads handover + strategy_tree YAML and never calls the graph or ingestor is superseded by the new flow (ingest → query → synthesize). Remove or refactor the old "YAML-only" branch so the single code path uses graph_gateway and ingestor; avoid leaving two parallel implementations.  
  - **Hard-coded strategy_tree path**: Replace `open("src/excelsior_architect/resources/strategy_tree.yaml")` with resource loading (e.g. `importlib.resources`) or storage so the same code works from an installed package. Remove any duplicate or legacy path logic.

- **Not deprecated but verify**  
  - **DesignPatternRecommendation** (entities): Kept for health-report pattern recommendations; distinct from graph `RecommendedStrategy`. No removal.  
  - **strategy_tree.yaml vs design_patterns_tree.csv**: Both are used (YAML for blueprint synthesis steps, CSV for graph hydration). Keep both; ensure bootstrapper uses CSV only for init and use case uses YAML only where needed.

- **Cleanup before "done"**  
  - Ensure no dead code: any function or branch that was only used by the old blueprint path (e.g. YAML-only cluster analysis with no graph) is removed or inlined.  
  - Run Ruff, Mypy, and Excelsior on the full codebase and fix any new issues introduced by SAE changes so the project remains "fully green" for lint and type-check.

---

## Final green state (success criteria)

The project is **done** for this SAE work when:

1. **Full flow runs**: `excelsior init` (scaffold + SAE bootstrap) → `excelsior check` (audit + handover) → `excelsior blueprint` (ingest, query graph, write BLUEPRINT.md) completes without errors for a representative project (e.g. excelsior-architect itself or a small bait project).
2. **All tests pass**: `PYTHONPATH=src pytest` (default: `-m 'not slow'`) passes with `--cov-fail-under=80` and no coverage-impact regressions. Optional: `pytest -m slow` passes for any slow tests.
3. **Lint and types**: Ruff, Pylint (if used), and Mypy pass on the full codebase with no new errors.
4. **No broken or deprecated paths**: CLIDependencies and container provide graph_gateway, graph_ingestor, sae_bootstrapper; init and blueprint use only injected dependencies; no remaining direct bootstrap_sae import in the CLI; single, graph-based blueprint flow (no leftover YAML-only path).
5. **Documentation**: README or COMMANDS.md (if present) updated to describe `init` (SAE hydration), `blueprint`, and optional `fix --strategy auto` so the "fully green" state is reproducible by others.
