# FedFalsify Phase 3 Design: Noise-Calibrated Scope Certification

**Design status:** Approved architecture, specification pending user review before implementation  
**Working method name:** **FedFalsify v12: Set-Conditional Structural Verification with Noise-Calibrated Scope Certification (SCSV-NCSC)**  
**Base scientific source:** `e58ff85a93a7498a6220a3032d153c02290de352`  
**Branch:** `research/phase3-noise-calibrated-scope-certification`  
**Date:** 2026-09-06

## 1. Purpose

Phase 3 is not another PQCR variant. Phase 1 and Phase 2 showed that post-quarantine coefficient refitting can occasionally recover real conditional structure, but it does not solve the dominant structural-recovery ceiling. DR-PQCR-v2 restored the v11 exact-recovery level by preserving v11-certified deviations, yet it produced no net exact-recovery gain and introduced two false PQCR-only rescues for one true rescue.

The next method therefore targets the failure mechanism that remains after v11, PQCR-v1, and DR-PQCR-v2:

1. high-noise loss of power in conditional certification; and
2. high-noise errors in the supposedly immutable shared/core structure.

The scientific objective is to recover a **shared symbolic mechanism plus sparse client-localized deviations** using data-local sufficient statistics, while explicitly calibrating structural evidence to observed noise and preserving strict false-structure control.

## 2. Evidence motivating the redesign

The redesign is motivated by frozen evidence, not by a desire to rescue a failed gate post hoc.

### Phase-2 facts that the new design must explain

- v11 exact recovery: `0.8300`;
- DR-PQCR-v2 exact recovery: `0.8300`;
- DR-v11 exact gain: `0.0000` on every Phase-2 seed;
- v11 deviation TP/FP/FN: `461/1/59`;
- DR-PQCR-v2 deviation TP/FP/FN: `462/3/58`;
- all `59/59` v11 true-deviation misses occurred at noise ratio `0.30`;
- `56/59` missed true deviations were already present in the high-recall candidate bank;
- v11 true-deviation rejections decomposed into `26` effect-role localization failures, `25` pooled-evidence failures, and `8` outside-role failures;
- among `102` v11 non-exact conditions, `88` contained a shared/core error, including `46` shared/core-only failures;
- `87/88` shared/core-error conditions occurred at noise ratio `0.30`;
- DR-PQCR-v2 generated only three PQCR-only rescues, all at noise `0.30`, with one true structural rescue and two false structural additions.

These facts imply that candidate generation is already high recall. The dominant problem is not term invention. The dominant problem is **scope and structural evidence under noise**.

## 3. Research question

Given federated clients with related but non-identical symbolic mechanisms, can a method recover:

- an invariant/shared symbolic core;
- sparse client-localized conditional mechanisms;
- the subset of clients supporting each localized mechanism;

while maintaining strong null safety and false-structure control when observation noise increases?

## 4. Primary hypothesis

> **H3:** Replacing raw fold-vote and unscaled pooled-evidence decisions with noise-calibrated sufficient-statistic tests, while re-certifying the shared/core structure instead of freezing it, will improve exact structural recovery under high noise without materially increasing false shared or conditional structure.

The hypothesis has two separable mechanisms:

- **NCEE:** Noise-Calibrated Effect Evidence for localized deviations.
- **SCR:** Shared-Core Re-certification for ordinary/shared terms.

The full SCSV-NCSC method is `NCEE + SCR`. These components must be independently ablated.

## 5. Non-goals and claim boundaries

Phase 3 will not:

- retune PQCR or DR-PQCR thresholds;
- reuse `29101--29105` or `29201--29205` for method selection or prospective validation;
- touch the reserved `11001+` final-confirmation namespace;
- claim differential privacy, secure aggregation, or formal confidentiality merely because raw rows are not transmitted;
- claim causal interpretation of recovered client roles;
- claim to be the first federated symbolic-regression method;
- broaden the symbolic grammar merely to improve benchmark recovery;
- change the final method after fresh Phase-3 development evidence is inspected.

PQCR-v1 and DR-PQCR-v2 remain frozen historical ablations, not the main Phase-3 method.

## 6. Structural model

For client `k`, observation `i`, and feature vector `x_ki`, the target decomposition is

