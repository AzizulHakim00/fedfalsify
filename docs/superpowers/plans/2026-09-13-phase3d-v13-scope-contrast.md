# FedFalsify Phase-3D / v13 Scope-Contrast Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the zero-new-seed Phase-3D deterministic fixture proof for FedFalsify v13/SCSV-SCC, with source-protected scope-contrast certification, four prespecified model branches, atomic per-fixture×model×fold Drive persistence, exact resume, reproducible CSV/JSON/PKL/joblib outputs, and a one-cell Colab wrapper.

**Architecture:** Reuse the frozen v10 grammar and existing sufficient-statistic/rank infrastructure, but introduce a Phase-3D-only deterministic fixture layer and scope-contrast test whose candidate regressor is zero outside a frozen role and equals the source basis inside it. The v13 branch freezes role identities on Discovery, jointly certifies shared/source-shift structure on Selector, and confirms localized terms on Probe. Persistence treats `fixture × model × outer_fold` as the only atomic work unit.

**Tech Stack:** Python 3, numpy, scipy, pandas, joblib, pytest, GitHub Actions, Google Colab/Drive.

**Spec:** `docs/superpowers/specs/2026-09-13-phase3d-v13-scope-contrast-design.md`

## Global Constraints

- No access to scientific seeds `29300`, `29301–29310`, or `11001–11999`; Phase-3D fixtures are deterministic and seedless.
- Initial `OUTER_FOLDS = (0,)`; runner must accept more fold IDs later without changing persistence semantics.
- Exactly four methods: `v11-frozen`, `v12-frozen`, `scope-contrast-only`, `v13-full`.
- Exactly eight fixtures from the approved spec.
- Discovery/Selector/Probe separation is retained; Probe remains independent.
- Valid source-linked scope shifts are tested on aggregated role+outside contrast, never by requiring rank expansion within one role client.
- Every completed unit is atomically written and hashed before it enters the checkpoint index.
- Complete verified units skip on resume; incomplete or hash-corrupt units alone rerun.
- Outputs include JSON units, checkpoint CSV, result/diagnostic CSVs, PKL, joblib, integrity JSON, manifest, ZIP.
- No Phase-3C threshold tuning.

---

### Task 1: Deterministic fixtures and scope-contrast primitive

**Files:**
- Create: `tests/test_phase3d_scope_contrast.py`
- Create: `src/fedfalsify/phase3d_fixtures.py`
- Create: `src/fedfalsify/scope_contrast_v13.py`

**Interfaces:**
- `build_phase3d_fixtures() -> tuple[Phase3DFixture, ...]`
- `scope_contrast_test(clients, catalog, shared_terms, source_term, role_indices) -> ScopeContrastResult`
- `discover_scope_contrast(fixture, discovery_clients, catalog, shared_terms, localized_term, source_term) -> FrozenScopeHypothesis | ScopeContrastRejection`

- [ ] Write failing tests proving eight deterministic fixtures, exact true scopes, no scientific-seed parameters, and that the quadratic role+outside contrast increases rank while the role-client-only design remains collinear.
- [ ] Run `pytest -q tests/test_phase3d_scope_contrast.py` and record RED caused by missing Phase-3D modules.
- [ ] Implement deterministic fixed-grid fixtures and the minimal aggregated scope-contrast sufficient-statistic test.
- [ ] Run focused tests to GREEN.
- [ ] Commit.

### Task 2: v13 fixture methods and structural admissibility

**Files:**
- Extend: `tests/test_phase3d_scope_contrast.py`
- Create: `src/fedfalsify/scsv_v13.py`

**Interfaces:**
- `run_phase3d_model(fixture, model_name, outer_fold=0) -> Phase3DModelResult`
- result exposes `shared_structure`, `accepted_localized`, `localized_scopes`, `exact_shared`, `exact_localized`, `exact_scope`, `exact_structure`, `diagnostics`.

- [ ] Add failing tests for primary quadratic exact recovery, linear/trig/interaction/weak-source/dual exact scope, and zero localized acceptance on both null fixtures.
- [ ] Verify RED.
- [ ] Implement four prespecified branches. Frozen comparator branches call existing v11/v12 where compatible; Phase-3D structural proof branches use deterministic source-protected shared families and scope-contrast certification. `scope-contrast-only` isolates localization; `v13-full` jointly retains shared sources plus accepted shifts and independently verifies them on Probe.
- [ ] Verify all Phase-3D structural tests GREEN.
- [ ] Commit.

### Task 3: Atomic persistence, resume, and reproducible artifacts

**Files:**
- Create: `tests/test_phase3d_runner.py`
- Create: `src/fedfalsify/phase3d_runner.py`

**Interfaces:**
- `run_phase3d(output_dir: Path, outer_folds=(0,), live=True) -> dict`
- `verify_unit(path, expected_key, config_sha256) -> dict | None`
- `atomic_json_write(path, payload) -> None`

- [ ] Add failing tests for atomic unit persistence, complete-unit skip, corrupt-unit rerun, checkpoint row count, CSV/PKL/joblib equivalence, manifest verification, and seed-firewall strings absent from work-unit generation.
- [ ] Verify RED.
- [ ] Implement unit-level temp+fsync+`os.replace`, SHA validation, deterministic aggregation, CSV/PKL/joblib writes, integrity/manifest/ZIP creation, and organized live shell progress.
- [ ] Verify focused runner tests GREEN.
- [ ] Commit.

### Task 4: One-cell Colab wrapper and CI gate

**Files:**
- Create: `tests/test_phase3d_colab.py`
- Create: `tools/build_phase3d_colab.py`
- Create: `colab/FedFalsify_Phase3D_V13_Scope_Contrast_OneCell.ipynb`
- Create: `.github/workflows/phase3d_v13_fixture_ci.yml`

**Interfaces:**
- `tools/build_phase3d_colab.py` generates one code cell only.
- Wrapper mounts Drive first, clones an exact implementation commit, creates a clean environment, runs focused + full tests, then calls `run_phase3d()` against the fixed Drive root.

- [ ] Add failing tests that the builder generates exactly one code cell, Drive mount precedes clone/execution, no scientific seed block appears in executable experiment configuration, output root is fixed, and the wrapper calls the resume-safe runner rather than inlining scientific algorithms.
- [ ] Verify RED.
- [ ] Implement builder/workflow and generate notebook.
- [ ] Run focused tests, then `pytest -q` full suite in CI.
- [ ] Regenerate notebook after pinning the verified implementation commit; confirm source pin and config hash.
- [ ] Commit final wrapper seal.

### Final verification

- [ ] Confirm frozen v11/v12 scientific files have not changed from Phase-3C execution source except new Phase-3D imports/modules.
- [ ] Confirm all Phase-3D tests pass and complete repository suite passes.
- [ ] Confirm deterministic Phase-3D runner does not invoke any scientific seed.
- [ ] Confirm generated notebook has exactly one code cell.
- [ ] Confirm resume semantics by rerunning a fixture directory with at least one valid unit and one intentionally corrupt unit in tests.
- [ ] Produce user-downloadable `.ipynb` and `.py` copies from the verified one-cell wrapper.
