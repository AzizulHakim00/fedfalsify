# FedFalsify v12 / SCSV-NCSC Phase 3 Final-Candidate Specification

**Status:** Final candidate for human review; implementation not authorized  
**Date:** 2026-09-06  
**Base scientific source:** `e58ff85a93a7498a6220a3032d153c02290de352`  
**Branch:** `research/phase3-noise-calibrated-scope-certification`  
**Supersedes for implementation:** earlier Phase-3 design drafts on this branch

## 1. Scientific objective

SCSV-NCSC is a new scientific generation, not a PQCR-v3 repair. It targets two frozen failure mechanisms established by Phase 1 and Phase 2:

1. high-noise loss of power in localized/deviation certification; and
2. high-noise errors in ordinary/shared structure that v11 treats as immutable.

The target output is a symbolic model with two explicit scopes:

- a **shared symbolic core**;
- sparse **client-localized symbolic deviations** with certified client roles.

The server operates on additive sufficient statistics rather than raw rows. This is a data-local computation property only; it is not a differential-privacy or cryptographic privacy guarantee.

## 2. Frozen evidence that motivates the redesign

Phase-2 v11:

- exact recovery `0.8300`;
- deviation TP/FP/FN `461/1/59`;
- all `59/59` true-deviation misses at noise `0.30`;
- `56/59` missed true deviations already present in the high-recall bank;
- miss taxonomy: `26` role-localization, `25` pooled-evidence, `8` outside-role failures;
- `102` non-exact conditions;
- `88/102` contained shared/core error;
- `46` were shared/core-only failures;
- `87/88` shared/core-error conditions at noise `0.30`.

Phase-2 DR-PQCR-v2:

- exact recovery `0.8300`, equal to v11;
- exact gain `0.0000` on every Phase-2 seed;
- three PQCR-only rescues: one true structural rescue, two false structural additions.

Therefore the next method must improve **scope-specific structural evidence under noise**, not candidate invention or PQCR rescue arbitration.

## 3. Primary hypothesis

> A sequential Discovery -> Selector -> Probe architecture using independent shared-core certification, noise-calibrated partial nested-model evidence, and Holm-controlled final Probe testing will improve high-noise exact structural recovery over v11 without materially increasing false shared or localized structure.

Two independently ablated mechanisms are defined:

- **SCR:** Shared-Core Re-certification.
- **NCEE:** Noise-Calibrated Effect Evidence for localized deviations.

Full SCSV-NCSC = `SCR + NCEE`.

## 4. Structural model

For client `k`, observation `i`:

`y_ki = f_0(x_ki) + sum_m z_km * delta_m * phi_m(x_ki) + epsilon_ki`,

where:

- `f_0` is shared structure;
- `phi_m` is a declared localized symbolic candidate;
- `z_km in {0,1}` is localized-role membership;
- `delta_m` is the role-common localized coefficient;
- `epsilon_ki` is observation noise.

For the frozen synthetic benchmark, all clients in a condition receive independent Gaussian noise with the same pooled `noise_std`. Classical nested-model F calibration is therefore aligned with the development generator. External-data calibration is a separate question and must be revalidated under a separately frozen protocol.

## 5. Sequential split firewall

The existing deterministic partitions are retained, but scientific responsibilities are separated.

### 5.1 Discovery D

Discovery may perform only:

- v6 high-recall candidate-bank generation;
- ordinary/shared candidate nomination;
- localized candidate nomination and provenance;
- exploratory localized-role construction after Selector has fixed shared structure.

Discovery does not provide a final structural p-value.

### 5.2 Selector S

Selector may perform:

- independent shared-core certification for the Discovery-nominated ordinary family;
- non-final localized-role screening after Discovery freezes a candidate role;
- effect-sign confirmation;
- median role-benefit checking;
- outside-role non-degradation checking;
- rank/estimability checks.

Selector does not provide the final localized acceptance p-value.

### 5.3 Probe P

Probe is reserved for final localized structural testing.

Before Probe is read, freeze:

