# Phase 3A Shadow Refactor and Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and verify additive Phase-3 statistical infrastructure that is numerically equivalent to the frozen predecessor sufficient-statistic calculations without modifying the official v11 comparator or spending any fresh scientific seed.

**Architecture:** Phase 3A is an additive shadow refactor. New reusable sufficient-statistic, deterministic least-squares/rank, and caching primitives are added beside the frozen predecessor implementation. The official `scsv_v11.py` and its study path remain scientifically unchanged. Equivalence is established with deterministic fixtures and engineering-only seed `29001` before any Phase-3B scientific method code is written.

**Tech Stack:** Python >=3.10, NumPy >=1.26,<3, pytest >=8,<9, existing FedFalsify benchmark/data structures.

**Spec:** `docs/superpowers/specs/2026-09-06-scsv-ncsc-phase3-final-candidate.md`

## Global Constraints

- Base scientific source remains `e58ff85a93a7498a6220a3032d153c02290de352`.
- Work only on `research/phase3-noise-calibrated-scope-certification` or an isolated worktree/feature branch derived from it.
- `src/fedfalsify/scsv_v11.py` is a frozen scientific comparator and must not be edited in Phase 3A.
- `src/fedfalsify/scsv_v11_study.py` scientific rules, `SMOKE_SEED=29001`, and v11 development seeds must not be changed.
- Do not regenerate or use `29101--29105` or `29201--29205`.
- Do not touch `29300`, `29301--29310`, or `11001+` in Phase 3A.
- No new scientific threshold, alpha level, q level, rescue rule, candidate grammar, or benchmark condition is introduced in Phase 3A.
- Existing predecessor numerical outside-safety tolerance `1e-10` is not changed.
- Deterministic catalog/client ordering must be preserved.
- New numerical primitives must be additive and testable without changing official v11 decisions.
- No performance optimization is accepted until numerical equivalence tests pass.

---

## File Structure Locked for Phase 3A

**Create**

- `src/fedfalsify/sufficient_stats.py` — immutable additive packet representation, packet construction, aggregation, SSE reconstruction.
- `src/fedfalsify/linear_algebra.py` — deterministic rank policy and least-squares fit from sufficient statistics.
- `src/fedfalsify/phase3_cache.py` — condition-local immutable packet/cache bundle for reuse by future Phase 3B code.
- `studies/phase3a_parity.py` — engineering-only parity/equivalence audit using deterministic fixtures and seed `29001` only.
- `tests/test_sufficient_stats.py` — old/new packet and SSE equivalence.
- `tests/test_linear_algebra.py` — centralized/federated least-squares and rank equivalence.
- `tests/test_phase3_cache.py` — cache determinism and packet reuse invariants.
- `tests/test_phase3a_seed_firewall.py` — hard guard that Phase 3A cannot execute scientific namespaces.
- `research/PHASE3A_PARITY_REPORT.md` — generated only after all Phase 3A verification passes.

**Do not modify**

- `src/fedfalsify/scsv_v11.py`
- `src/fedfalsify/scsv_v11_study.py`
- `src/fedfalsify/scsv_v10_benchmarks.py`
- spent Phase-1/Phase-2 result artifacts

---

### Task 1: Lock the Frozen-v11 Comparator Boundary

**Files:**
- Create: `tests/test_phase3a_seed_firewall.py`
- Test: `tests/test_scsv_v11.py`
- Read only: `src/fedfalsify/scsv_v11.py`
- Read only: `src/fedfalsify/scsv_v11_study.py`

**Interfaces:**
- Consumes: `SMOKE_SEED`, `DEVELOPMENT_SEEDS`, `_validate_seeds` from `fedfalsify.scsv_v11_study`.
- Produces: a Phase-3A-only guard function in the test file proving allowed engineering seeds are exactly `{29001}`.

- [ ] **Step 1: Write the Phase-3A seed-firewall tests**

Create `tests/test_phase3a_seed_firewall.py` with:

```python
import pytest

from fedfalsify.scsv_v11_study import DEVELOPMENT_SEEDS, SMOKE_SEED

PHASE3A_ALLOWED_SEEDS = {29001}
PHASE1_SPENT = {29101, 29102, 29103, 29104, 29105}
PHASE2_SPENT = {29201, 29202, 29203, 29204, 29205}
PHASE3_ENGINEERING_RESERVED = {29300}
PHASE3_FRESH_RESERVED = set(range(29301, 29311))
FINAL_RESERVED = set(range(11001, 12000))


def validate_phase3a_seed(seed: int) -> None:
    if int(seed) not in PHASE3A_ALLOWED_SEEDS:
        raise ValueError("Phase 3A permits engineering seed 29001 only")


def test_phase3a_seed_namespace_is_disjoint_from_all_scientific_blocks():
    assert SMOKE_SEED == 29001
    assert set(DEVELOPMENT_SEEDS) == PHASE1_SPENT
    assert PHASE3A_ALLOWED_SEEDS.isdisjoint(PHASE1_SPENT)
    assert PHASE3A_ALLOWED_SEEDS.isdisjoint(PHASE2_SPENT)
    assert PHASE3A_ALLOWED_SEEDS.isdisjoint(PHASE3_ENGINEERING_RESERVED)
    assert PHASE3A_ALLOWED_SEEDS.isdisjoint(PHASE3_FRESH_RESERVED)
    assert PHASE3A_ALLOWED_SEEDS.isdisjoint(FINAL_RESERVED)


def test_phase3a_rejects_every_non_29001_namespace():
    for seed in (29101, 29201, 29300, 29301, 11001):
        with pytest.raises(ValueError, match="29001 only"):
            validate_phase3a_seed(seed)
```

- [ ] **Step 2: Run the new firewall tests**

Run:

```bash
pytest -q tests/test_phase3a_seed_firewall.py
```

Expected: `2 passed`.

- [ ] **Step 3: Re-run frozen v11 tests before adding infrastructure**

Run:

```bash
pytest -q tests/test_scsv_v11.py
```

Expected: all existing v11 tests pass; current repository baseline is six tests.

- [ ] **Step 4: Record the frozen comparator file hashes locally for the implementation session**

Run:

```bash
sha256sum src/fedfalsify/scsv_v11.py src/fedfalsify/scsv_v11_study.py > /tmp/phase3a_frozen_v11.sha256
cat /tmp/phase3a_frozen_v11.sha256
```

Expected: two SHA256 lines. These are checked again in Task 6.

- [ ] **Step 5: Commit the firewall test only**

```bash
git add tests/test_phase3a_seed_firewall.py
git commit -m "test: lock Phase-3A engineering seed firewall"
```

---

### Task 2: Add an Additive Sufficient-Statistic Packet Module

**Files:**
- Create: `src/fedfalsify/sufficient_stats.py`
- Create: `tests/test_sufficient_stats.py`
- Read only comparator: `src/fedfalsify/scsv_diagnostic.py`

**Interfaces:**
- Consumes: `TermCatalog`; dataset objects exposing `.x`, `.y`, `.client_id`.
- Produces:
  - `SufficientStatsPacket`
  - `packet_from_dataset(dataset, catalog, terms)`
  - `aggregate_packets(packets)`
  - `subset_packet(packet, selected_terms)`
  - `sse_from_packet(packet, terms, coefficients)`

- [ ] **Step 1: Write failing compatibility tests against the predecessor packet implementation**

Create `tests/test_sufficient_stats.py`:

```python
import numpy as np

from fedfalsify.scsv_diagnostic import _packet as predecessor_packet
from fedfalsify.scsv_diagnostic import _packet_sse as predecessor_packet_sse
from fedfalsify.scsv_v10_benchmarks import generate_v10_benchmark, v10_catalog
from fedfalsify.sufficient_stats import (
    packet_from_dataset,
    sse_from_packet,
)


def _fixture():
    generated = generate_v10_benchmark(
        "quadratic_role_v10",
        seed=29001,
        num_clients=4,
        balance_profile="balanced",
        role_profile="single",
        noise_ratio=0.10,
    )
    catalog = v10_catalog()
    terms = ("1", "x1", "x3^2", "I(x3<-0.90)*x3^2")
    return generated.clients[0], catalog, terms


def test_shadow_packet_matches_predecessor_packet_numerically():
    dataset, catalog, terms = _fixture()
    old = predecessor_packet(dataset, catalog, terms)
    new = packet_from_dataset(dataset, catalog, terms)
    assert new.client_id == old.client_id
    assert new.support == old.support
    assert new.terms == old.terms
    np.testing.assert_allclose(new.gram, old.gram, rtol=0.0, atol=1e-12)
    np.testing.assert_allclose(new.target, old.target, rtol=0.0, atol=1e-12)
    assert abs(new.target_energy - old.target_energy) <= 1e-12
    assert new.observed_support == old.observed_support


def test_shadow_sse_matches_predecessor_sse():
    dataset, catalog, terms = _fixture()
    old = predecessor_packet(dataset, catalog, terms)
    new = packet_from_dataset(dataset, catalog, terms)
    coefficients = np.asarray([0.1, 0.5, 0.8, 0.2], dtype=float)
    from fedfalsify.basis import CandidateEquation
    candidate = CandidateEquation(terms, tuple(coefficients), "phase3a-parity")
    expected = predecessor_packet_sse(old, terms, candidate)
    observed = sse_from_packet(new, terms, coefficients)
    assert abs(observed - expected) <= 1e-10
```

- [ ] **Step 2: Run the tests and confirm import failure**

```bash
pytest -q tests/test_sufficient_stats.py
```

Expected: FAIL because `fedfalsify.sufficient_stats` does not yet exist.

- [ ] **Step 3: Implement the immutable packet and packet construction**

Create `src/fedfalsify/sufficient_stats.py` with the following public API and semantics:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

from .basis import TermCatalog


@dataclass(frozen=True)
class SufficientStatsPacket:
    client_id: str
    support: int
    terms: tuple[str, ...]
    gram: np.ndarray
    target: np.ndarray
    target_energy: float
    observed_support: tuple[int, ...]


def packet_from_dataset(dataset, catalog: TermCatalog, terms: tuple[str, ...]) -> SufficientStatsPacket:
    design = catalog.matrix(dataset.x, terms)
    gram = np.asarray(design.T @ design, dtype=float)
    target = np.asarray(design.T @ dataset.y, dtype=float)
    target_energy = float(np.asarray(dataset.y, dtype=float) @ np.asarray(dataset.y, dtype=float))
    observed_support = tuple(
        int(np.count_nonzero(np.abs(catalog.get(term).evaluate(dataset.x)) > 1e-12))
        for term in terms
    )
    return SufficientStatsPacket(
        client_id=str(dataset.client_id),
        support=int(len(dataset.y)),
        terms=tuple(terms),
        gram=gram,
        target=target,
        target_energy=target_energy,
        observed_support=observed_support,
    )
```

Add exact term-index validation and implement `sse_from_packet` from

`q - 2 beta^T h + beta^T G beta`, clamped to `max(sse, 0.0)` only for floating-point cancellation, matching the predecessor behavior.

- [ ] **Step 4: Add packet aggregation tests**

Append tests verifying that elementwise sums of client packets equal a packet built from explicit row concatenation of the same clients. Use `np.testing.assert_allclose(..., atol=1e-10, rtol=1e-12)` for Gram/target/energy.

- [ ] **Step 5: Run the sufficient-stat tests**

```bash
pytest -q tests/test_sufficient_stats.py
```

Expected: all tests PASS.

- [ ] **Step 6: Run frozen v11 tests again**

```bash
pytest -q tests/test_scsv_v11.py
```

Expected: all PASS; no predecessor file was edited.

- [ ] **Step 7: Commit**

```bash
git add src/fedfalsify/sufficient_stats.py tests/test_sufficient_stats.py
git commit -m "feat: add Phase-3 additive sufficient-stat primitives"
```

---

### Task 3: Add Deterministic Rank and Least-Squares Reconstruction

**Files:**
- Create: `src/fedfalsify/linear_algebra.py`
- Create: `tests/test_linear_algebra.py`

**Interfaces:**
- Consumes: aggregated `SufficientStatsPacket` and exact ordered selected terms.
- Produces:
  - `RankPolicy`
  - `LeastSquaresFit`
  - `matrix_rank_svd(matrix, policy)`
  - `fit_from_sufficient_stats(packet, selected_terms, policy)`

- [ ] **Step 1: Write centralized-equivalence tests first**

Create `tests/test_linear_algebra.py` with a deterministic generated condition using seed `29001`. For selected terms `("1", "x1", "x3^2")`, concatenate all client rows directly and compute:

```python
X = catalog.matrix(x_concat, selected_terms)
y = y_concat
beta_central, *_ = np.linalg.lstsq(X, y, rcond=None)
sse_central = float(np.sum((y - X @ beta_central) ** 2))
rank_central = int(np.linalg.matrix_rank(X))
```

Then compare those values with `fit_from_sufficient_stats(...)` from the summed client packets:

```python
np.testing.assert_allclose(fit.coefficients, beta_central, rtol=1e-10, atol=1e-10)
assert abs(fit.sse - sse_central) <= 1e-8
assert fit.rank == rank_central
```

Add a rank-deficient fixture with two duplicate columns and assert `fit.full_rank is False`.

- [ ] **Step 2: Run tests and confirm failure**

```bash
pytest -q tests/test_linear_algebra.py
```

Expected: FAIL because `fedfalsify.linear_algebra` is absent.

- [ ] **Step 3: Implement one global deterministic rank policy**

Use:

```python
@dataclass(frozen=True)
class RankPolicy:
    relative_tolerance: float = 1.0


