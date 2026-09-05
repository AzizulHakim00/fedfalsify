# Phase-3B Scientific Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement FedFalsify v12 / SCSV-NCSC as a tested, mechanism-isolated Phase-3B package with SCR, NCEE, strict Discovery -> Selector -> Probe firewalls, an engineering-only seed-29300 harness, and a reproducible one-cell Google Colab runner that persists all artifacts to Google Drive.

**Architecture:** Preserve frozen v11 unchanged. Reuse the sealed Phase-3A sufficient-statistic and deterministic-rank primitives, add one shared partial nested-F engine and one multiplicity engine, then build SCR and NCEE as independent modules before composing four matched branches (`v11`, `scr-only`, `ncee-only`, `scsv-ncsc`). The engineering harness is outcome-neutral: seed 29300 is used only after all deterministic tests pass, and no performance threshold may be tuned from that smoke run.

**Tech Stack:** Python 3.10+, NumPy, SciPy, pandas, joblib, pytest, Google Colab/Drive, GitHub-pinned source.

**Spec:** `docs/superpowers/specs/2026-09-06-phase3b-scientific-implementation-design.md`

## Global Constraints

- Frozen comparator files must remain byte-for-byte unchanged: `src/fedfalsify/scsv_v11.py`, `src/fedfalsify/scsv_v11_study.py`, `src/fedfalsify/scsv_v10_benchmarks.py`.
- Reuse `src/fedfalsify/sufficient_stats.py` and `src/fedfalsify/linear_algebra.py`; do not alter their scientific behavior in Phase-3B.
- Shared capacity = 6 total terms including intercept; maximum 5 non-intercept shared terms.
- Localized operational capacity = 2 deviations; final total structure capacity = 10 including intercept.
- `alpha_shared = 0.05` with Holm; `q_role = 0.10` with BH; `alpha_dev = 0.05` with Holm.
- Outside-role non-degradation = `SSE_FULL <= SSE_REDUCED + 1e-10`.
- No tuned rank threshold, ridge rescue, positive pooled-delta tolerance, PQCR/DR rescue, globality repair, HEAR, consensus rescue, grammar expansion, or benchmark-truth use in inference.
- Probe may not change candidate, source, role, outside role, sign, shared structure, or hypothesis family.
- Phase-3 engineering may use only seed `29300`; predecessor parity may use `29001`; `29101--29105`, `29201--29205`, `29301--29310`, and `11001+` are blocked.
- `29300` is an integration/numerical smoke, not a performance-development set. It may not be used to change alpha/q/support floors/capacities/rank/safety rules.
- No Phase-3 development runner is created in this plan. `29301--29310` remain unusable until a later separately frozen protocol.
- All scientific modules must be deterministic for fixed input data and seed.
- CSV/JSON/TXT are archival truth; PKL/joblib are convenience state formats only.
- Google Drive output root for the engineering smoke is `/content/drive/MyDrive/FedFalsify_Q1/SCSV_NCSC_PHASE3_ENGINEERING/`.

---

## File map

### New scientific modules

- `src/fedfalsify/nested_tests.py` — fixed-scope partial nested-F inference from sufficient statistics.
- `src/fedfalsify/multiple_testing.py` — deterministic Holm and BH correction.
- `src/fedfalsify/shared_recertification.py` — SCR candidate family and Selector certification.
- `src/fedfalsify/role_localization_v12.py` — NCEE Discovery client tests and frozen role construction.
- `src/fedfalsify/localized_certification.py` — Selector screening, Probe Holm certification, ambiguity/capacity filters.
- `src/fedfalsify/legacy_v11_adapter.py` — SCR-only adapter that applies frozen v11 localized rules to an externally supplied shared core without changing v11.
- `src/fedfalsify/scsv_v12.py` — four-branch orchestration and final refit.
- `src/fedfalsify/phase3_engineering_runner.py` — engineering study, checkpoint/resume, summaries, Drive artifacts.

### New tests

- `tests/test_nested_tests.py`
- `tests/test_multiple_testing.py`
- `tests/test_shared_recertification.py`
- `tests/test_role_localization_v12.py`
- `tests/test_localized_certification.py`
- `tests/test_legacy_v11_adapter.py`
- `tests/test_scsv_v12.py`
- `tests/test_phase3_seed_firewall.py`
- `tests/test_phase3_engineering_runner.py`
- `tests/test_phase3_colab_notebook.py`

### Governance / runner files

- `research/FROZEN_PHASE3_ENGINEERING_PROTOCOL.md` — exact six-condition engineering matrix and immutable statistical constants; explicitly does not authorize fresh development.
- `tools/build_phase3_engineering_colab.py` — generates the one-cell notebook after code/protocol sealing and embeds the exact scientific source commit and protocol SHA256.
- `colab/FedFalsify_Phase3_NCSC_OneCell.ipynb` — one executable cell only.
- `.github/workflows/phase3b_engineering_ci.yml` — frozen-comparator guard + deterministic Phase-3B tests; does not run seed 29300 in CI.