- shared structure;
- localized candidate term;
- source term;
- role client IDs;
- outside-role client IDs;
- expected localized effect sign;
- full family of localized hypotheses to be multiplicity corrected.

Probe may not nominate terms, change roles, change shared structure, or change the tested family.

## 6. Federated sufficient statistics

For design matrix `X` and response `y`, each client packet provides:

- `G = X^T X`;
- `h = X^T y`;
- `q = y^T y`;
- `n`;
- observed term support required for gated-term diagnostics.

For any fixed client scope, `G`, `h`, `q`, and `n` add across clients exactly in real arithmetic.

All routines use canonical catalog term ordering.

## 7. Deterministic rank policy

Inferential tests use one rank-revealing SVD/QR convention implemented in a single module.

Requirements:

- one scale-aware machine-precision rank tolerance;
- no outcome-tuned rank threshold;
- no tuned ridge penalty to manufacture inferential rank;
- FULL must increase effective rank by exactly one over REDUCED;
- non-identifiable hypotheses abstain with `STRUCTURAL-RANK-AMBIGUOUS`.

The same rank convention is used in federated and centralized equivalence tests.

## 8. Core statistical primitive: partial nested-model F test

For a fixed client scope and fixed shared **structure**, compare:

- REDUCED: `y = X_S beta + epsilon`;
- FULL: `y = X_S beta + z delta + epsilon`.

Nuisance shared coefficients are re-estimated inside both models on the evaluation partition. This avoids confusing coefficient transport error with candidate-specific structural evidence.

Let:

- `SSE_R` = minimized REDUCED SSE;
- `SSE_F` = minimized FULL SSE;
- `r_F` = effective FULL rank;
- `N` = observations in the tested scope.

If `r_F = r_R + 1` and `N - r_F > 0`, compute

`F = ((SSE_R - SSE_F) / 1) / (SSE_F / (N - r_F))`.

The upper-tail `F(1, N-r_F)` probability is the structural p-value under the frozen synthetic noise assumptions.

The old raw pooled-delta statistic remains diagnostic/ablation information only and is not part of the primary v12 acceptance rule.

## 9. Multiplicity policy

### 9.1 Shared structure

Use **Holm step-down family-wise error control at `alpha_shared = 0.05`** across Selector p-values for the Discovery-nominated ordinary candidate family.

The family is fixed before Selector is inspected. Holm is valid under arbitrary dependence when the individual null p-values are valid.

### 9.2 Role discovery

Use **Benjamini-Hochberg at `q_role = 0.10`** across eligible Discovery client p-values within each localized candidate.

This is exploratory/high-recall role construction only. It is not a final inferential claim.

### 9.3 Final localized structure

Use **Holm step-down at `alpha_dev = 0.05`** across Probe p-values for the complete localized hypothesis family frozen by Discovery+Selector.

Final operational localized terms must be a subset of Holm rejections. Additional deterministic safety filters may only remove Holm rejections.

No family-specific, noise-specific, seed-specific, or post-hoc alpha/q values are allowed.

## 10. Shared-Core Re-certification (SCR)

### 10.1 Candidate family

Discovery nominates:

- intercept `1`;
- ordinary terms in the v6 selector structure;
- ordinary terms in the v6 high-recall bank.

Exception/gated terms are excluded from the ordinary shared family.

### 10.2 Selector partial tests

On Selector:

1. construct one pooled joint model containing all identifiable ordinary candidates;
2. for each non-intercept term `t`, compare joint FULL against joint REDUCED removing only `t`;
3. compute the one-df partial nested F p-value;
4. apply Holm `alpha_shared = 0.05`;
5. retain intercept plus Holm-rejected non-intercept terms.

A rank-ambiguous candidate is not certified.

### 10.3 Exact predecessor capacity

Frozen v6 uses `max_terms = 6` and explicitly enumerates at most `max_terms - 1` non-intercept terms because intercept is part of the structure.

Therefore SCR preserves:

- maximum shared structure = **6 total terms including intercept**;
- maximum non-intercept shared terms = **5**.

