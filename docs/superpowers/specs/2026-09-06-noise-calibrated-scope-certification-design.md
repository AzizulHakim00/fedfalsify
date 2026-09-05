# FedFalsify Phase 3 Design: Noise-Calibrated Scope Certification

**Design status:** Approved architecture, written specification pending user review before implementation  
**Working method name:** **FedFalsify v12: Set-Conditional Structural Verification with Noise-Calibrated Scope Certification (SCSV-NCSC)**  
**Base scientific source:** `e58ff85a93a7498a6220a3032d153c02290de352`  
**Design branch:** `research/phase3-noise-calibrated-scope-certification`  
**Date:** 2026-09-06

## 1. Purpose

Phase 3 is not another PQCR variant. Phase 1 and Phase 2 showed that post-quarantine coefficient refitting can occasionally recover real conditional structure, but it does not solve the dominant structural-recovery ceiling. DR-PQCR-v2 restored the v11 exact-recovery level by preserving v11-certified deviations, yet it produced no net exact-recovery gain and introduced two false PQCR-only rescues for one true rescue.

The next method therefore targets the mechanisms that remain after v11, PQCR-v1, and DR-PQCR-v2:

1. high-noise loss of power in conditional certification; and
2. high-noise errors in the supposedly immutable shared/core structure.

The scientific objective is to recover a **shared symbolic mechanism plus sparse client-localized deviations** using data-local sufficient statistics, while explicitly calibrating structural evidence to observed noise and preserving strict false-structure control.

## 2. Frozen evidence motivating the redesign

The redesign is motivated by sealed evidence, not by post-hoc adjustment of a failed gate.

### Phase-2 facts the new design must explain

- v11 exact recovery: `0.8300`;
- DR-PQCR-v2 exact recovery: `0.8300`;
- DR-v11 exact gain: `0.0000` on every Phase-2 seed;
- v11 deviation TP/FP/FN: `461/1/59`;
- DR-PQCR-v2 deviation TP/FP/FN: `462/3/58`;
- all `59/59` v11 true-deviation misses occurred at noise ratio `0.30`;
- `56/59` missed true deviations were already in the high-recall candidate bank;
- v11 true-deviation rejections decomposed into `26` effect-role localization failures, `25` pooled-evidence failures, and `8` outside-role failures;
- among `102` v11 non-exact conditions, `88` contained a shared/core error, including `46` shared/core-only failures;
- `87/88` shared/core-error conditions occurred at noise ratio `0.30`;
- DR-PQCR-v2 generated only three PQCR-only rescues, all at noise `0.30`, with one true structural rescue and two false structural additions.

These facts imply that candidate generation is already high recall. The dominant problem is **scope and structural evidence under noise**, not term invention.

## 3. Research question

Given federated clients with related but non-identical symbolic mechanisms, can a method recover:

- an invariant/shared symbolic core;
- sparse client-localized conditional mechanisms; and
- the subset of clients supporting each localized mechanism,

while maintaining strong null safety and false-structure control as observation noise increases?

## 4. Primary hypothesis

> **H3:** Replacing raw fold-vote and unscaled pooled-evidence decisions with noise-calibrated sufficient-statistic tests, while re-certifying shared/core structure instead of freezing it, will improve exact structural recovery under high noise without materially increasing false shared or conditional structure.

The hypothesis contains two separable mechanisms:

- **NCEE:** Noise-Calibrated Effect Evidence for localized deviations.
- **SCR:** Shared-Core Re-certification for ordinary/shared terms.

The full SCSV-NCSC method is `SCR + NCEE`. These mechanisms must be independently ablated.

## 5. Non-goals and claim boundaries

Phase 3 will not:

- retune PQCR or DR-PQCR thresholds;
- reuse `29101--29105` or `29201--29205` for method selection or prospective validation;
- touch the reserved `11001+` final-confirmation namespace;
- claim differential privacy, secure aggregation, or cryptographic confidentiality merely because raw rows are not transmitted;
- claim causal interpretation of recovered client roles;
- claim to be the first federated symbolic-regression method;
- broaden the symbolic grammar merely to improve benchmark recovery;
- alter the final method after fresh Phase-3 development outcomes are inspected.

