# Phase-3B Scientific Implementation Design

**Status:** Written design for human review; implementation not yet authorized  
**Date:** 2026-09-06  
**Base branch/commit:** `research/phase3a-shadow-refactor-parity` @ `78d0ab7ca7afb1edfa4725a45dfd20ce2db39659`  
**Implementation branch:** `research/phase3b-scientific-implementation`  
**Scientific target:** FedFalsify v12 / SCSV-NCSC  

## 1. Objective

Phase-3B implements exactly the scientific mechanisms already motivated by the sealed Phase-1/Phase-2 evidence and the approved SCSV-NCSC specification:

1. **SCR — Shared-Core Re-certification** to correct high-noise ordinary/shared structural errors that v11 leaves immutable.
2. **NCEE — Noise-Calibrated Effect Evidence** to improve high-noise localized-deviation certification while preserving strict false-structure control.

Phase-3B is not PQCR-v3, not a threshold-retuning exercise, and not an opportunity to expand the grammar or add rescue heuristics.

The implementation must preserve the sequential scientific firewall:

`Discovery -> Selector -> Probe`.

## 2. Non-negotiable scientific constraints

The following remain fixed throughout Phase-3B:

- frozen primary comparator: unmodified v11;
- frozen grammar and condition geometry from v10/v11;
- shared structure capacity: maximum 6 terms total including intercept;
- localized operational capacity: maximum 2 deviations;
- final total structure capacity: maximum 10 terms including intercept;
- `alpha_shared = 0.05`, Holm step-down;
- `q_role = 0.10`, BH, exploratory role construction only;
- `alpha_dev = 0.05`, Holm step-down on the untouched Probe family;
- outside-role non-degradation rule: `SSE_FULL <= SSE_REDUCED + 1e-10`;
- rank policy fixed at the Phase-3A machine-scale convention;
- no family-specific, noise-specific, seed-specific, or post-hoc statistical threshold;
- no positive pooled-delta tolerance;
- no PQCR rescue, DR arbitration, consensus rescue, globality repair, or HEAR-style repair;
- no benchmark-truth use in inference;
- no modification of a Probe hypothesis after Probe is read.

## 3. Scientific modules

### 3.1 Nested structural test engine

A single reusable engine must compare fixed nested models from sufficient statistics.

For a fixed client scope and fixed ordered term sets:

- REDUCED = shared structure;
- FULL = shared structure + one candidate term.

The engine must:

1. fit REDUCED and FULL using the sealed Phase-3A sufficient-statistic/rank primitives;
2. require `rank(FULL) = rank(REDUCED) + 1`;
3. require positive residual degrees of freedom;
4. compute minimized `SSE_R` and `SSE_F`;
5. compute

   `F = ((SSE_R - SSE_F) / 1) / (SSE_F / (N - rank_FULL))`;

6. return the upper-tail `F(1, N-rank_FULL)` p-value;
7. abstain rather than regularize if the added structural degree is not identifiable;
8. record the fitted coefficient of the candidate and its sign.

The same engine is used by SCR, NCEE client-role discovery, Selector diagnostics, and Probe confirmation.

### 3.2 Multiple-testing engine

Implement two deterministic procedures only:

- Holm step-down with adjusted p-values and rejection set;
- Benjamini-Hochberg with adjusted q-values/rejection set.

Required properties:

- stable handling of ties through original/canonical hypothesis order;
- no hidden randomization;
- no dependency on benchmark labels/truth;
- adjusted values and raw values both recorded.

### 3.3 SCR — Shared-Core Re-certification

Discovery nominates the shared candidate family from:

- intercept;
- ordinary terms in the predecessor selector structure;
- ordinary terms in the predecessor high-recall bank.

Gated/exception terms are excluded from this family.

Selector then independently certifies the Discovery-frozen ordinary family:

1. construct one pooled joint model containing all identifiable ordinary candidates;
2. for each non-intercept term, compare the joint FULL model against joint REDUCED with that term removed;
3. compute one-df partial nested-model p-values;
4. apply Holm at `alpha_shared = 0.05`;
5. retain intercept plus rejected non-intercept terms;
6. if more than five non-intercept terms survive, retain the five smallest Holm-adjusted p-values with canonical catalog order as final tie-breaker;
7. record any capacity truncation;
8. rank-ambiguous candidates are not certified and receive an explicit abstention code.

The resulting shared **term set**, not a transported coefficient vector, is passed to later structural tests. Nuisance coefficients are re-estimated within each evaluation split.

### 3.4 NCEE — Discovery role construction

After the shared structure is frozen for the given method branch:

For every nominated localized candidate and every client on Discovery:

1. test REDUCED shared structure vs FULL shared-plus-candidate;
2. require at least 10 active candidate rows;
3. require FULL rank increase exactly one;
4. require residual degrees of freedom at least 5;
5. compute the client partial-F p-value and candidate coefficient sign;
6. apply BH `q_role = 0.10` across eligible clients for that candidate;
7. BH-supported clients form the provisional role.

Role admissibility requires:

- at least one role client;
- at least one outside client;
- role size no greater than half of all clients;
- common nonzero candidate coefficient sign among supported clients;
- declared source-term provenance;
- weak structural heredity because the source is in either the chosen shared structure or the Discovery high-recall bank.

Before Selector localized screening, freeze:

- candidate term;
- source term;
- role IDs;
- outside IDs;
- Discovery sign.

### 3.5 Selector localized screening

Selector may only screen/remove frozen localized hypotheses.

For each frozen candidate-role hypothesis:

1. compute a role-scope partial nested F statistic/p-value as diagnostic only;
2. require Selector candidate sign = Discovery sign;
3. require positive median role-client raw gain `SSE_R - SSE_F`;
4. require exact FULL/REDUCED structural nesting;
5. require rank/estimability validity;
6. require outside-role non-degradation with `1e-10` tolerance.

Selector p-values are not final significance claims.

### 3.6 Probe final localized certification

Probe is untouched until the complete surviving localized family is frozen.

For every surviving localized hypothesis:

1. use Probe only;
2. test role-scope REDUCED shared structure vs FULL shared-plus-candidate;
3. require rank increase exactly one;
4. compute one-df partial nested F p-value;
5. apply Holm `alpha_dev = 0.05` across the complete frozen Probe family;
6. require Probe candidate sign = Discovery sign;
7. require positive median role-client Probe gain;
8. require Probe outside-role non-degradation with `1e-10` tolerance;
9. require structural nesting/invariance.

Final localized acceptances must be a strict subset of Holm rejections after deterministic safety filters.

If multiple accepted localized candidates share one source, reject the source-linked localized set as ambiguous.

If more than two localized candidates would become operational, reject the newly proposed localized set rather than selecting by benchmark outcome.

## 4. Four primary scientific branches

Every engineering/future-development condition must be evaluable through the same APIs as:

1. **v11** — frozen unmodified comparator;
2. **SCR-only** — SCR shared structure + predecessor v11 localized scientific logic unchanged;
3. **NCEE-only** — predecessor v11 shared structure exactly + new NCEE localized path;
4. **Full SCSV-NCSC** — SCR shared structure + NCEE localized path.

Common packet/statistical primitives must be shared across the three Phase-3 branches so that ablation differences represent scientific mechanisms rather than duplicated implementation.

## 5. Prespecified mechanism diagnostic ledger

Before any `29300` or fresh-development run, every condition must record the following diagnostics regardless of whether the method succeeds:

### Shared diagnostics

- Discovery ordinary-family size;
- ordinary candidate terms in canonical order;
- per-candidate FULL/REDUCED ranks;
- per-candidate raw shared p-value;
- per-candidate Holm-adjusted shared p-value;
- shared Holm rejection set;
- shared rank-abstention codes;
- shared capacity-truncation flag and terms removed by capacity.

### Localized diagnostics

- Discovery localized-family size;
- per-candidate/per-client eligibility;
- active support count;
- client raw p-value;
- client BH-adjusted value;
- provisional BH role IDs;
- Discovery sign;
- Selector rejection reason if removed;
- Selector role median gain;
- Selector outside-role delta SSE;
- Probe raw p-value;
- Probe Holm-adjusted p-value;
- Probe median role gain;
- Probe outside-role delta SSE;
- final accepted localized set;
- final shared structure;
- final complete structure.

These diagnostics do not affect acceptance rules. Their only purpose is reproducibility and failure explanation.

## 6. Phase-3B code boundaries

New scientific behavior must live in new modules. Frozen v11 source remains unchanged.

Planned modules:

```text
src/fedfalsify/
    nested_tests.py
    multiple_testing.py
    shared_recertification.py
    role_localization_v12.py
    localized_certification.py
    scsv_v12.py

studies/
    phase3_engineering.py
    phase3_development.py

colab/
    FedFalsify_Phase3_NCSC_OneCell.ipynb
```

Existing sealed Phase-3A modules are reused, not rewritten:

```text
src/fedfalsify/sufficient_stats.py
src/fedfalsify/linear_algebra.py
```

Frozen comparator files must be guarded by CI diff checks.

## 7. Testing requirements before integration

The following tests are required before `scsv_v12.py` may compose the full method:

1. centralized/federated coefficient equivalence;
2. centralized/federated SSE equivalence;
3. centralized/federated effective-rank equivalence;
4. centralized/federated nested-F equivalence;
5. analytic one-term full-rank F example;
6. exact-collinearity abstention;
7. deterministic near-collinearity rank behavior;
8. Holm known-vector examples;
9. BH known-vector examples;
10. post-Holm subset property;
11. Discovery candidate-family immutability after Selector begins;
12. frozen role-family immutability after Selector begins;
13. Probe family immutability after Probe begins;
14. outside-role `1e-10` tolerance regression test;
15. shared capacity exactly five non-intercept terms plus intercept;
16. localized capacity exactly two operational deviations;
17. shared-source ambiguity rejection;
18. no hidden use of benchmark truth in scientific modules;
19. frozen-v11 file diff guard;
20. frozen-v11 regression tests still pass.