If more than five non-intercept terms are Holm-rejected, retain the five smallest Holm-adjusted p-values, with canonical catalog order as final tie-breaker.

Capacity-truncation frequency must be reported.

### 10.4 Shared coefficients vs shared structure

Only the **shared term set** is an input to later nested structural tests. Those tests re-estimate nuisance shared coefficients on their own evaluation split.

A Discovery+Selector shared coefficient refit may be maintained for diagnostics/prediction and later final-model initialization, but it must not substitute for the split-specific nuisance refits used by the structural test engine.

Probe remains untouched.

## 11. Noise-Calibrated Effect Evidence (NCEE)

### 11.1 Candidate provenance

A localized candidate must:

- exist in the frozen grammar;
- have a declared `source_term`;
- satisfy weak structural heredity because its source is in either the SCR shared structure or the Discovery high-recall bank.

A banked source may remain provenance-only and is not automatically inserted into shared structure.

### 11.2 Discovery client tests

After SCR freezes shared structure, return to Discovery.

For each localized candidate and each client:

1. build REDUCED shared and FULL shared-plus-candidate models;
2. re-estimate nuisance shared coefficients in each model;
3. require FULL to increase effective rank by one;
4. compute client partial F p-value;
5. record FULL candidate coefficient sign;
6. apply BH `q_role = 0.10` across eligible clients.

BH-supported clients form the provisional role.

### 11.3 Prospective estimability guard

A client is role-eligible only if:

- candidate observed support is positive;
- candidate has at least `10` active Discovery rows;
- FULL increases rank by exactly one;
- residual degrees of freedom are at least `5`.

The `10` active-row floor is a conservative prospective engineering guard, not a claim of equivalence to the predecessor five-fold rule and not a value tuned from Phase 1/2 outcomes.

### 11.4 Role admissibility

Require:

- at least one BH-supported client;
- at least one outside client;
- role size no greater than half of all clients;
- common nonzero candidate coefficient sign across supported clients.

Mixed or numerically indeterminate signs -> `SCOPE-SIGN-AMBIGUOUS`.

Support on more than half of clients -> `GLOBAL-SCOPE-AMBIGUOUS`.

### 11.5 Frozen localized hypothesis

Before Selector localized screening, freeze:

- candidate term;
- source term;
- role IDs;
- outside IDs;
- Discovery effect sign.

No later split may alter these quantities.

## 12. Selector localized screening

For each frozen localized hypothesis, Selector performs non-final screening:

1. compute role-scope partial nested F statistic/p-value as a diagnostic only;
2. require Selector candidate sign to match Discovery sign;
3. require positive median role-client raw gain `SSE_R - SSE_F`;
4. require exact structural FULL/REDUCED nesting/invariance;
5. require aggregate Selector outside-role non-degradation;
6. require rank/estimability validity.

Outside-role safety preserves the frozen predecessor numerical rule:

`SSE_FULL <= SSE_REDUCED + 1e-10`.

Hypotheses failing any Selector safety condition do not reach Probe.

Because Selector has already been used for shared-core certification, its localized screening p-value is explicitly non-final and carries no alpha-level claim.

## 13. Probe final localized certification

For every surviving frozen localized hypothesis:

1. use Probe only;
2. fit role-scope REDUCED shared and FULL shared-plus-candidate models from Probe packets;
3. require rank increase exactly one;
4. compute one-df partial nested F p-value;
5. apply Holm `alpha_dev = 0.05` across the **entire frozen Probe family**;
6. require Probe candidate sign = Discovery sign;
7. require positive median role-client Probe gain;
8. require Probe outside-role non-degradation with `1e-10` tolerance;
9. require structural nesting/invariance.

Only Holm rejections passing all safety filters become operational localized deviations.

## 14. Final structure and coefficient refit

Final structure = SCR shared terms union Probe-certified localized terms.

Frozen high-level capacities:

- shared structure <= `6` total terms including intercept;
- operational localized deviations <= `2`;
- final structure <= `10` total terms including intercept.