### Modified files

- `pyproject.toml` — bump package version to `0.7.0`, add SciPy core dependency, add study extras `pandas` and `joblib`, and add `fedfalsify-phase3-engineering` CLI.

---

### Task 1: Dependency and Frozen-Boundary Gate

**Files:**
- Modify: `pyproject.toml`
- Create: `tests/test_phase3_seed_firewall.py`
- Create: `.github/workflows/phase3b_engineering_ci.yml`

**Interfaces:**
- Consumes: frozen Phase-3A branch state at `78d0ab7ca7afb1edfa4725a45dfd20ce2db39659`.
- Produces: package `0.7.0`, SciPy availability, study extras, explicit seed validator used by the engineering runner, and CI guards that prevent comparator drift.

- [ ] **Step 1: Write failing seed-firewall tests**

```python
import pytest

from fedfalsify.phase3_engineering_runner import validate_phase3_engineering_seed


def test_phase3_engineering_seed_allows_only_29300():
    validate_phase3_engineering_seed(29300)
    for seed in (29001, 29101, 29201, 29301, 29310, 11001, 11999):
        with pytest.raises(ValueError):
            validate_phase3_engineering_seed(seed)
```

- [ ] **Step 2: Run the test to confirm RED**

Run:

```bash
pytest -q tests/test_phase3_seed_firewall.py
```

Expected: import/function failure because the Phase-3 engineering runner does not exist yet.

- [ ] **Step 3: Update dependency metadata without adding scientific behavior**

Set:

```toml
[project]
version = "0.7.0"
dependencies = ["numpy>=1.26,<3", "scipy>=1.11,<2"]

[project.optional-dependencies]
dev = ["pytest>=8,<9"]
study = ["pandas>=2.1,<4", "joblib>=1.3,<2"]
sr = ["pysr>=1.5.10,<2"]

[project.scripts]
fedfalsify-phase3-engineering = "fedfalsify.phase3_engineering_runner:main"
```

Create only the minimal seed-validator shell in `phase3_engineering_runner.py` at this task:

```python
ENGINEERING_SEED = 29300


def validate_phase3_engineering_seed(seed: int) -> None:
    if int(seed) != ENGINEERING_SEED:
        raise ValueError("Phase-3 engineering permits seed 29300 only")
```

- [ ] **Step 4: Add CI comparator-integrity guard**

The workflow must run:

```bash
git diff --exit-code 78d0ab7ca7afb1edfa4725a45dfd20ce2db39659 -- \
  src/fedfalsify/scsv_v11.py \
  src/fedfalsify/scsv_v11_study.py \
  src/fedfalsify/scsv_v10_benchmarks.py
pytest -q tests/test_scsv_v11.py
```

and later Phase-3B test files as they are added. The workflow must never execute `29300` automatically.

- [ ] **Step 5: Run focused tests GREEN**

```bash
python -m pip install -e ".[dev,study]"
pytest -q tests/test_phase3_seed_firewall.py tests/test_scsv_v11.py
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml src/fedfalsify/phase3_engineering_runner.py tests/test_phase3_seed_firewall.py .github/workflows/phase3b_engineering_ci.yml
git commit -m "chore: establish Phase-3B dependency and seed firewall"
```

---

### Task 2: Partial Nested-F Statistical Primitive

**Files:**
- Create: `src/fedfalsify/nested_tests.py`
- Create: `tests/test_nested_tests.py`

**Interfaces:**
- Consumes: `SufficientStatsPacket`, `aggregate_packets`, `fit_from_sufficient_stats`, `RankPolicy`.
- Produces:
  - `NestedFResult`
  - `partial_nested_f(packet, reduced_terms, full_terms, *, candidate_term) -> NestedFResult`
  - `aggregate_scope(packets, indices) -> SufficientStatsPacket`

`NestedFResult` fields:

```python
@dataclass(frozen=True)
class NestedFResult:
    admissible: bool
    reason: str
    reduced_terms: tuple[str, ...]
    full_terms: tuple[str, ...]
    n: int
    reduced_rank: int
    full_rank: int
    residual_df: int
    reduced_sse: float
    full_sse: float
    raw_gain: float
    f_statistic: float | None
    p_value: float | None
    candidate_coefficient: float | None
    candidate_sign: int
```

- [ ] **Step 1: Write analytic and equivalence tests**

Tests must cover:

```python
import numpy as np

from fedfalsify.basis import TermCatalog
from fedfalsify.nested_tests import partial_nested_f
from fedfalsify.sufficient_stats import packet_from_dataset


def test_nested_f_matches_direct_ols_and_scipy_reference(simple_dataset, simple_catalog):
    packet = packet_from_dataset(simple_dataset, simple_catalog, ("1", "x1"))
    out = partial_nested_f(packet, ("1",), ("1", "x1"), candidate_term="x1")
    assert out.admissible
    assert out.full_rank == out.reduced_rank + 1
    assert out.residual_df > 0
    assert 0.0 <= out.p_value <= 1.0


def test_nested_f_abstains_on_exact_collinearity(collinear_packet):
    out = partial_nested_f(
        collinear_packet,
        ("1", "x1"),
        ("1", "x1", "x1_copy"),
        candidate_term="x1_copy",
    )
    assert not out.admissible
    assert out.reason == "STRUCTURAL-RANK-AMBIGUOUS"
    assert out.p_value is None
```