PQCR-v1 and DR-PQCR-v2 remain frozen historical ablations, not the Phase-3 headline method.

## 6. Structural model

For client `k`, observation `i`, and feature vector `x_ki`, the target decomposition is

`y_ki = f_0(x_ki) + sum_m z_km * delta_m * phi_m(x_ki) + epsilon_ki`,

where:

- `f_0` is the shared symbolic mechanism;
- `phi_m` is a declared candidate localized mechanism;
- `z_km in {0,1}` identifies whether client `k` belongs to the mechanism's role;
- `delta_m` is the common coefficient for that localized role; and
- `epsilon_ki` is observation noise.

The Phase-3 development grammar and source-term provenance remain unchanged from the frozen v11 benchmark family.

## 7. Statistical foundation

### 7.1 Fixed-reference one-term sufficient-statistic test

For a fixed reduced/reference model `R`, candidate basis column `z`, and fixed client scope `S`, define on a data partition:

- residual `r = y - R(x)`;
- score `U = z^T r`;
- information `I = z^T z`;
- reduced SSE `SSE_R = r^T r`;
- one-parameter estimate `beta_hat = U / (I + eps)`;
- minimized one-term full SSE `SSE_F = SSE_R - U^2 / (I + eps)`.

Across a fixed client scope, these statistics add:

- `U_S = sum_k U_k`;
- `I_S = sum_k I_k`;
- `SSE_R,S = sum_k SSE_R,k`;
- `N_S = sum_k N_k`.

When only the added coefficient is estimated on that evaluation partition and the reference coefficients are fixed, use

`F = ((SSE_R,S - SSE_F,S) / 1) / (SSE_F,S / max(N_S - 1, 1))`.

The `F(1, N_S-1)` upper-tail probability is the noise-calibrated structural p-value.

This test scales evidence by residual noise and is exactly reconstructible from additive sufficient statistics for a fixed reference and scope.

### 7.2 Joint nested test for shared-core candidates

Shared-core candidates are correlated, so SCR must not test each term only against an unrelated frozen marginal reference.

Let `C` be the complete ordinary/shared candidate set for the condition. Fit the joint candidate model from pooled discovery sufficient statistics. For each non-intercept term `t in C`, compare:

- FULL: joint model containing `t` and the other ordinary candidates;
- REDUCED: the same joint model with only `t` removed.

Use the standard one-degree-of-freedom nested-model F statistic with denominator degrees of freedom `N - p_full`.

This makes shared-term evidence **partial evidence conditional on the other ordinary candidates**, reducing false inclusion caused by correlated symbolic bases.

If the joint normal equations are rank-deficient, use a deterministic rank-revealing solve and mark non-identifiable terms as `SHARED-RANK-AMBIGUOUS`; do not resolve the ambiguity with tuned regularization.

### 7.3 Numerical policy

Machine-safety constants such as `1e-12` may prevent division by zero or negative SSE from floating-point cancellation. They are not scientific thresholds and must be centralized in one tested module.

## 8. Multiple-testing policy

Symbolic candidates are correlated. Uncorrected per-term p-values are not sufficient for final structural claims.

### 8.1 Shared/core discovery

Apply **Benjamini-Yekutieli (BY)** at `q_shared = 0.05` to the joint nested-discovery p-values for ordinary/shared candidates.

Because the v6 high-recall bank itself is discovery-adaptive, this BY step is treated as a **conservative multiplicity-adjusted discovery rule**, not as a formal finite-sample FDR theorem for the shared-core stage unless a later selective-inference proof is established.

### 8.2 Localized role discovery

Within each candidate deviation, apply **Benjamini-Hochberg (BH)** at `q_role = 0.10` across eligible clients' discovery p-values to form a high-recall candidate role.

This is an exploratory role-construction level. It is not a final structural acceptance level.

### 8.3 Final deviation certification

Apply **BY at `q_dev = 0.05`** across the independent held-out p-values for candidate deviation hypotheses in that condition.