def _svd_tolerance(singular_values: np.ndarray, rows: int, cols: int) -> float:
    if singular_values.size == 0:
        return 0.0
    return float(max(rows, cols) * np.finfo(float).eps * singular_values[0])
```

Do not add a user-tunable scientific rank threshold. The effective threshold is matrix-scale times machine precision.

- [ ] **Step 4: Implement `fit_from_sufficient_stats`**

The function must:

1. subset Gram/target by exact ordered terms;
2. compute a deterministic eig/SVD-based pseudoinverse only for numerical reconstruction;
3. report effective rank explicitly;
4. compute minimized SSE as `q - 2 beta^T h + beta^T G beta`;
5. clamp only tiny negative SSE caused by floating-point cancellation to zero;
6. expose whether the selected normal equations are full rank.

Use a frozen dataclass:

```python
@dataclass(frozen=True)
class LeastSquaresFit:
    terms: tuple[str, ...]
    coefficients: tuple[float, ...]
    sse: float
    rank: int
    residual_df: int
    full_rank: bool
```

- [ ] **Step 5: Run numerical-equivalence tests**

```bash
pytest -q tests/test_linear_algebra.py tests/test_sufficient_stats.py
```

Expected: all PASS.

- [ ] **Step 6: Run v11 tests**

```bash
pytest -q tests/test_scsv_v11.py
```

Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add src/fedfalsify/linear_algebra.py tests/test_linear_algebra.py
git commit -m "feat: add deterministic sufficient-stat least squares"
```

---

### Task 4: Build a Condition-Local Immutable Packet Cache

**Files:**
- Create: `src/fedfalsify/phase3_cache.py`
- Create: `tests/test_phase3_cache.py`

**Interfaces:**
- Consumes: existing `partition_clients`, `split_selector_probe`, catalog, exact all-term tuple, engineering seed.
- Produces:
  - `Phase3PacketCache`
  - `build_phase3_packet_cache(datasets, catalog, all_terms, seed)`
  - immutable discovery/selector/probe packet tuples keyed by client order.

- [ ] **Step 1: Write determinism and one-build tests**

Create tests that build the cache twice for the same 29001 benchmark condition and assert:

```python
assert cache1.client_ids == cache2.client_ids
assert cache1.all_terms == cache2.all_terms
for a, b in zip(cache1.discovery, cache2.discovery):
    np.testing.assert_allclose(a.gram, b.gram, atol=0.0, rtol=0.0)
```

Also compare each shadow discovery/selector/probe packet numerically with the corresponding predecessor `_build_packets(...)` packet for the same partition objects.

- [ ] **Step 2: Run tests and confirm failure**

```bash
pytest -q tests/test_phase3_cache.py
```

Expected: module import failure.

- [ ] **Step 3: Implement the cache without changing predecessor code**

Use a frozen dataclass:

```python
@dataclass(frozen=True)
class Phase3PacketCache:
    seed: int
    client_ids: tuple[str, ...]
    all_terms: tuple[str, ...]
    discovery: tuple[SufficientStatsPacket, ...]
    selector: tuple[SufficientStatsPacket, ...]
    probe: tuple[SufficientStatsPacket, ...]
```

`build_phase3_packet_cache` must call the existing deterministic `partition_clients(...)` and `split_selector_probe(...)` exactly once per condition and build each packet tuple exactly once.

- [ ] **Step 4: Add an explicit no-fresh-seed guard parameter**

At the top-level builder, reject any seed other than `29001` while the module is in Phase-3A engineering mode:

```python
if int(seed) != 29001:
    raise ValueError("Phase-3A cache builder is engineering-only and permits seed 29001")
```

This guard will be removed/replaced only in the separately reviewed Phase-3B study harness, not silently relaxed here.

- [ ] **Step 5: Run cache and predecessor tests**

```bash
pytest -q tests/test_phase3_cache.py tests/test_scsv_v11.py
```

Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add src/fedfalsify/phase3_cache.py tests/test_phase3_cache.py
git commit -m "feat: add deterministic Phase-3 engineering packet cache"
```

---

### Task 5: Build the Engineering-Only Phase-3A Parity Audit

**Files:**
- Create: `studies/phase3a_parity.py`
- Test: `tests/test_phase3a_seed_firewall.py`
- Read only: `src/fedfalsify/scsv_v11_study.py`

**Interfaces:**
- Consumes: the six frozen `_smoke_conditions()` from v11, `SMOKE_SEED=29001`, old predecessor packet helpers, new Phase-3A primitives.
- Produces: deterministic JSON report containing six condition-level equivalence records and aggregate PASS/FAIL.

- [ ] **Step 1: Implement a report schema before the runner**

Use:

```python
@dataclass(frozen=True)
class Phase3AParityRecord:
    family: str
    noise_ratio: float
    num_clients: int
    balance_profile: str
    role_profile: str
    seed: int
    packet_equivalent: bool
    aggregate_equivalent: bool
    least_squares_equivalent: bool
    max_abs_gram_error: float
    max_abs_target_error: float
    max_abs_sse_error: float


@dataclass(frozen=True)
class Phase3AParityReport:
    schema_version: int
    seed: int
    conditions: int
    passed: bool
    records: tuple[Phase3AParityRecord, ...]
```

- [ ] **Step 2: Implement the runner using only `_smoke_conditions()`**

The runner must import the frozen six engineering smoke conditions and assert every condition seed equals `29001` before generating data.

For each condition:

1. generate the benchmark using existing `generate_v10_benchmark`;
2. build predecessor packets and shadow packets on the same deterministic partitions;
3. compare Gram/target/energy/support values;
4. aggregate all discovery packets and compare with direct centralized row concatenation;
5. fit at least the ordinary anchor-compatible term subset using the new least-squares primitive and direct `np.linalg.lstsq`;
6. record maximum absolute errors.

No exact-recovery, deviation-recall, benchmark truth, or GO/NO-GO performance metric is computed in Phase 3A.

- [ ] **Step 3: Add hard scientific-namespace assertions**

Before execution:

```python
assert SMOKE_SEED == 29001
assert all(condition[-1] == 29001 for condition in _smoke_conditions())
```

Reject command-line seed overrides entirely; Phase 3A runner has no `--seed` argument.

- [ ] **Step 4: Add JSON output only to an explicitly supplied engineering path**

CLI:

```bash
python -m studies.phase3a_parity --output /tmp/phase3a_parity.json
```

The runner must fail if the output parent path contains `results/scsv_v11`, `phase1`, `phase2`, `29301`, or `11001` as a defensive namespace check.

- [ ] **Step 5: Run the audit**

```bash
python -m studies.phase3a_parity --output /tmp/phase3a_parity.json
cat /tmp/phase3a_parity.json
```

Expected:

- `seed: 29001`
- `conditions: 6`
- `passed: true`
- all packet/aggregate/least-squares equivalence booleans true
- numerical errors within the tolerances already asserted by unit tests.

- [ ] **Step 6: Commit**

```bash
git add studies/phase3a_parity.py
git commit -m "test: add Phase-3A engineering parity audit"
```

---

### Task 6: Full Verification and Frozen-Comparator Integrity Check

**Files:**
- Create only after PASS: `research/PHASE3A_PARITY_REPORT.md`
- Verify: all Phase-3A and existing tests.

**Interfaces:**
- Consumes: all previous Phase-3A tasks.
- Produces: human-readable sealed Phase-3A parity report. Phase-3B remains blocked until this report is reviewed.

- [ ] **Step 1: Run the complete test suite**

```bash
pytest -q
```

Expected: all repository tests PASS.

- [ ] **Step 2: Run focused Phase-3A tests with verbose output**

```bash
pytest -v \
  tests/test_phase3a_seed_firewall.py \
  tests/test_sufficient_stats.py \
  tests/test_linear_algebra.py \
  tests/test_phase3_cache.py \
  tests/test_scsv_v11.py