Add a centralized-row reference using `np.linalg.lstsq` and `scipy.stats.f.sf`, and assert coefficients/SSE/F/p match the packet calculation within strict floating-point tolerances.

- [ ] **Step 2: Run RED**

```bash
pytest -q tests/test_nested_tests.py
```

Expected: module missing.

- [ ] **Step 3: Implement the minimal engine**

Rules:

```python
if tuple(full_terms[:-1]) != tuple(reduced_terms) or candidate_term not in full_terms:
    # do not rely on positional form; validate set nesting instead

if full_fit.rank != reduced_fit.rank + 1:
    return abstention("STRUCTURAL-RANK-AMBIGUOUS")
if full_fit.residual_df <= 0:
    return abstention("INSUFFICIENT-RESIDUAL-DF")

gain = max(reduced_fit.sse - full_fit.sse, 0.0)
f_value = gain / (full_fit.sse / full_fit.residual_df)
p_value = scipy.stats.f.sf(f_value, 1, full_fit.residual_df)
```

Candidate coefficient is read by term name from the FULL fit. Sign convention: `+1` above `1e-12`, `-1` below `-1e-12`, else `0`.

- [ ] **Step 4: Add multi-client additivity test**

Split one deterministic centralized fixture into at least three client packets, aggregate, and assert equality of rank/SSE/F/p against the centralized fixture.

- [ ] **Step 5: Run GREEN**

```bash
pytest -q tests/test_sufficient_stats.py tests/test_linear_algebra.py tests/test_nested_tests.py
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/fedfalsify/nested_tests.py tests/test_nested_tests.py
git commit -m "feat: add Phase-3 nested structural test engine"
```

---

### Task 3: Deterministic Holm and BH Correction

**Files:**
- Create: `src/fedfalsify/multiple_testing.py`
- Create: `tests/test_multiple_testing.py`

**Interfaces:**
- Produces:
  - `MultiplicityResult`
  - `holm_adjust(names, p_values, alpha=0.05) -> MultiplicityResult`
  - `bh_adjust(names, p_values, q=0.10) -> MultiplicityResult`

```python
@dataclass(frozen=True)
class MultiplicityResult:
    names: tuple[str, ...]
    raw_values: tuple[float, ...]
    adjusted_values: tuple[float, ...]
    rejected: tuple[str, ...]
```

- [ ] **Step 1: Write known-vector tests**

```python
from fedfalsify.multiple_testing import bh_adjust, holm_adjust


def test_holm_known_vector_and_original_order():
    out = holm_adjust(("a", "b", "c", "d"), (0.01, 0.04, 0.03, 0.20), alpha=0.05)
    assert out.names == ("a", "b", "c", "d")
    assert all(0.0 <= p <= 1.0 for p in out.adjusted_values)


def test_bh_ties_are_deterministic():
    first = bh_adjust(("a", "b", "c"), (0.02, 0.02, 0.50), q=0.10)
    second = bh_adjust(("a", "b", "c"), (0.02, 0.02, 0.50), q=0.10)
    assert first == second
```

Also compare adjusted values to hand-calculated Holm/BH references.

- [ ] **Step 2: Run RED**

```bash
pytest -q tests/test_multiple_testing.py
```

- [ ] **Step 3: Implement exact deterministic procedures**

Validate finite p-values in `[0,1]`, unique hypothesis names, and fixed `alpha/q`. Sorting uses `(raw_p, original_index)`; returned arrays remain original order.

- [ ] **Step 4: Add subset-safety regression test**

Verify a later deterministic filter can only remove names from `rejected`, never add them.

- [ ] **Step 5: Run GREEN and commit**

```bash
pytest -q tests/test_multiple_testing.py
git add src/fedfalsify/multiple_testing.py tests/test_multiple_testing.py
git commit -m "feat: add deterministic Phase-3 multiplicity control"
```

---

### Task 4: Shared-Core Re-certification (SCR)

**Files:**
- Create: `src/fedfalsify/shared_recertification.py`
- Create: `tests/test_shared_recertification.py`

**Interfaces:**
- Consumes: frozen v6 anchor output, Discovery/Selector packets, catalog, `partial_nested_f`, `holm_adjust`.
- Produces:
  - `SharedCandidateDiagnostic`
  - `SharedRecertificationResult`
  - `nominate_shared_family(anchor, catalog) -> tuple[str, ...]`
  - `certify_shared_core(anchor, selector_packets, catalog) -> SharedRecertificationResult`