No family-specific, noise-specific, seed-specific, or retrospectively selected q-values are permitted.

## 9. Shared-Core Re-certification (SCR)

The v11 ordinary/core anchor is no longer immutable.

### 9.1 Candidate set

The shared candidate set is fixed to:

- intercept `1`;
- ordinary terms already in the v6 discovery anchor; and
- ordinary terms present in the v6 high-recall response bank.

Exception/gated terms are not promoted to the ordinary shared core by SCR.

### 9.2 Selection

Using discovery data only:

1. fit the joint ordinary candidate model from pooled sufficient statistics;
2. compute one-term partial nested F tests;
3. apply BY `q_shared = 0.05`;
4. retain the intercept and BY-surviving identifiable ordinary terms.

Consequences:

- unsupported ordinary anchor terms may be removed;
- banked ordinary terms missed by the original anchor may be added;
- the intercept is always retained;
- the existing six-term shared cap remains frozen.

If more than six non-intercept shared terms survive, retain the deterministic six smallest BY-adjusted p-values, using canonical catalog order as the final tie-breaker.

### 9.3 Refit and freeze

Refit the selected shared structure on the complete discovery partition. The resulting provisional shared core is frozen before localized role construction or held-out deviation certification begins.

Selector/probe outcomes therefore cannot change the shared reference used by the deviation certificate.

## 10. Noise-Calibrated Effect Evidence (NCEE)

### 10.1 Candidate provenance

A localized exception candidate must:

- exist in the declared grammar;
- have a declared `source_term`; and
- satisfy weak structural heredity because its source is either operational in the re-certified shared core or present in the high-recall bank.

A source may remain provenance-only and is not inserted globally merely to enable its child.

### 10.2 Estimability

A gated/localized candidate is client-estimable only when:

- discovery active-row support is at least `10`; and
- candidate information `I > 1e-12`.

The support floor `10` is inherited from the previous total `8 training + 2 held-out active-row` estimability floor; it is not fitted from Phase-1 or Phase-2 outcomes.

### 10.3 Per-client discovery evidence

For every eligible client:

1. freeze the re-certified shared core;
2. compute the one-term discovery `beta_hat`, F statistic, and p-value;
3. apply BH `q_role = 0.10` across clients for that candidate.

The BH-supported clients form the provisional role.

### 10.4 Role admissibility

A localized role is admissible only when:

- at least one client is BH-supported;
- at least one outside-role client remains;
- role size is at most half of all clients;
- every BH-supported nonzero `beta_hat` has the same sign.

A supported coefficient with absolute value `<= 1e-12` is treated as sign-indeterminate. Any mixed or indeterminate supported signs produce `SCOPE-SIGN-AMBIGUOUS` and reject the role hypothesis.

If more than half of clients support a gated exception, classify it `GLOBAL-SCOPE-AMBIGUOUS` and reject it as a localized exception. Phase 3 does not reinterpret an exception-grammar term as a shared ordinary term.

### 10.5 Discovery direction

Aggregate the discovery sufficient statistics across the admissible role and record the sign of the discovery `beta_hat`. The **role identity, shared reference, and expected effect sign** are frozen before selector/probe certification.

The numerical coefficient itself is **not** frozen for the held-out F test; the held-out test estimates its own single added coefficient so that the nested F statistic is valid. This distinction is deliberate.

## 11. Independent held-out deviation certification

Selector and probe remain untouched during shared-core selection and role discovery.

For each fixed candidate role:

1. compute the fixed-reference sufficient statistics separately on selector and probe;
2. sum selector and probe sufficient statistics only after the role and expected sign are frozen;
3. estimate the one held-out candidate coefficient from the combined held-out statistics;
4. compute the one-degree-of-freedom combined held-out F p-value;
5. apply final BY `q_dev = 0.05` across candidate deviations;
6. require held-out coefficient sign to equal the frozen discovery sign;
7. require median role-client held-out raw gain to be positive;
8. require pair invariance;
9. require selector outside-role non-degradation;
10. require probe outside-role non-degradation.