```

Expected: all PASS.

- [ ] **Step 3: Run the six-condition engineering audit again**

```bash
python -m studies.phase3a_parity --output /tmp/phase3a_parity_final.json
python - <<'PY'
import json
p = json.load(open('/tmp/phase3a_parity_final.json'))
assert p['seed'] == 29001
assert p['conditions'] == 6
assert p['passed'] is True
print('PHASE3A PARITY PASS')
PY
```

Expected: `PHASE3A PARITY PASS`.

- [ ] **Step 4: Verify frozen comparator files were not modified**

```bash
sha256sum -c /tmp/phase3a_frozen_v11.sha256
```

Expected:

```text
src/fedfalsify/scsv_v11.py: OK
src/fedfalsify/scsv_v11_study.py: OK
```

If either hash fails, stop and inspect; do not write the parity report.

- [ ] **Step 5: Write `research/PHASE3A_PARITY_REPORT.md`**

The report must contain exactly these factual sections:

```markdown
# Phase 3A Parity Report

## Scope
Engineering-only additive shadow refactor; no new scientific behavior.

## Seed use
Only 29001 was used. No 291xx, 292xx, 293xx, or 11001+ seed was executed.

## Frozen comparator integrity
scsv_v11.py unchanged: PASS
scsv_v11_study.py unchanged: PASS

## Numerical equivalence
Packet equivalence: PASS
Aggregated sufficient-stat equivalence: PASS
Centralized-vs-federated least-squares equivalence: PASS
Deterministic rank tests: PASS

## Repository tests
Full pytest suite: PASS

## Decision
PHASE3A-ENGINEERING-PASS. This authorizes review of a separate Phase-3B scientific implementation plan only. It does not authorize fresh development.
```

Include actual test counts and SHA256 values from the verification run; do not estimate them.

- [ ] **Step 6: Commit the sealed engineering report**

```bash
git add research/PHASE3A_PARITY_REPORT.md
git commit -m "research: seal Phase-3A parity verification"
```

- [ ] **Step 7: Stop**

Do not implement SCR, NCEE, Holm testing, partial F tests, `scsv_v12.py`, a Phase-3 development runner, or any `293xx` execution in this plan. Those belong to a separate Phase-3B implementation plan written only after Phase-3A passes and is reviewed.

---

## Self-Review Checklist

Before executing this plan, verify:

- Every task has a failing-test -> implementation -> passing-test cycle where code is added.
- `scsv_v11.py` and `scsv_v11_study.py` remain read-only throughout Phase 3A.
- No task imports or generates spent Phase-1/Phase-2 development conditions.
- No task uses `29300`, `29301--29310`, or `11001+`.
- Phase 3A computes numerical equivalence only, not scientific performance or GO/NO-GO metrics.
- No Phase-3B statistical threshold or inferential rule is implemented here.
- New modules are additive and can be deleted without altering frozen v11 behavior.
- The final parity report is created only after the complete test suite and frozen-file hash checks pass.

## Execution Boundary

This plan intentionally covers **Phase 3A only**. Phase 3B (SCR, NCEE, partial nested F tests, Holm/BH multiplicity control, sequential Selector/Probe certification, ablations, 29300 engineering smoke, and prospective 29301--29310 development protocol) requires its own reviewed implementation plan after Phase 3A is sealed.
