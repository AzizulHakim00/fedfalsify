# Phase 3 Theory Sketch: SCSV-NCSC

**Status:** Pre-implementation mathematical audit  
**Date:** 2026-09-06  
**Purpose:** verify that the proposed federated structural tests and sequential error-control claims are mathematically coherent before implementation.

## 1. Notation

For client `k`, let

- `X_k in R^(n_k x p)` be a fixed design matrix for a fixed ordered symbolic term set;
- `y_k in R^(n_k)` be the response;
- `G_k = X_k^T X_k`;
- `h_k = X_k^T y_k`;
- `q_k = y_k^T y_k`.

For a fixed client scope `A`, define

- `G_A = sum_{k in A} G_k`;
- `h_A = sum_{k in A} h_k`;
- `q_A = sum_{k in A} q_k`;
- `n_A = sum_{k in A} n_k`.

Let `X_A` and `y_A` denote the centralized row concatenation of clients in `A`.

Then by direct block multiplication:

`X_A^T X_A = G_A`,

`X_A^T y_A = h_A`,

`y_A^T y_A = q_A`.

These equalities are exact in real arithmetic.

## 2. Deterministic rank convention

All inferential routines must use one deterministic rank-revealing convention.

Proposed implementation rule:

1. obtain singular values of the symmetric Gram matrix or equivalent design factorization;
2. define numerical rank with a scale-aware machine-precision threshold fixed in code and unit-tested;
3. use the same convention in federated and centralized reference calculations;
4. never tune rank tolerance from benchmark outcomes;
5. never use a fitted ridge penalty to manufacture inferential rank.

A candidate structural test is admissible only if FULL increases effective rank by exactly one relative to REDUCED.

## 3. Theorem A: centralized equivalence of pooled least squares

### Statement

For a fixed ordered term set, fixed client scope, and identical deterministic generalized-inverse/rank convention, the least-squares solution reconstructed from aggregate sufficient statistics is the same as the solution obtained from centralized row concatenation, up to floating-point summation error.

### Proof sketch

The centralized normal equations are

`X_A^T X_A beta = X_A^T y_A`.

By additivity,

`X_A^T X_A = G_A`

and

`X_A^T y_A = h_A`.

Therefore centralized and federated calculations solve the same linear system with the same deterministic generalized-inverse convention.

The minimized SSE can be written as

`SSE(beta) = q_A - 2 beta^T h_A + beta^T G_A beta`.

Because `q_A`, `h_A`, `G_A`, and `beta` are the same mathematical quantities, the minimized SSE is also identical in exact arithmetic.

### Implementation consequence

A unit test must compare federated and centralized coefficients, rank, and SSE on deterministic matrices including:

- full-rank designs;
- exactly rank-deficient designs;
- near-collinear designs under the fixed rank convention;
- multiple-client decompositions of one centralized matrix.

## 4. Theorem B: centralized equivalence of partial nested F tests

### Setup

Let REDUCED and FULL be fixed nested symbolic term sets for the same fixed client scope, with FULL containing exactly one additional identifiable structural degree of freedom.

Let

- `SSE_R` be minimized REDUCED SSE;
- `SSE_F` be minimized FULL SSE;
- `r_F` be effective FULL rank;
- `N` be total observations in scope.

Define

`F = ((SSE_R - SSE_F) / 1) / (SSE_F / (N - r_F))`.

### Statement

The federated statistic reconstructed from summed client sufficient statistics equals the centralized statistic from concatenated rows, up to floating-point error.

### Proof sketch

By Theorem A, federated and centralized calculations produce the same REDUCED and FULL minimized SSE values and effective ranks. Substitution into the deterministic F-statistic expression gives the same F value. The same reference distribution therefore gives the same p-value.

## 5. Statistical calibration under the frozen synthetic benchmark

The frozen v10/v11 generator adds Gaussian noise using one pooled `noise_std` shared across all clients in a generated condition. Thus within a condition the benchmark uses independent homoskedastic Gaussian observation noise.

Conditional on a fixed FULL/REDUCED design and the benchmark model assumptions, the classical nested-model F test is aligned with the data-generating process.

This supports a clean synthetic-development claim.