If multiple accepted localized candidates share one source, source ambiguity rejects that source-linked localized set.

If more than two localized candidates would become operational, global ambiguity rejects the newly proposed localized set rather than selecting by benchmark outcome.

After structure is frozen, numerical coefficients are refit using the predecessor final-refit policy on training information allowed by the study harness. The final refit cannot change structural acceptance.

## 15. Theoretical claims to prove

### Theorem A — federated/centralized least-squares equivalence

For a fixed ordered term set and deterministic rank convention, summed client `X^T X`, `X^T y`, `y^T y`, and `n` produce the same pooled least-squares solution, effective rank, and minimized SSE as centralized row concatenation up to floating-point summation error.

### Theorem B — federated/centralized nested-F equivalence

For fixed FULL/REDUCED structures and client scope, the federated partial nested F statistic and p-value equal the centralized calculation up to floating-point error.

### Proposition C — shared-family FWER

Conditional on the Discovery-nominated ordinary family and valid Selector p-values, Holm at `alpha_shared` strongly controls at least one false shared rejection at level `alpha_shared`.

### Proposition D — Probe-family FWER

Conditional on the entire Discovery+Selector hypothesis-construction pipeline, valid untouched-Probe p-values plus Holm at `alpha_dev` strongly control at least one false localized Probe rejection at level `alpha_dev`.

### Proposition E — deterministic post-Holm filtering

Because final localized acceptances are a subset of Holm rejections, deterministic post-Holm safety filters cannot increase the probability of at least one false final localized acceptance.

### Proposition F — empirical outside-role safety

For every accepted localized deviation, recorded Selector and Probe outside-role SSE satisfy FULL <= REDUCED + `1e-10`. This is an empirical held-out property, not a population guarantee.

## 16. Claim boundaries

Do not claim:

- first federated symbolic regression;
- first shared/task-specific symbolic regression;
- first noise-robust symbolic regression;
- first uncertainty-aware symbolic regression;
- first selective-inference symbolic regression;
- causal role discovery;
- differential privacy or cryptographic privacy;
- universal symbolic recovery;
- exact F calibration on arbitrary external noise distributions.

The candidate novelty claim is narrower:

> federated set-conditional symbolic discovery with explicit shared/localized scope decomposition, sequential independent structural certification, family-wise multiplicity control, additive sufficient-statistic equivalence, and outside-role safety.

This claim must be re-audited before manuscript submission.

## 17. Primary ablations

Every fresh Phase-3 condition runs four primary methods.

### 17.1 Frozen v11

Unmodified comparator.

### 17.2 SCR-only

- use Discovery candidate nomination;
- use new Selector SCR to obtain shared structure;
- pass that shared structure to the predecessor v11 localized path;
- do not change predecessor localized scientific thresholds or acceptance logic.

Purpose: isolate shared-core correction.

### 17.3 NCEE-only

- retain the predecessor v11 ordinary shared structure exactly;
- replace localized role construction and final localized certification with the new Discovery -> Selector -> Probe NCEE path.

Purpose: isolate noise-calibrated localized certification.

### 17.4 Full SCSV-NCSC

Use SCR shared structure plus NCEE localized certification.

Ablations must share common candidate/statistic primitives so that differences reflect scientific mechanisms rather than duplicated implementation.

## 18. Engineering-before-science implementation epochs

### 18.1 Phase 3A — refactor/parity only

No new scientific decisions.

- extract reusable packet/statistic code;
- cache deterministic quantities;
- preserve frozen v11 decisions;
- run predecessor tests;
- verify centralized/federated numerical equivalence on deterministic fixtures;
- use only deterministic fixtures and engineering seed `29001`.

Do not regenerate `291xx` or `292xx` conditions.

### 18.2 Phase 3B — v12 scientific implementation

Only after Phase-3A parity is sealed:

- implement SCR;
- implement NCEE;
- implement Holm/BH;
- implement sequential split firewalls;
- implement ablation composition;
- implement diagnostics and study harness.

## 19. Package architecture