`y_ki = f_0(x_ki) + sum_m z_km * delta_m * phi_m(x_ki) + epsilon_ki`,

where:

- `f_0` is the shared symbolic mechanism;
- `phi_m` is a declared candidate localized mechanism;
- `z_km in {0,1}` identifies whether client `k` belongs to the mechanism's role;
- `delta_m` is the role-common deviation coefficient;
- `epsilon_ki` is observation noise.

The benchmark grammar and source-term provenance remain unchanged from the frozen v11 family unless a future separately approved protocol explicitly expands them.

## 7. Core statistical primitive: one-degree-of-freedom sufficient-statistic test

The principal Phase-3 change is to scale evidence by estimated residual noise instead of relying mainly on raw positive-fold counts or an unstandardized pooled boundary.

For a fixed reduced/reference model `R`, candidate basis column `z`, and a fixed client scope `S`, define on a data partition:

- residual `r = y - R(x)`;
- score `U = z^T r`;
- information `I = z^T z`;
- reduced SSE `SSE_R = r^T r`;
- added-term estimate `beta_hat = U / (I + eps)`;
- full SSE `SSE_F = SSE_R - U^2 / (I + eps)`.

For aggregated scope `S`, the sufficient statistics add exactly across clients:

- `U_S = sum_k U_k`;
- `I_S = sum_k I_k`;
- `SSE_R,S = sum_k SSE_R,k`;
- `N_S = sum_k N_k`.

Under the fixed-reference Gaussian-noise model, the added one-parameter term is tested by

`F = ((SSE_R,S - SSE_F,S) / 1) / (SSE_F,S / max(N_S - 1, 1))`.

The corresponding `F(1, N_S-1)` tail probability is the **noise-calibrated structural p-value**.

This choice is deliberate:

- noise magnitude enters through residual variance;
- higher noise therefore reduces certainty instead of arbitrarily flipping a fixed raw-gain threshold;
- the statistic is computable from federated sufficient statistics;
- for a fixed reference and fixed scope, aggregation is algebraically equivalent to computing the same test on concatenated rows;
- no raw client observation must be sent to the server.

Numerical guards must be deterministic and limited to machine-safety constants such as `1e-12`; they are not tunable scientific thresholds.

## 8. Multiple-testing policy

Candidate symbolic terms are correlated. Final structural inclusion therefore must not rely on uncorrected per-term p-values.

### Shared/core terms

Shared-term discovery uses **Benjamini-Yekutieli (BY)** false-discovery-rate control at `q_shared = 0.05` across the ordinary/shared candidate terms in one dataset condition. BY is chosen because it controls FDR under arbitrary dependence, which is safer than assuming independent symbolic basis terms.

### Localized role discovery

Client membership for a candidate deviation is an exploratory discovery step that is independently certified later. Within each candidate, client-level discovery p-values use **Benjamini-Hochberg (BH)** at `q_role = 0.10` to form a high-recall candidate role.

The `0.10` role level is fixed prospectively as a discovery level; it is not a final acceptance level.

### Final deviation certification

Final held-out deviation p-values use **BY at `q_dev = 0.05`** across the candidate deviation hypotheses for the condition.

No family-specific q-values, noise-specific q-values, seed-specific q-values, or post-hoc threshold search are permitted.

## 9. Shared-Core Re-certification (SCR)

The v11 ordinary/core anchor must no longer be immutable.

### 9.1 Shared candidate set

The shared candidate set is fixed to:

- intercept `1`;
- ordinary terms already in the v6 discovery anchor; and
- ordinary terms present in the v6 high-recall response bank.

Exception/gated terms are not promoted to the shared core by SCR.

### 9.2 Shared evidence

For every ordinary candidate term, construct a pair differing only in that term and compute the all-client discovery sufficient-statistic F test.

Apply BY `q_shared = 0.05` across the ordinary candidates.

A non-intercept ordinary term is operational in the provisional shared core if and only if it survives this shared evidence rule and all structural invariants pass.

Consequences:

- unsupported ordinary anchor terms may be removed;
- banked ordinary terms omitted by the original anchor may be added;
- the intercept is always retained;
- the existing six-term shared cap remains frozen.

