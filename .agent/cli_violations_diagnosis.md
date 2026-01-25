# Why CLI Violations Weren’t Caught: Diagnosis

## 1. What We *Do* Catch (and Why It Persisted Anyway)

### W9001 (clean-arch-dependency): Interface → Infrastructure

- **Rule**: `DependencyChecker` bans Interface from importing Infrastructure. Interface may only import UseCase and Domain.
- **cli.py**: Mapped as `Interface` (`layer_map`: `"clean_architecture_linter.cli" = "Interface"`). It imports:
  - `clean_architecture_linter.infrastructure.adapters.*` (Infrastructure)
  - `clean_architecture_linter.infrastructure.gateways.libcst_fixer_gateway` (Infrastructure)
  - `clean_architecture_linter.infrastructure.services.scaffolder` (Infrastructure)
  - `clean_architecture_linter.di.container` (Infrastructure)
- **Result**: W9001 **does** fire for these imports. Pre-flight reports ~10 W9001; several come from cli (and other Interface modules like checker/reporter).
- **Why it persisted**: We **chose to tolerate** these violations:
  - **Import-Linter** `ignore_imports` explicitly allows `cli → infrastructure.adapters.linter_adapters` and `cli → di.container`. That encodes “we allow cli to pull these.”
  - We never fixed the underlying design (thin controller + use cases). The rules flagged it; we didn’t remediate.

**Conclusion**: The dependency rule *did* catch Interface→Infrastructure. We didn’t treat it as a hard stop.

---

## 2. What We *Don’t* Catch (Gaps)

### 2.1 God-File (W9010) Only Looks at **Classes**

- **Rule**: `ModuleStructureChecker` triggers “God File” when:
  - **Mixed layers**: more than one layer among **classes** in the file, or
  - **Heavy components**: more than one **class** in UseCase/Infrastructure (excluding Protocol/DTO).
- **Implementation**: It uses `visit_classdef` / `leave_module`. Only **classes** are counted. Module-level functions are ignored.
- **cli.py**: Has **no classes** — only module-level functions (`main`, `check_command`, `_gather_linter_results`, etc.). So `heavy_component_count` and `current_layer_types` stay empty → **W9010 never fires**.
- **Gap**: We detect “god **file**” (too many heavy **classes**), but not “god **module**” (too many module-level functions / too much orchestration in one module). A front controller implemented as a bag of functions is invisible to W9010.

**Conclusion**: The current god-file rule **cannot** catch cli’s “god module” structure. We’d need a separate “god module” / “too many top-level functions” rule.

### 2.2 Import-Linter Contract Excludes `cli`

- **Contract** (`pyproject.toml`): `layers = [checker, reporter, checks, domain]`, `containers = [clean_architecture_linter]`. **`cli` is not a layer.**
- **Effect**: Import-Linter only validates imports **between** those four layers. It does **not** validate `cli`’s imports. The `ignore_imports` entries for `cli → …` are effectively unused for that contract (or apply only if cli were ever folded into a layer).
- **Gap**: We don’t enforce layer boundaries on `cli` via Import-Linter. All layer enforcement on cli comes from the **Pylint** DependencyChecker (W9001).

**Conclusion**: Import-Linter was never applied to cli. We rely only on Pylint for cli’s dependency violations.

### 2.3 No “Thin Controller” / “Orchestration Bloat” Rule

- We have no rule that says “Interface modules (e.g. CLI) must not contain X% of project logic” or “must delegate to use cases.”
- **Gap**: Even if we enforced “Interface may only import UseCase + Domain,” we wouldn’t enforce “Interface must be a thin router.” Orchestration, formatting, persistence, and adapter wiring can all live in one module and still satisfy W9001 **if** we switched to Protocol-based injection (Interface → UseCase only). The **god-module** and **thin-controller** problems are separate from dependency direction.

**Conclusion**: Missing rule: “thin controller” / “orchestration scope” for Interface modules.

### 2.4 Root-Logic (W9011) Doesn’t Apply to `cli`

- **Rule**: Flags “logic in project root” (single-segment path). Allowed exceptions: `setup.py`, `conftest.py`, `manage.py`, etc.
- **cli.py**: Lives under `src/clean_architecture_linter/cli.py` (multiple path segments). So W9011 does not apply.
- **Conclusion**: No gap here; this rule simply doesn’t target cli.

---

## 3. Summary Table

| Rule / Tool            | Could catch cli?        | Why it didn’t / did |
|------------------------|-------------------------|---------------------|
| W9001 (dependency)     | Yes                     | **Did** catch. We tolerated it; import-linter ignores encode allowed exceptions. |
| W9010 (god-file)       | No                      | **Only classes.** cli has no classes → never triggers. |
| W9011 (root logic)     | No                      | cli not in root → rule doesn’t apply. |
| Import-Linter          | No                      | **cli not a layer** → not validated. |
| “God module”           | Would help              | **Rule doesn’t exist.** |
| “Thin controller”      | Would help              | **Rule doesn’t exist.** |

---

## 4. Why This Was “Allowed” to Persist

1. **W9001 fires** on Interface→Infrastructure, including cli. We accepted those violations and added import-linter ignores for two specific edges.
2. **W9010** can’t see cli at all, because it only considers classes.
3. **Import-Linter** doesn’t model cli as a layer, so it never enforced cli’s imports.
4. We have **no rules** for “god module” (too many functions) or “thin controller” (orchestration bloat). So those design issues were never enforced.

---

## 5. Rules That *Don’t* Exist But *Should* (To Prevent This)

1. **God-module / “too many top-level functions”**  
   - Flag modules that have:
     - No (or very few) classes, and  
     - Many top-level functions (e.g. &gt; N), or high “orchestration” density (calls to many different domains).  
   - Would have made cli’s structure visible even without classes.

2. **Thin-controller / “orchestration scope” for Interface**  
   - E.g. “Interface modules may not define more than X logic statements / use-case calls.”  
   - Would push routing and wiring into use cases / services and keep Interface thin.

3. **Include `cli` (and similar entrypoints) in Import-Linter**  
   - Add `cli` as a layer (e.g. “CLI” or “Entrypoint”) and enforce its allowed imports.  
   - Then we could remove or narrow import-linter `ignore_imports` and enforce those boundaries explicitly.

4. **Optional: “Interface must not instantiate Infrastructure”**  
   - Stricter than “no import”: even with Protocol-based UseCases, Interface must not `new` adapters/gateways.  
   - Would have forced DI/container usage earlier and made cli’s current design impossible.

---

## 6. Tests Added (Mirroring “Should Have Caught”)

- **`tests/unit/checks/test_dependencies.py::test_interface_imports_infrastructure_flagged`**: Interface → Infrastructure import → we **do** flag W9001. (Existing rule that should catch cli-like imports.)
- **`tests/unit/checks/test_structure.py::test_god_module_functions_only_not_flagged`**: Module with only functions, **no** classes → we **do not** flag W9010. (Documents current gap.)
- **`tests/functional/test_cli_violations_diagnosis.py::test_interface_imports_infrastructure_flagged`**: Temporary project with Interface + Infrastructure `layer_map`; Interface module imports Infrastructure → pylint reports W9001.
- **`tests/functional/test_cli_violations_diagnosis.py::test_god_module_functions_only_not_flagged`**: Same-style module (functions only) → we **do not** flag clean-arch-god-file.

**Future**: When a “god module” rule exists, add `test_god_module_functions_only_flagged` and flip the structure test to expect a violation.