```text
src/fedfalsify/
    sufficient_stats.py
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

tests/
    test_sufficient_stats.py
    test_nested_tests.py
    test_multiple_testing.py
    test_shared_recertification.py
    test_role_localization_v12.py
    test_localized_certification.py
    test_scsv_v12.py
    test_phase3_seed_firewall.py
    test_centralized_equivalence.py
```

The Colab notebook remains one cell, but only installs a pinned commit and calls tested package APIs.

## 20. Safe performance optimization

After parity tests exist:

- build partitions/folds/packets once per condition;
- cache client Gram/cross-response/support values;
- cache nested-model rank/SSE quantities;
- avoid candidate-invariant recomputation inside candidate loops;
- separate method runtime from reporting/checkpoint time;
- use atomic per-condition checkpoint records plus periodic consolidation.

No optimization is accepted before regression/equivalence tests prove scientific parity.

## 21. Seed firewall

- `29001`: predecessor engineering/parity only;
- `29101--29105`: spent Phase 1;
- `29201--29205`: spent Phase 2;
- `29300`: reserved Phase-3 engineering smoke;
- `29301--29310`: reserved Phase-3 fresh development, untouched;
- `11001+`: reserved final confirmation, untouched.

A first run using any `29301--29310` seed permanently spends the full fresh Phase-3 block.

This specification does **not** authorize fresh Phase-3 development.

## 22. Fresh development matrix after later authorization

Use the frozen v10/v11 grammar and condition geometry with ten fresh seeds `29301--29310`:

- `1,200` matched conditions;
- four primary methods per condition;
- `4,800` primary rows.

The matrix keeps the existing families, K values, balance profiles, role profiles, and noise ratios.

## 23. Prospective development gate

Full SCSV-NCSC must satisfy all gates against matched v11:

- `1,200` unique conditions / `4,800` primary rows;
- zero integrity failures;
- zero frozen-v11 branch-parity failures;
- overall exact gain >= `+0.03`;
- seed-cluster bootstrap 95% CI lower bound for exact gain > `0`;
- deviation precision >= `0.99`;
- deviation recall >= `0.94`;
- shared precision >= `0.975`;
- shared recall >= `0.98`;
- null spurious localized acceptance <= `0.02`;
- null spurious shared acceptance <= `0.02`;
- exact-harm rate relative to v11 successes <= `0.01`;
- every main-family true-deviation recovery >= `0.92`;
- K=4 recovery >= `0.90`;
- K=8 recovery >= `0.93`;
- K=16 recovery >= `0.95`;
- high-noise main true-deviation recovery >= `0.90`;
- high-noise overall exact gain over v11 >= `+0.05`;
- dual-role recovery >= `0.90`;
- weak-source recovery >= `0.90`;
- median communication ratio vs v11 <= `1.25`;
- median method-runtime ratio vs v11 <= `1.50`.

All criteria are conjunctive. Secondary metrics cannot override a failed gate.

## 24. External validation after development GO

A development GO still does not authorize `11001+`.

Before final confirmation, separately freeze and run:

- FSL-GEP or the strongest compatible federated GP baseline;
- BFSR;
- local-only SR;
- centralized pooled SR;
- strong general SR (e.g. PySR/Operon where compatible);
- a noise-robust SR baseline such as NRSR where implementable;
- compatible multitask/shared-specific SR comparison;
- broader noise stress;
- client-scaling/partial-participation stress;
- at least one realistic multi-source/multi-environment dataset;
- assumption-robust inference analysis for heteroskedastic/non-Gaussian data;
- full SCR/NCEE/multiplicity ablations;
- communication and method-only runtime accounting.

Only a later separately frozen confirmation protocol may authorize `11001+` once.

## 25. Required documents before implementation planning

Human review must cover together:

1. this final-candidate specification;
2. `research/PHASE3_NOVELTY_AUDIT.md`;
3. `research/PHASE3_THEORY_SKETCH.md`.

Only after explicit human approval is an implementation plan authorized. No v12 implementation and no fresh-seed runner may be written before that approval.