Outside-role non-degradation means the inherited FULL candidate must not increase aggregate SSE relative to REDUCED on the recorded outside-role clients, using the exact numerical tolerance already pinned in the predecessor implementation.

The old raw pooled-delta boundary is not part of the primary NCEE decision. It remains available as a diagnostic/ablation value.

## 12. Final model refit

After shared and localized **structure** is accepted:

- refit final coefficients using the same predecessor policy for the full training information available to the method;
- do not use external test data or benchmark truth in the refit;
- record both discovery and held-out structural evidence separately from the final refitted coefficients.

Structural acceptance is never changed because a final coefficient refit improves NMSE.

## 13. Ambiguity and capacity rules

Retain the predecessor safety constraints:

- maximum operational localized exceptions: `2`;
- maximum final structure size: `10` including intercept;
- multiple accepted localized exceptions linked to one source trigger source ambiguity and are rejected;
- exceeding the localized-exception cap triggers global ambiguity and rejects the new exception set rather than choosing by benchmark outcome.

Shared and localized terms must be reported separately in diagnostics.

## 14. Theoretical targets

### Proposition A: centralized equivalence of fixed-scope evidence

For a fixed reference, candidate basis, and client scope, summing client sufficient statistics yields the same `beta_hat`, reduced SSE, minimized one-term full SSE, F statistic, and p-value as the corresponding calculation on centrally concatenated observations, up to floating-point summation error.

### Proposition B: centralized equivalence of joint shared nested tests

For the same fixed ordinary candidate set and rank convention, aggregation of client Gram/cross-response sufficient statistics yields the same pooled joint least-squares solution and one-term nested F statistics as centralized concatenation.

### Proposition C: data-local computation boundary

The server can execute these structural tests from aggregate sufficient statistics without directly receiving raw client rows. This is a data-local/communication property, not a DP or cryptographic privacy guarantee.

### Proposition D: final deviation FDR control

Conditional on the discovery-selected shared reference and client roles, valid held-out null p-values, and no held-out use in role construction, BY at `q_dev` controls expected false-discovery proportion among final deviation hypotheses under arbitrary dependence.

### Proposition E: empirical outside-role safety

For every accepted localized deviation, the selector and probe safety checks guarantee no recorded aggregate held-out SSE increase of FULL relative to REDUCED on the recorded outside-role sets, subject to the inherited numerical tolerance. This is an empirical held-out property, not a population theorem.

## 15. Software architecture

The algorithm must move out of giant notebook cells and into tested package modules.

```text
src/fedfalsify/
    sufficient_stats.py
    structural_tests.py
    multiple_testing.py
    shared_recertification.py
    role_localization.py
    scope_certification.py
    scsv_v12.py

studies/
    phase3_engineering.py
    phase3_development.py

colab/
    FedFalsify_Phase3_NCSC_OneCell.ipynb

tests/
    test_sufficient_stats.py
    test_structural_tests.py
    test_multiple_testing.py
    test_shared_recertification.py
    test_role_localization.py
    test_scope_certification.py
    test_scsv_v12.py
    test_phase3_seed_firewall.py
    test_centralized_equivalence.py
```

The Colab artifact remains one-cell for reproducibility, but the cell installs a pinned commit and calls tested package APIs rather than embedding the scientific implementation.

## 16. Engineering optimization requirements

### Mandatory safe optimizations

1. Build discovery folds/partitions and sufficient packets once per condition, not once per candidate.
2. Cache client-level `U`, `I`, SSE, support, and nested-model quantities for each fixed reference/candidate pair.
3. Derive pooled evidence, client gains, and outside safety from cached arrays rather than repeated packet-SSE calls.
4. Separate scientific method runtime from checkpoint/report-generation time.
5. Save atomic per-condition checkpoint records and periodically consolidate them, instead of rewriting a growing multi-megabyte CSV after every condition.
6. Preserve deterministic client, term, condition, and aggregation ordering.

### Optimization acceptance rule

No optimization is accepted merely because it is faster. Before scientific implementation uses it, regression tests must demonstrate frozen v11 structural parity and centralized/sufficient-statistic numerical equivalence.