`SharedRecertificationResult` must expose candidate family, accepted shared terms, Holm raw/adjusted evidence, rank abstentions, capacity truncation flag, and removed-by-capacity terms.

- [ ] **Step 1: Write candidate-family tests**

Use a deterministic/mock anchor and verify:

```python
family = nominate_shared_family(anchor, catalog)
assert family[0] == "1"
assert all(catalog.get(term).kind != "exception" for term in family)
assert len(family) == len(set(family))
```

- [ ] **Step 2: Write independent Selector certification tests**

Construct synthetic packets with one required shared term, one null ordinary term, and one collinear term. Verify the required term can survive, null term can fail, collinear term abstains, and no Discovery outcome beyond the frozen family is read.

- [ ] **Step 3: Write exact capacity test**

Create six strongly supported non-intercept terms and verify operational result contains exactly intercept + five, selected by smallest Holm-adjusted p-value then canonical catalog order.

- [ ] **Step 4: Run RED**

```bash
pytest -q tests/test_shared_recertification.py
```

- [ ] **Step 5: Implement SCR without candidate expansion**

For each non-intercept candidate `t`, FULL is the complete identifiable joint ordinary family and REDUCED removes only `t`. Apply Holm across all valid per-term p-values; rank-ambiguous terms receive an abstention diagnostic and are never silently dropped from the multiplicity ledger.

- [ ] **Step 6: Run GREEN and commit**

```bash
pytest -q tests/test_nested_tests.py tests/test_multiple_testing.py tests/test_shared_recertification.py
git add src/fedfalsify/shared_recertification.py tests/test_shared_recertification.py
git commit -m "feat: implement shared-core recertification"
```

---

### Task 5: NCEE Discovery Role Construction

**Files:**
- Create: `src/fedfalsify/role_localization_v12.py`
- Create: `tests/test_role_localization_v12.py`

**Interfaces:**
- Consumes: frozen shared term set, Discovery client packets, catalog, candidate/source metadata, `partial_nested_f`, `bh_adjust`.
- Produces:
  - `NCEEClientEvidence`
  - `FrozenLocalizedHypothesis`
  - `discover_localized_role(...) -> FrozenLocalizedHypothesis | RoleRejection`

Required frozen hypothesis fields:

```python
@dataclass(frozen=True)
class FrozenLocalizedHypothesis:
    term: str
    source_term: str
    role_indices: tuple[int, ...]
    outside_indices: tuple[int, ...]
    role_client_ids: tuple[str, ...]
    outside_client_ids: tuple[str, ...]
    discovery_sign: int
    client_evidence: tuple[NCEEClientEvidence, ...]
```

- [ ] **Step 1: Write eligibility tests**

Verify a client is ineligible if active support `<10`, FULL rank does not increase by one, or residual df `<5`.

- [ ] **Step 2: Write BH role test**

Construct client packets with strong candidate evidence on a known minority subset and null evidence outside. Verify BH uses only eligible client p-values and the resulting role is exactly the supported subset.

- [ ] **Step 3: Write role-admissibility tests**

Reject:

- empty supported role -> `EFFECT-ROLE-NOT-LOCALIZED`;
- all/global or more-than-half support -> `GLOBAL-SCOPE-AMBIGUOUS`;
- mixed nonzero signs -> `SCOPE-SIGN-AMBIGUOUS`;
- missing source provenance -> `SOURCE-PROVENANCE-MISSING`.

- [ ] **Step 4: Run RED, implement, run GREEN**

```bash
pytest -q tests/test_role_localization_v12.py
```

Implementation must not accept Selector or Probe packets as arguments. That API boundary is itself part of the firewall.

- [ ] **Step 5: Commit**

```bash
git add src/fedfalsify/role_localization_v12.py tests/test_role_localization_v12.py
git commit -m "feat: implement noise-calibrated discovery roles"
```

---

### Task 6: Selector Screening and Untouched-Probe Certification

**Files:**
- Create: `src/fedfalsify/localized_certification.py`
- Create: `tests/test_localized_certification.py`

**Interfaces:**
- Consumes: tuple of frozen localized hypotheses, fixed shared term set, Selector packets, Probe packets, catalog.
- Produces:
  - `SelectorLocalizedDiagnostic`
  - `ProbeLocalizedDiagnostic`
  - `LocalizedCertificationResult`
  - `screen_on_selector(...)`
  - `certify_on_probe(...)`

- [ ] **Step 1: Write Selector safety tests**

Verify Selector can only remove hypotheses and rejects on sign mismatch, nonpositive median role gain, outside-role degradation greater than `1e-10`, rank ambiguity, or structural nesting failure.

- [ ] **Step 2: Write Probe-family immutability test**

Snapshot the entire tuple of candidate/source/role/outside/sign before calling Probe. Assert returned result retains exactly those hypothesis identities and does not create or alter any role.

- [ ] **Step 3: Write Holm whole-family test**

Create at least three frozen hypotheses with known Probe p-values. Verify Holm is computed across the complete frozen family reaching Probe, then safety filters only remove Holm rejections.