If more than six nontrivial shared terms survive, keep the deterministic six with smallest BY-adjusted p-values, using canonical catalog order as the final tie-breaker. This is a capacity rule, not a tuned scientific parameter.

### 9.3 Refit

After shared structure is selected using discovery data only, refit its coefficients on the full discovery partition. The resulting provisional shared core is then frozen for localized-deviation discovery and independent held-out certification.

This ordering is essential: selector/probe data must not be used to choose the shared reference that later serves as the deviation reference.

## 10. Noise-Calibrated Effect Evidence (NCEE) for localized deviations

### 10.1 Candidate provenance

An exception candidate must:

- exist in the declared grammar;
- have a declared `source_term`; and
- satisfy weak structural heredity because its source is either operational in the re-certified shared core or present in the high-recall bank.

A source may remain provenance-only. It is not inserted globally merely to permit a child mechanism.

### 10.2 Per-client discovery evidence

For each candidate exception and each eligible client:

1. freeze the re-certified discovery shared core;
2. compute `U`, `I`, reduced SSE, `beta_hat`, F statistic, and p-value using that client's discovery data;
3. preserve the existing estimability guard for very low active support;
4. apply BH `q_role = 0.10` across clients for that candidate.

The BH-supported clients form the provisional role.

### 10.3 Role admissibility

A localized role is admissible only when:

- at least one client is BH-supported;
- at least one outside-role client remains;
- role size is at most half of all clients;
- discovery effect signs among supported clients are consistent.

A mixed-sign supported role is classified as **scope/sign ambiguous** and rejected rather than forcing one common coefficient.

If more than half of clients support a gated exception, the candidate is **global-scope ambiguous** and is rejected as a localized exception. Phase 3 does not reinterpret gated exception grammar as a new shared ordinary term.

This preserves a clear separation between ordinary shared structure and declared conditional mechanisms.

### 10.4 Discovery coefficient

For an admissible role, estimate one common deviation coefficient from the additive role sufficient statistics on discovery data. Freeze this coefficient and the role identity before selector/probe certification.

## 11. Independent held-out deviation certification

Selector and probe remain untouched during role discovery.

For each fixed candidate role:

1. compute sufficient-statistic structural evidence on selector and probe packets;
2. aggregate the two held-out partitions only after role and coefficient direction are frozen;
3. compute the combined one-degree-of-freedom F p-value;
4. require final BY-adjusted `q_dev <= 0.05`;
5. require held-out effect sign to agree with discovery effect sign;
6. require median role-client held-out raw gain to be positive;
7. require pair invariance;
8. require selector outside-role non-degradation;
9. require probe outside-role non-degradation.

The existing outside-role safety definition is retained so that improved noise power cannot be purchased by degrading clients outside the inferred role.

The selector/probe directional veto from older versions is not reintroduced unless a separately approved ablation demonstrates a need. The final Phase-3 acceptance statistic is the noise-calibrated F certificate plus the preserved safety invariants.

## 12. Ambiguity and structural capacity

Retain the frozen high-level safety rules unless an engineering impossibility is demonstrated before fresh development:

- maximum operational localized exceptions: `2`;
- maximum final structure size: `10` including intercept;
- multiple accepted localized exceptions linked to the same source trigger source ambiguity and are rejected;
- exceeding the localized-exception cap triggers global ambiguity and rejects newly proposed exceptions rather than silently choosing by outcome.

Shared terms and localized terms are reported separately in diagnostics.

## 13. Expected theoretical results

Phase 3 should attempt to establish the following propositions formally.

### Proposition A: centralized-equivalence of the fixed-scope test

For a fixed reference model, candidate basis, and fixed client scope, summing client sufficient statistics produces the same `beta_hat`, reduced SSE, full SSE, and one-degree-of-freedom F statistic as the corresponding centralized calculation on concatenated observations, up to floating-point summation error.

### Proposition B: data-local computation boundary

The server can execute the structural test from aggregate sufficient statistics without direct access to raw client rows. This is a communication/data-locality property only; it is **not** a differential-privacy or cryptographic privacy guarantee.

### Proposition C: final deviation FDR control

Conditional on discovery-selected candidate roles and valid held-out null p-values, BY correction at `q_dev` controls the expected false-discovery proportion among final deviation hypotheses under arbitrary dependence.