## 8. Execution order

Phase-3B is implemented in this order only:

### B1 — statistical primitives

Implement nested tests and multiplicity functions. Pass all deterministic mathematical tests.

### B2 — SCR only

Implement shared re-certification and its diagnostics. Test without changing localized science.

### B3 — NCEE only

Implement Discovery role construction, Selector safety screening, and Probe final certification. Test split firewalls explicitly.

### B4 — method composition

Compose v11, SCR-only, NCEE-only, and full SCSV-NCSC through one orchestration API.

### B5 — engineering study harness

Implement the engineering-only runner using `29300` as the only permitted Phase-3 scientific integration smoke seed.

`29300` is for integration/numerical validation only. It must not be repeatedly rerun to tune alpha/q values, support floors, capacities, rank tolerance, or safety rules.

No `29301--29310` condition is permitted during B1--B5.

## 9. Colab one-cell runner requirements

The user-facing runner must follow the previous Phase-1/Phase-2 operating style while keeping the algorithm in tested package modules.

The notebook must contain exactly **one executable code cell**.

The single cell must:

1. mount Google Drive immediately;
2. create a dedicated Drive study directory;
3. print run label, source commit, protocol hash, Python/library versions and seed firewall;
4. install/download the exact pinned GitHub commit rather than an unfrozen branch head;
5. verify the frozen protocol SHA256 before any scientific evaluation;
6. run the required package test gate before the engineering smoke;
7. load an existing checkpoint if present;
8. validate checkpoint schema/completeness before resume;
9. show organized live stage output and current progress with `flush=True`;
10. write an atomic checkpoint after every complete matched condition group;
11. never save partial method groups as complete;
12. resume by skipping only fully valid completed groups;
13. show concise in-cell method/diagnostic tables at stage boundaries;
14. save every result to Google Drive before final display/packaging;
15. produce a final integrity/manifest report and ZIP;
16. print final file paths and SHA256 hashes in cell output.

The notebook source must call package APIs; it must not contain a second independent copy of the scientific algorithm.

## 10. Drive persistence and artifact contract

Phase-3 engineering smoke directory:

`/content/drive/MyDrive/FedFalsify_Q1/SCSV_NCSC_PHASE3_ENGINEERING/`

The engineering runner must save at least:

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
```

If figures are generated for engineering diagnostics, they must also be listed in the manifest. No figure is allowed to affect scientific decisions.

The final archive name is:

`FedFalsify_PHASE3_NCSC_ENGINEERING_RESULTS.zip`

The runner must test the ZIP and print the ZIP SHA256.

## 11. Checkpoint/resume semantics

For the engineering study, one condition is complete only after all four primary method rows are present:

- `v11-elrc`;
- `scr-only`;
- `ncee-only`;
- `scsv-ncsc`.

On resume:

- validate exact method set;
- validate one row per method;
- reject/remove a partial group;
- recompute that same condition in full;
- never substitute a seed;
- never advance the seed namespace because of failure/disconnect.

Checkpoint writing must use temporary-file + atomic replacement semantics where supported.

## 12. Organized live output contract

The one-cell runner must print clearly separated stages, for example:

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

Per-condition progress must include condition index/total, family, K, balance, role profile, noise and seed. Long-running output must flush live.

Scientific result summaries appear only after the engineering smoke completes; the runner must not encourage mid-run outcome peeking or adaptive changes.

## 13. Reproducibility contract

Every run must record:

- exact Git commit SHA;
- protocol SHA256;
- package version;
- Python version;
- NumPy/SciPy/pandas/sklearn versions where present;
- platform/CPU metadata available from the runtime;
- exact engineering seed;
- exact condition matrix;
- exact statistical constants;
- test command/results;
- file SHA256 manifest;
- run timestamps;
- communication and method-only runtime accounting definitions.

PKL/Joblib state is supplementary convenience. CSV/JSON/TXT remain the transparent archival formats.

## 14. Seed firewall

The implementation must hard-block:

- `29101--29105`;
- `29201--29205`;
- `29301--29310` during Phase-3 engineering;
- `11001+`.

Allowed engineering namespaces:

- `29001` only for predecessor parity tests;
- `29300` only for the Phase-3 engineering integration smoke after B1--B4 pass.

The development seeds `29301--29310` remain untouched until a later separately frozen development protocol and explicit authorization.

## 15. What Phase-3B does not do

Phase-3B does not yet:

- run fresh Phase-3 development;
- alter the prospective development gate;
- benchmark external methods;
- run realistic external datasets;
- add heteroskedastic/permutation/bootstrap inference;
- change grammar complexity;
- optimize thresholds from spent data;
- touch final confirmation seeds.

Those belong only after the engineering implementation is stable and, for external work, after a future development GO.

## 16. Approval gate

This written design must be reviewed by the user before an implementation plan is written.

After approval, the next artifact will be a detailed TDD implementation plan. Only after that plan is approved/executed will the one-cell Colab notebook and package implementation be produced.