- [ ] **Step 4: Write outside-role tolerance test**

Test the exact boundary:

```python
assert outside_safe(reduced_sse=1.0, full_sse=1.0 + 1e-10)
assert not outside_safe(reduced_sse=1.0, full_sse=1.0 + 1.0001e-10)
```

- [ ] **Step 5: Write ambiguity/capacity tests**

Verify:

- multiple accepted deviations sharing one source -> all linked localized terms rejected as source ambiguous;
- more than two operational localized candidates -> newly proposed localized set rejected, not ranked by benchmark outcome.

- [ ] **Step 6: Run RED, implement, run GREEN**

```bash
pytest -q tests/test_localized_certification.py
```

- [ ] **Step 7: Commit**

```bash
git add src/fedfalsify/localized_certification.py tests/test_localized_certification.py
git commit -m "feat: add selector and probe localized certification"
```

---

### Task 7: Frozen-v11 Localized Adapter for SCR-Only Ablation

**Files:**
- Create: `src/fedfalsify/legacy_v11_adapter.py`
- Create: `tests/test_legacy_v11_adapter.py`

**Interfaces:**
- Consumes: externally supplied shared/core `CandidateEquation`, frozen v6 bank/candidate provenance, datasets/catalog/seed.
- Produces: localized acceptance using the exact v11 scientific constants and decision rules without modifying `scsv_v11.py`.

- [ ] **Step 1: Write parity test on the original v11 core**

Run frozen v11 on deterministic seed-29001 fixtures, extract its ordinary core, then run the adapter with that same core. Assert exact equality for:

- candidate deviation family;
- accepted deviations;
- role client IDs;
- rejection reasons;
- final localized set.

- [ ] **Step 2: Run RED**

```bash
pytest -q tests/test_legacy_v11_adapter.py
```

- [ ] **Step 3: Implement adapter by reusing frozen v11 helpers/constants**

Import and use frozen v11 logic (`_localize_effect_role`, `_effect_pair`, `_weak_heredity_pass`, `MIN_*`, capacity rules) rather than re-defining numeric thresholds. Do not call benchmark truth.

- [ ] **Step 4: Assert frozen-v11 source diff remains empty**

```bash
git diff --exit-code 78d0ab7ca7afb1edfa4725a45dfd20ce2db39659 -- \
  src/fedfalsify/scsv_v11.py \
  src/fedfalsify/scsv_v11_study.py \
  src/fedfalsify/scsv_v10_benchmarks.py
```

- [ ] **Step 5: Run GREEN and commit**

```bash
pytest -q tests/test_scsv_v11.py tests/test_legacy_v11_adapter.py
git add src/fedfalsify/legacy_v11_adapter.py tests/test_legacy_v11_adapter.py
git commit -m "feat: add frozen-v11 localized ablation adapter"
```

---

### Task 8: Compose v11, SCR-only, NCEE-only, and Full SCSV-NCSC

**Files:**
- Create: `src/fedfalsify/scsv_v12.py`
- Create: `tests/test_scsv_v12.py`

**Interfaces:**
- Produces:
  - `SCSVV12Output`
  - `run_scsv_v12_branches(datasets, catalog, *, seed, target_mse, min_repair_score=0.05) -> tuple[BranchOutput, ...]`

Four exact method IDs:

```python
PHASE3_METHODS = (
    "scsv-elrc-v11-full",
    "scr-only",
    "ncee-only",
    "scsv-ncsc",
)
```

- [ ] **Step 1: Write four-branch structure tests**

Assert one call returns exactly four outputs in fixed method order and that the v11 branch is produced directly by `scsv_elrc_v11_method`.

- [ ] **Step 2: Write ablation-isolation tests**

- SCR-only must use SCR shared structure and the frozen-v11 localized adapter.
- NCEE-only must use the predecessor v11 ordinary shared structure and NCEE.
- Full must use SCR + NCEE.
- None may alter v11 output.

- [ ] **Step 3: Write final-refit test**

After final structure freezes, reuse predecessor `_refit(..., include_validation=True)` to refit numerical coefficients. Assert refit cannot change accepted term identities.

- [ ] **Step 4: Write mechanism-ledger completeness test**

Every non-v11 branch must emit all prespecified shared/localized diagnostics even when no term is accepted.

- [ ] **Step 5: Run RED, implement, run GREEN**

```bash
pytest -q \
  tests/test_shared_recertification.py \
  tests/test_role_localization_v12.py \
  tests/test_localized_certification.py \
  tests/test_legacy_v11_adapter.py \
  tests/test_scsv_v12.py
```

- [ ] **Step 6: Commit**

```bash
git add src/fedfalsify/scsv_v12.py tests/test_scsv_v12.py
git commit -m "feat: compose FedFalsify v12 scientific branches"
```

---

### Task 9: Freeze the Engineering Protocol and Exact Six-Condition Matrix