It does **not** justify claiming exact F calibration on arbitrary external data with heteroskedasticity, dependence, heavy tails, or misspecification. External validation must treat this as an assumption and later consider robust/permutation/bootstrap alternatives through a separately frozen protocol.

## 6. Proposition C: independent shared-core certification

### Data-use sequence

Discovery `D` nominates the ordinary candidate family. Selector `S` is not used during nomination.

Conditional on the nominated family from `D`, shared-core p-values are computed only on `S`.

### Claim

If each Selector null p-value is valid conditional on the frozen Discovery-nominated family, Holm step-down at `alpha_shared` strongly controls the probability of at least one false shared rejection in that tested family at no more than `alpha_shared`, without requiring independence among p-values.

### Why the conditional framing matters

The candidate family is adaptive with respect to Discovery, but not Selector. Therefore the family can be treated as fixed when conditioning on Discovery. The inferential claim is about Selector error control for that frozen family, not about unconditional selective inference on Discovery.

## 7. Role discovery is explicitly exploratory

Localized role construction uses Discovery client-level p-values with BH `q_role = 0.10` only to form a provisional role.

No theorem in Phase 3 will interpret these BH-selected clients as individually confirmed effects.

The reasons are deliberate:

- localized candidates were nominated using Discovery;
- shared structure was selected using Selector and then supplied back to the Discovery role stage;
- role construction is hypothesis generation for later untouched Probe certification.

Therefore role-stage p-values are ranking/discovery evidence, not the paper's final frequentist guarantee.

## 8. Proposition D: untouched-Probe localized certification

### Sigma-field formulation

Let `H_DS` denote all information used before Probe:

- Discovery candidate bank;
- Selector-certified shared structure;
- Discovery role client IDs;
- Selector role/safety screening;
- expected candidate sign;
- surviving localized candidate family.

The protocol requires that Probe `P` not influence any component of `H_DS`.

Conditional on `H_DS`, the Probe localized hypotheses are fixed.

### Claim

Under valid Probe null p-values conditional on `H_DS`, Holm step-down at `alpha_dev` strongly controls the probability of at least one false Probe rejection in the localized hypothesis family at no more than `alpha_dev`.

### Important implementation requirement

No code path may:

- alter role membership after reading Probe;
- add a candidate after reading Probe;
- alter the shared structure after reading Probe;
- choose a different hypothesis family based on Probe outcomes.

Tests must explicitly firewall these behaviors.

## 9. Proposition E: post-Holm deterministic safety filtering preserves FWER

Let `R_Holm` be the set of localized hypotheses rejected by Holm on Probe.

Let `A_final` be the final operational localized set after requiring additional deterministic conditions such as:

- sign agreement;
- median role gain > 0;
- pair/structure invariance;
- outside-role non-degradation;
- capacity/ambiguity rules.

The protocol requires

`A_final subseteq R_Holm`.

The event

`{A_final contains at least one true null}`

is therefore a subset of

`{R_Holm contains at least one true null}`.

Hence

`P(any false final localized acceptance) <= P(any false Holm rejection) <= alpha_dev`.

This argument is one reason Holm/FWER is preferred over making an FDR claim after arbitrary post-rejection filtering.

## 10. Proposition F: empirical outside-role non-degradation

For a fixed recorded outside-role client set `O`, the implementation computes aggregate held-out SSE for FULL and REDUCED.

The predecessor safety rule is

`SSE_FULL <= SSE_REDUCED + 1e-10`.

If this deterministic inequality is required on Selector and Probe for an accepted candidate, then the stored evidence establishes non-degradation on those observed outside-role splits, subject to the numerical tolerance.

This is an empirical held-out property only. It is not a guarantee of population-level non-harm or causal invariance.

## 11. Shared-core capacity and FWER

The predecessor shared cap is `6` total terms including intercept, i.e. at most `5` non-intercept shared terms.

If more than five non-intercept terms are Holm-rejected on Selector, Phase 3 keeps only the five smallest Holm-adjusted p-values with deterministic catalog tie-breaking.

Because the capacity-selected operational shared set is a subset of Holm rejections, this truncation does not increase the event probability of at least one false operational shared term relative to the Holm family.