## 17. Test strategy

### 17.1 Mathematical unit tests

Use deterministic arrays with known results to test:

- score `U` and information `I`;
- one-term coefficient estimate;
- reduced/full SSE identity;
- fixed-reference F statistic and p-value;
- joint nested-model F statistic;
- additive aggregation across clients;
- rank-deficient joint designs;
- zero-information candidates;
- near-zero residual variance.

### 17.2 Multiple-testing tests

Use fixed p-value vectors with known BH/BY outcomes, including ties, empty sets, all-null, all-significant, and canonical tie-breaking.

### 17.3 Structural engineering falsification cases

Hand-constructed cases must cover:

- clean shared term;
- missing shared term in the initial anchor;
- spurious shared anchor term;
- correlated ordinary candidates;
- clean one-client localized deviation;
- quarter-client localized deviation;
- dual localized deviations;
- weak-source/provenance-only child;
- high-noise true deviation;
- high-noise null candidate;
- mixed-sign role ambiguity;
- >50% global-scope ambiguity;
- outside-role degradation;
- capacity ambiguity.

These are engineering tests, not publication evidence.

### 17.4 Frozen predecessor parity

Before fresh Phase-3 seeds are touched:

- official v11 tests must pass;
- any refactored v11 path must match the frozen v11 implementation on engineering conditions;
- Phase-1/Phase-2 evidence must not be regenerated or relabeled;
- any read of spent evidence is descriptive only.

## 18. Phase-3 ablation design

Fresh development must identify which mechanism causes any gain.

Primary matched methods:

1. **v11 frozen comparator**;
2. **NCEE-only:** frozen v11 shared/core behavior + noise-calibrated localized certification;
3. **SCR-only:** shared-core re-certification + frozen v11 localized certification;
4. **SCSV-NCSC full:** SCR + NCEE.

PQCR-v1 and DR-PQCR-v2 may appear only in a separate historical table and are not Phase-3 gate comparators.

No ablation may be used to redefine thresholds after fresh outcomes are visible.

## 19. Seed firewall

Spent:

- `29001`: predecessor engineering/parity use only;
- `29101--29105`: Phase-1 development spent;
- `29201--29205`: Phase-2 development spent.

Reserved Phase-3 engineering-only:

- `29300`.

Reserved Phase-3 fresh development:

- `29301, 29302, 29303, 29304, 29305, 29306, 29307, 29308, 29309, 29310`.

Reserved final confirmation:

- `11001+`, untouched.

The first execution of any fresh `29301--29310` condition permanently spends all ten Phase-3 development seeds, regardless of outcome. They are forbidden during debugging, threshold choice, or mathematical tests.

## 20. Fresh development matrix

Retain the predecessor structural grammar and factors:

- quadratic, linear, trigonometric, and interaction localized families;
- `K = 4, 8, 16`;
- single and quarter roles where admissible;
- balanced and imbalanced client-size profiles;
- noise ratios `0.10` and `0.30`;
- null and anchor-contamination null families;
- weak-source and dual-role families.

Ten prospective seeds produce **1,200 matched conditions**. Each condition runs the four frozen Phase-3 methods on the same generated data.

## 21. Endpoints

### Primary

Exact recovery of the full symbolic term set.

### Secondary

- shared TP/FP/FN, precision, recall;
- deviation TP/FP/FN, precision, recall;
- exact repairs/harms relative to v11;
- role-set recovery where truth is defined;
- high-noise exact, shared, and deviation recovery;
- family recovery;
- K-specific recovery;
- null spurious shared/deviation acceptance;
- test NMSE;
- runtime and communication;
- structural p/q-value calibration diagnostics.

Predictive NMSE is secondary. Lower NMSE must not be represented as structural correctness when the symbolic structure is wrong.

## 22. Prospective GO/NO-GO gate

The full SCSV-NCSC method must satisfy **all** of the following before any independent-validation stage is authorized:

1. exactly 1,200 matched fresh conditions and zero implementation/integrity failures;
2. overall exact-recovery gain vs v11 `>= +0.03`;
3. seed-cluster bootstrap 95% CI lower bound for exact gain `> 0`;
4. paired discordance favors SCSV-NCSC, with exact two-sided McNemar/binomial `p < 0.05` as supportive evidence;
5. pooled deviation precision `>= 0.99`;
6. pooled deviation recall `>= 0.94`;
7. pooled shared precision `>= 0.975`;
8. pooled shared recall `>= 0.98`;
9. null spurious deviation acceptance `<= 0.02`;
10. null spurious shared-term acceptance `<= 0.02`;
11. exact-harm rate relative to v11 `<= 0.01` and net exact repairs strictly positive;
12. each main family all-true-deviation recovery `>= 0.90`;
13. `K=4` recovery `>= 0.90`;
14. `K=8` recovery `>= 0.90`;
15. `K=16` recovery `>= 0.95`;
16. high-noise main deviation recovery `>= 0.90`;
17. high-noise overall exact recovery improves over v11 by `>= +0.05`;
18. dual-role recovery `>= 0.90`;
19. weak-source recovery `>= 0.90`;
20. median communication ratio vs v11 `<= 1.25`;
21. median runtime ratio vs v11 `<= 1.50`.

No single favorable metric overrides a failed gate.

A failure gives `PHASE3-DEVELOPMENT-NO-GO`. The ablations may diagnose the failure but may not be used to redefine the full method on the same fresh seeds.

## 23. Statistical reporting

Publication-quality reporting must include:

- per-seed rates;
- seed-cluster bootstrap confidence intervals;
- paired discordant counts and exact McNemar/binomial analysis;
- Wilson intervals for absolute recovery rates;
- raw TP/FP/FN counts;
- calibration/null diagnostics for structural p/q-values where meaningful;
- clustered interpretation of conditions nested within seeds.

The 1,200 conditions must not be treated as 1,200 independent replicates for the primary uncertainty claim.

## 24. Literature and novelty audit before publication claims

Before writing “first,” “unique,” or equivalent novelty language, perform and archive a systematic search covering at least:

- federated symbolic regression;
- distributed symbolic regression;
- Bayesian federated symbolic regression;
- federated system identification;
- multitask/shared-specific symbolic regression;
- noise-robust symbolic regression;
- uncertainty-calibrated symbolic regression;
- structure-selection/FDR in symbolic regression.

Search Google Scholar, Crossref/Semantic Scholar or Scopus/Web of Science where available, IEEE Xplore, ACM DL, Springer, ScienceDirect, arXiv, and major ML proceedings. Record query, date, inclusion/exclusion reason, and closest competing mechanism.

The target novelty claim is not “federated symbolic regression.” It is:

> **Federated set-conditional symbolic discovery that distinguishes shared symbolic structure from sparse client-localized structural deviations using noise-calibrated, independently certified sufficient-statistic evidence.**

This wording remains provisional until the formal literature audit is complete.

## 25. External-validation path after a GO

A Phase-3 GO does not authorize final confirmation immediately.

The next separately frozen stage should add:

- reproducible federated SR baselines where code/assumptions permit;
- local-only and pooled-centralized references;
- a strong centralized SR package such as PySR or Operon where grammar compatibility permits;
- an appropriate noise-robust SR comparator;
- stronger noise levels beyond `0.30`;
- partial participation and missingness stress tests;
- larger client counts;
- at least one realistic multi-source or naturally partitioned benchmark with defensible structural or semi-synthetic truth.

Only after that stage is frozen and successful should `11001+` be touched once.

## 26. Implementation order after written-spec approval

After the user approves this written specification, implementation planning must proceed in this order:

1. refactor/parity infrastructure;
2. sufficient-statistic and nested-F modules;
3. BH/BY module;
4. SCR;
5. NCEE role construction;
6. held-out deviation certification;
7. final refit and diagnostics;
8. ablation wrappers;
9. engineering falsification suite;
10. performance profiling and caching;
11. frozen Phase-3 protocol plus explicit development authorization;
12. only then execute `29301--29310`.

No fresh Phase-3 development run is authorized by this design document alone.