**Files:**
- Create: `research/FROZEN_PHASE3_ENGINEERING_PROTOCOL.md`
- Extend: `tests/test_phase3_seed_firewall.py`
- Create: `tests/test_phase3_engineering_runner.py`

**Interfaces:**
- Engineering condition key = `(family, num_clients, balance_profile, role_profile, noise_ratio, seed)`.
- Exact engineering matrix uses seed `29300` only and reuses the predecessor six-smoke geometry with the new engineering namespace:

```python
ENGINEERING_CONDITIONS = (
    ("quadratic_role_v10", 4, "balanced", "single", 0.10, 29300),
    ("trig_role_v10", 4, "balanced", "single", 0.30, 29300),
    ("null_role_v10", 8, "balanced", "none", 0.10, 29300),
    ("anchor_contamination_null_v10", 8, "balanced", "none", 0.30, 29300),
    ("weak_source_role_v10", 8, "balanced", "quarter", 0.10, 29300),
    ("dual_role_v10", 8, "imbalanced", "quarter", 0.30, 29300),
)
```

This is integration coverage, not a development performance sample.

- [ ] **Step 1: Write protocol content before any 29300 execution**

Protocol must enumerate:

- exact six conditions above;
- four methods;
- all fixed statistical constants/capacities;
- seed firewall;
- checkpoint semantics;
- engineering decision definition;
- explicit statement: no scientific GO/NO-GO inference from 29300.

- [ ] **Step 2: Write matrix/firewall tests**

```python
def test_engineering_matrix_is_exact_and_seed_is_29300_only():
    assert len(ENGINEERING_CONDITIONS) == 6
    assert {row[-1] for row in ENGINEERING_CONDITIONS} == {29300}
```

Also assert no blocked namespace appears anywhere in the matrix.

- [ ] **Step 3: Define engineering decision only from integrity**

`phase3_engineering_decision.json` may contain only `PHASE3-ENGINEERING-PASS` or `PHASE3-ENGINEERING-FAIL`, determined by:

- all required tests passed before execution;
- six/6 condition groups complete;
- exactly four method rows per condition;
- zero duplicate method rows;
- zero integrity/firewall violations;
- all required artifacts written and hashable.

Exact recovery/NMSE/precision/recall must not be used in this engineering pass/fail decision.

- [ ] **Step 4: Run tests without running 29300**

```bash
pytest -q tests/test_phase3_seed_firewall.py tests/test_phase3_engineering_runner.py
```

- [ ] **Step 5: Commit the frozen protocol**

```bash
git add research/FROZEN_PHASE3_ENGINEERING_PROTOCOL.md tests/test_phase3_seed_firewall.py tests/test_phase3_engineering_runner.py
git commit -m "research: freeze Phase-3 engineering protocol"
```

After this commit, protocol scientific constants may not change in response to `29300` results.

---

### Task 10: Engineering Runner, Atomic Resume, Diagnostics, and Drive Artifacts

**Files:**
- Extend: `src/fedfalsify/phase3_engineering_runner.py`
- Extend: `tests/test_phase3_engineering_runner.py`

**Interfaces:**
- `run_engineering(output_dir: Path, *, seed: int = 29300, live: bool = True) -> dict`
- `load_checkpoint(path) -> list[dict]`
- `validate_checkpoint_groups(rows) -> tuple[list[dict], set[ConditionKey]]`
- `atomic_write_csv(df, path)`
- `save_reproducibility_artifacts(...)`

- [ ] **Step 1: Write atomic checkpoint/resume tests**

Create temporary checkpoint data with:

1. one complete four-method group;
2. one partial two-method group.

Verify resume keeps/skips only the complete group and removes/recomputes the partial group.

```python
assert completed_keys == {complete_condition_key}
assert all(row["condition_key"] != partial_condition_key for row in cleaned_rows)
```

- [ ] **Step 2: Write method-set and duplicate validation tests**

A complete group must contain exactly:

```python
{
    "scsv-elrc-v11-full",
    "scr-only",
    "ncee-only",
    "scsv-ncsc",
}
```

and exactly one row per method.

- [ ] **Step 3: Implement live stage/progress printing**

Use `print(..., flush=True)` and these exact stage labels:

```text
[STAGE 0/10] Protocol + seed firewall
[STAGE 1/10] Google Drive persistence
[STAGE 2/10] Exact source + dependency verification
[STAGE 3/10] Scientific test gate
[STAGE 4/10] Condition matrix + checkpoint validation
[STAGE 5/10] Phase-3 engineering smoke
[STAGE 6/10] Mechanism diagnostics
[STAGE 7/10] Ablation summaries
[STAGE 8/10] Reproducibility artifacts
[STAGE 9/10] Integrity manifest + ZIP
[STAGE 10/10] Engineering decision
```

During Stage 5 print only condition metadata/progress, elapsed time, and save status. Do not print comparative outcome metrics condition-by-condition.

- [ ] **Step 4: Implement archival outputs**

Required files in `output_dir`:

```text
FROZEN_PHASE3_ENGINEERING_PROTOCOL.md
phase3_engineering_checkpoint.csv
phase3_engineering_rows.csv
phase3_engineering_method_summary.csv
phase3_engineering_shared_diagnostics.csv
phase3_engineering_localized_diagnostics.csv
phase3_engineering_ablation_summary.csv
phase3_engineering_integrity.json
phase3_engineering_environment.json
phase3_engineering_decision.json
phase3_engineering_state.pkl
phase3_engineering_state.joblib
phase3_engineering_report.txt
phase3_engineering_sha256.txt
FedFalsify_PHASE3_NCSC_ENGINEERING_RESULTS.zip
```

CSV/JSON/TXT must be sufficient to reconstruct all reported summaries without loading PKL/joblib.

- [ ] **Step 5: Implement state persistence**

After every complete matched four-method condition:

1. update in-memory rows;
2. write checkpoint to `*.tmp` in the same directory;
3. `os.replace(tmp, final)`;
4. update convenience PKL and joblib state atomically;
5. print `[CHECKPOINT] condition X/6 saved`.

- [ ] **Step 6: Implement transparent summaries**

`phase3_engineering_method_summary.csv` and `phase3_engineering_ablation_summary.csv` are descriptive engineering-only summaries. Include exact recovery, term precision/recall, shared precision/recall, deviation precision/recall, NMSE, communication, and method-only runtime, but never use them for the engineering PASS decision.

- [ ] **Step 7: Implement SHA256 manifest and ZIP verification**

Hash every final artifact except the manifest itself, write sorted `sha256  filename` lines, create ZIP, reopen with `zipfile.ZipFile(...).testzip()`, then print the ZIP SHA256.

- [ ] **Step 8: Run tests without seed 29300**

Use monkeypatched/fake condition evaluator in unit tests. Do not execute scientific engineering data yet.

```bash
pytest -q tests/test_phase3_engineering_runner.py
```

- [ ] **Step 9: Commit**

```bash
git add src/fedfalsify/phase3_engineering_runner.py tests/test_phase3_engineering_runner.py
git commit -m "feat: add reproducible Phase-3 engineering runner"
```

---

### Task 11: Generate the Exact One-Cell Google Colab Notebook

**Files:**
- Create: `tools/build_phase3_engineering_colab.py`
- Create: `tests/test_phase3_colab_notebook.py`
- Create: `colab/FedFalsify_Phase3_NCSC_OneCell.ipynb`

**Interfaces:**
- Builder reads the current scientific-source commit with `git rev-parse HEAD` and computes SHA256 of `research/FROZEN_PHASE3_ENGINEERING_PROTOCOL.md`.
- Builder writes those values as literal constants into the notebook cell.
- Notebook contains exactly one executable code cell.

- [ ] **Step 1: Write notebook-structure tests**

```python
import json


def test_phase3_colab_has_exactly_one_code_cell():
    nb = json.loads(Path("colab/FedFalsify_Phase3_NCSC_OneCell.ipynb").read_text())
    code = [cell for cell in nb["cells"] if cell["cell_type"] == "code"]
    assert len(code) == 1
```

Also assert the single source contains:

- `drive.mount('/content/drive')` before package execution;
- `PINNED_SOURCE_COMMIT`;
- `EXPECTED_PROTOCOL_SHA256`;
- exact Drive output root;
- `pip install` against `git+https://github.com/AzizulHakim00/fedfalsify.git@<literal pinned commit>`;
- protocol download/hash verification;
- test gate;
- call to `fedfalsify.phase3_engineering_runner`;
- no embedded copies of SCR/NCEE scientific functions.

- [ ] **Step 2: Run RED**

```bash
pytest -q tests/test_phase3_colab_notebook.py
```

- [ ] **Step 3: Implement builder**

The builder must programmatically:

```python
source_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
protocol_bytes = Path("research/FROZEN_PHASE3_ENGINEERING_PROTOCOL.md").read_bytes()
protocol_sha = hashlib.sha256(protocol_bytes).hexdigest()
```

Then generate one cell whose execution order is:

1. import standard library;
2. mount Drive;
3. create output directory;
4. print pinned source/protocol/seed firewall;
5. download the protocol at the pinned commit and verify SHA256;
6. `pip install -q "git+https://github.com/AzizulHakim00/fedfalsify.git@${PINNED_SOURCE_COMMIT}[dev,study]"` using the literal commit value generated into the cell;
7. print Python/NumPy/SciPy/pandas/joblib/platform metadata;
8. run deterministic Phase-3B pytest gate from a shallow pinned source checkout or downloaded archive;
9. invoke the engineering runner with output directory and seed 29300;
10. print organized final tables, artifact paths, manifest path, and ZIP SHA256.

- [ ] **Step 4: Generate notebook and run structure tests GREEN**

```bash
python tools/build_phase3_engineering_colab.py
pytest -q tests/test_phase3_colab_notebook.py
```

- [ ] **Step 5: Commit notebook builder and generated notebook**