However, truncation may reduce power and can change the best refitted shared model. The paper should report capacity-trigger frequency as a diagnostic.

## 12. Why partial nested tests are preferred over frozen-coefficient residual tests

A fixed-coefficient residual test can confound two phenomena:

1. the candidate contributes unique structural information;
2. the reference coefficients are imperfect on the evaluation partition.

The proposed partial test re-estimates nuisance coefficients in both FULL and REDUCED while changing only the candidate term's structural inclusion.

Thus the null hypothesis is closer to:

> conditional on the known shared basis, the candidate contributes no additional linear coefficient on this scope.

This does not make the grammar-selection problem trivial, but it better isolates structural evidence from coefficient transport error.

## 13. Interaction between shared certification and localized discovery

The sequential design is:

1. Discovery nominates ordinary and localized candidates;
2. Selector certifies shared structure;
3. Discovery constructs localized roles conditional on the Selector-certified shared **structure**;
4. Selector screens those role hypotheses for safety/non-final evidence;
5. Probe performs final localized tests.

The nested tests depend on shared **structure**, not on importing one frozen coefficient vector from another split. Nuisance shared coefficients are re-estimated within each evaluation partition.

Therefore the shared numerical refit used for the final operational model is not part of the inferential nested-test definition.

This distinction must be reflected in implementation APIs: structural test functions consume term sets and packets, not an externally fitted coefficient vector.

## 14. Ablation interpretation

### SCR-only

Use the new independent Selector shared-core certification, then apply the predecessor v11 localized logic using the SCR-certified shared structure as its core structure. All other localized scientific thresholds remain v11-frozen.

This measures the effect of allowing shared-core correction while preserving the predecessor localized certificate.

### NCEE-only

Keep the predecessor v11 ordinary shared structure exactly, but replace role discovery/final localized certification with the new Discovery -> Selector -> Probe NCEE path.

This measures the effect of localized noise calibration while preserving the predecessor shared structure.

### Full SCSV-NCSC

Use SCR shared structure plus NCEE localized certification.

Ablation code must share common primitives rather than silently reimplementing subtly different candidate families.

## 15. Identified assumptions and failure modes

The mathematical guarantees rely on assumptions that must be explicit in the manuscript:

- fixed finite grammar within each study condition;
- deterministic split protocol;
- untouched Probe until localized hypotheses are frozen;
- valid nested-model p-values under the synthetic noise model;
- correct effective-rank accounting;
- no hidden outcome-dependent candidate expansion;
- no benchmark-truth use in inference;
- no post-hoc alpha/q changes.

Known threats include:

- correlated symbolic bases and rank ambiguity;
- candidate-set truncation due to the shared cap;
- small localized scopes;
- external-data heteroskedasticity or dependence;
- model misspecification when the true mechanism lies outside the frozen grammar;
- multiple localized deviations whose roles or terms are strongly collinear.

These cases require explicit diagnostics/abstention rather than silent regularization.

## 16. Required mathematical tests before v12 integration

Before `scsv_v12.py` is allowed to call the new test engine, the following tests must pass:

1. centralized/federated coefficient equivalence;
2. centralized/federated SSE equivalence;
3. centralized/federated effective-rank equivalence;
4. centralized/federated nested-F equivalence;
5. full-rank one-term analytic example;
6. exact-collinearity abstention;
7. near-collinearity deterministic-rank behavior;
8. Holm known-vector examples;
9. BH known-vector examples;
10. post-Holm subset property;
11. Probe hypothesis-family immutability test;
12. outside-role `1e-10` tolerance regression test.

## 17. Theory decision

The theoretical core is coherent enough to continue to implementation planning **after human approval of the revised design**, provided the code follows the sequential split firewall exactly.

The strongest formal claims to pursue are:

- algebraic centralized equivalence of sufficient-statistic least squares;
- algebraic centralized equivalence of fixed-scope nested F tests;
- conditional Holm FWER for independent Selector shared certification;
- conditional Holm FWER for untouched-Probe localized certification;
- preservation of FWER under deterministic post-Holm subset filtering;
- empirical held-out outside-role non-degradation.

No theorem should claim universal symbolic recovery, causal client roles, privacy, or exact external-data calibration.