The theorem statement must make its assumptions explicit: fixed held-out reference conditional on discovery, valid F-test noise model, and no use of held-out outcomes for role construction.

### Proposition D: empirical outside-role safety

For any accepted localized term, the existing selector and probe non-degradation checks guarantee that the tested FULL model does not increase aggregate held-out SSE relative to REDUCED on the recorded outside-role sets, subject only to the existing numerical tolerance. This is an empirical held-out property, not a population-level theorem.

## 14. Software architecture

Scientific methods must move out of giant notebooks into tested package modules.

Proposed structure:

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

The Colab notebook remains a one-cell reproducible runner, but the algorithm itself must be imported from pinned, tested package code.

## 15. Engineering optimization requirements

The refactor must improve runtime without changing frozen v11 decisions.

### Mandatory safe optimizations

1. Build discovery folds and sufficient packets once per condition, not once per candidate.
2. Cache per-client `U`, `I`, SSE, and support values for each fixed reference/candidate pair.
3. Derive pooled evidence, client gains, and outside safety from cached arrays instead of repeatedly calling packet-SSE routines.
4. Separate study/checkpoint/reporting time from method runtime.
5. Save atomic per-condition checkpoint records and periodically consolidate them to CSV, avoiding a full multi-megabyte CSV rewrite after every condition.
6. Keep deterministic ordering for clients, terms, conditions, and aggregation.

### Optimization acceptance rule

No optimization is accepted merely because it is faster. It must first pass frozen parity/regression tests showing unchanged v11 structural decisions and numerically equivalent sufficient-statistic calculations on the engineering suite.

## 16. Test strategy

### 16.1 Pure mathematical unit tests

Construct deterministic arrays where centralized and packet-based calculations have closed-form expected values. Test:

- `U`, `I`, beta estimate;
- reduced/full SSE identity;
- F statistic and p-value;
- additive aggregation across clients;
- zero-information candidate behavior;
- numerical stability with nearly zero residual variance.

### 16.2 Multiple-testing tests

Use fixed p-value vectors with known BH/BY outcomes. Test ties, empty candidate sets, all-null, all-significant, and canonical ordering.

### 16.3 Structural engineering cases

Hand-constructed cases must cover:

- clean shared term;
- missing shared term in the initial anchor;
- spurious shared anchor term;
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

These are engineering falsification tests, not publication evidence.

### 16.4 Frozen predecessor parity

Before any fresh Phase-3 seed is touched:

- official v11 tests must pass;
- refactored v11 must match the frozen v11 implementation on engineering conditions;
- no Phase-1 or Phase-2 evidence is regenerated or relabeled;
- any descriptive read of spent results must be clearly separated from prospective Phase-3 evidence.

## 17. Phase-3 ablation design

The fresh study must identify which mechanism creates any gain.

Primary methods:

1. **v11 frozen comparator**;
2. **NCEE-only:** old v11 shared/core behavior + noise-calibrated localized certification;
3. **SCR-only:** shared-core re-certification + old v11 localized certification;
4. **SCSV-NCSC full:** SCR + NCEE.

Historical PQCR-v1 and DR-PQCR-v2 may be shown in a separate retrospective table but are not primary Phase-3 gate comparators.

No ablation is allowed to determine thresholds after fresh outcomes are visible.

## 18. Seed firewall and prospective study namespace

Spent namespaces:

- engineering predecessor seed `29001` may be reused only for parity/debugging;
- Phase-1 development `29101--29105`: spent;
- Phase-2 development `29201--29205`: spent.

Reserved Phase-3 engineering-only seed:

- `29300`.

Reserved Phase-3 fresh development seeds:

- `29301, 29302, 29303, 29304, 29305, 29306, 29307, 29308, 29309, 29310`.

Reserved final confirmation:

- `11001+`, untouched.

The `29301--29310` seeds become permanently spent when the first fresh development condition starts, regardless of outcome. They must not be used during implementation debugging, threshold selection, or mathematical-unit testing.

## 19. Fresh development matrix

Retain the same structural grammar and condition factors used by the previous frozen development matrix so that gains are interpretable:

- quadratic, linear, trigonometric, and interaction localized families;
- `K = 4, 8, 16` clients;
- single and quarter roles where admissible;
- balanced and imbalanced client-size profiles;
- noise ratios `0.10` and `0.30`;
- null and anchor-contamination null families;
- weak-source and dual-role families.

Using ten prospective seeds doubles the prior 600-condition design to **1,200 matched conditions**.

Each condition runs the four frozen Phase-3 methods on the same generated data.

## 20. Primary and secondary endpoints

### Primary endpoint

Exact structural recovery of the full symbolic term set.

### Secondary endpoints

- shared TP/FP/FN, precision, recall;
- deviation TP/FP/FN, precision, recall;
- exact repair/harm counts relative to v11;
- role-set recovery where truth is defined;
- high-noise exact recovery;
- high-noise shared recovery;
- high-noise deviation recovery;
- family recovery;
- K-specific recovery;
- null spurious shared/deviation acceptance;
- test NMSE;
- runtime;
- communication;
- calibration diagnostics for structural p-values/q-values.

Predictive NMSE is secondary. A lower NMSE must not be interpreted as structural correctness when the recovered equation is wrong.

## 21. Prospective GO/NO-GO gate

These thresholds are chosen before `29301--29310` are touched.

The full SCSV-NCSC method must satisfy **all** of the following:

1. integrity: exactly 1,200 matched fresh conditions and zero implementation failures;
2. primary exact-recovery gain vs v11 `>= +0.03`;
3. seed-cluster bootstrap 95% CI lower bound for exact gain `> 0`;
4. paired discordance analysis favors SCSV-NCSC, with exact two-sided McNemar/binomial `p < 0.05` as supportive evidence;
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

If the full method fails, the result is `PHASE3-DEVELOPMENT-NO-GO`. The ablations may explain the failure but may not be used to redefine the full method on the same fresh seeds.

## 22. Statistical reporting

For publication-quality reporting:

- report per-seed exact rates;
- report seed-cluster bootstrap confidence intervals;
- report paired discordant counts and exact McNemar/binomial test;
- report Wilson intervals for absolute recovery rates;
- report raw TP/FP/FN counts, not only precision/recall percentages;
- report calibration plots or empirical null distributions for structural p-values where appropriate;
- treat conditions nested within a seed as clustered, not as 1,200 independent replicates for primary uncertainty claims.

## 23. External-validation path after a GO

A Phase-3 GO does not authorize final confirmation immediately.

The next frozen validation stage should add:

- stronger symbolic-regression baselines, including a federated SR baseline where reproducible code is available;
- local-only and pooled-centralized references;
- a strong centralized SR package such as PySR/Operon where grammar compatibility permits;
- a noise-robust SR comparator where the benchmark assumptions are comparable;
- stronger noise levels beyond `0.30`;
- partial participation and missingness stress tests;
- larger client counts;
- at least one realistic multi-source or naturally partitioned dataset whose structural ground truth or semi-synthetic truth is defensible.

Only after that stage is frozen and successful should the `11001+` final-confirmation namespace be touched once.

## 24. Novelty claim to pursue

The intended novelty is not ordinary federated symbolic regression.

The defensible target contribution is:

> **Federated set-conditional symbolic discovery that jointly distinguishes shared symbolic structure from sparse client-localized structural deviations using noise-calibrated, independently certified sufficient-statistic evidence.**

The paper should emphasize four aspects only if the experiments support them:

1. shared-vs-localized symbolic scope recovery;
2. noise-calibrated structural certification;
3. false-structure and outside-role safety;
4. data-local sufficient-statistic computation with exact centralized-equivalence for fixed-scope tests.

A formal systematic literature review must be completed before using words such as “first” or “unique.”

## 25. Decision after design approval

After this written specification is reviewed and approved, implementation planning must proceed in this order:

1. refactor and parity infrastructure;
2. mathematical sufficient-statistic/F-test module;
3. shared-core re-certification;
4. noise-calibrated role discovery;
5. held-out deviation certification;
6. ablation wrappers;
7. engineering falsification suite;
8. performance profiling/caching;
9. frozen Phase-3 protocol and authorization;
10. only then run `29301--29310`.

No fresh Phase-3 development run is authorized by this design document alone.