```bash
git add tools/build_phase3_engineering_colab.py tests/test_phase3_colab_notebook.py colab/FedFalsify_Phase3_NCSC_OneCell.ipynb
git commit -m "feat: add pinned one-cell Phase-3 Colab runner"
```

Note: the notebook intentionally pins the scientific-source commit immediately before notebook generation. The later notebook commit is a runner wrapper commit; scientific package behavior remains the pinned source.

---

### Task 12: Full Verification, Review Gate, Then One Engineering Smoke

**Files:**
- Potentially modify only Phase-3B files found deficient during review; frozen comparator files remain immutable.
- Create after successful engineering run: `research/PHASE3B_ENGINEERING_VERIFICATION.md`

**Interfaces:**
- Verification report records exact source commit, protocol SHA, test counts, engineering-run integrity, artifact SHA manifest, and whether Phase-3B is safe to freeze for later fresh-development protocol design.

- [ ] **Step 1: Run full deterministic test suite before 29300**

```bash
python -m pip install -e ".[dev,study]"
pytest -q
```

Expected: zero failures.

- [ ] **Step 2: Verify frozen comparator diff before 29300**

```bash
git diff --exit-code 78d0ab7ca7afb1edfa4725a45dfd20ce2db39659 -- \
  src/fedfalsify/scsv_v11.py \
  src/fedfalsify/scsv_v11_study.py \
  src/fedfalsify/scsv_v10_benchmarks.py
```

Expected: no output, exit 0.

- [ ] **Step 3: Review scientific invariants line-by-line**

Confirm from tests/code:

- SCR uses Selector only for final shared certification;
- NCEE role discovery uses Discovery only;
- Selector localized screening cannot add/change a frozen hypothesis;
- Probe cannot nominate or change hypotheses;
- Holm/BH constants exactly match spec;
- shared/localized/final capacities match spec;
- outside-role tolerance exactly `1e-10`;
- no truth labels/target term sets enter scientific modules;
- no blocked seed can reach engineering runner;
- engineering PASS does not inspect performance metrics.

Any failure stops execution before seed 29300.

- [ ] **Step 4: Run the one and only planned Phase-3 engineering integration smoke**

In Google Colab, execute only the generated single cell. It must mount Drive and run the exact six seed-29300 conditions with checkpoint/resume and four methods per condition.

A disconnect may resume the same 29300 engineering matrix. A software/infrastructure defect may be fixed and rerun only if the scientific constants/rules remain unchanged; 29300 results may never justify a scientific-rule change.

- [ ] **Step 5: Verify saved artifacts from Drive**

Require:

- 6 complete conditions;
- 24 primary method rows;
- no duplicate or partial groups;
- all required diagnostics files present;
- PKL and joblib load successfully;
- CSV/JSON/TXT summaries reconstruct without PKL/joblib;
- ZIP `testzip()` returns `None`;
- every manifest hash matches;
- engineering decision is based only on integrity criteria.

- [ ] **Step 6: Write verification report**

Record actual test counts, source SHA, protocol SHA, ZIP SHA, max centralized/federated numerical discrepancies, integrity status, and any non-scientific engineering defects fixed before the successful run.

Do **not** declare Phase-3 scientific GO from engineering performance.

- [ ] **Step 7: Final commit after verified engineering smoke**

```bash
git add research/PHASE3B_ENGINEERING_VERIFICATION.md
git commit -m "research: seal Phase-3B engineering verification"
```

At this point stop. Do not create or run a `29301--29310` development harness. The next research action, if engineering verification passes, is a separate frozen fresh-development protocol review.

---

## Plan self-review

### Spec coverage

- SCR: Tasks 4, 8.
- NCEE Discovery roles: Task 5.
- Selector/Probe firewall and Holm final certification: Task 6.
- Frozen-v11 SCR-only ablation: Task 7.
- Four-method composition: Task 8.
- Diagnostic ledger: Tasks 4--6, 8, 10.
- Seed firewall and exact 29300-only matrix: Tasks 1, 9.
- Google Drive persistence, CSV/PKL/joblib/JSON/TXT/ZIP: Task 10.
- One-cell Colab, pinned source/protocol, organized live output: Task 11.
- No fresh development: Global Constraints, Tasks 9--12.
- Full verification before claims: Task 12.

### Scope decision

The plan intentionally does **not** implement `phase3_development.py`, external baselines, real datasets, heteroskedastic inference, or final-confirmation code. Those are scientifically separate phases and adding them now would violate the user's instruction not to overdo or drift.

### Type/interface consistency

- All structural inference consumes `SufficientStatsPacket` and term sets, never transported coefficients.
- SCR returns a term set plus diagnostics.
- NCEE returns immutable role hypotheses.
- Probe consumes immutable hypotheses and returns a subset of Holm rejections.
- `scsv_v12.py` is the only scientific composition layer.
- The engineering runner consumes composed branch outputs and never feeds benchmark metrics back into science.
