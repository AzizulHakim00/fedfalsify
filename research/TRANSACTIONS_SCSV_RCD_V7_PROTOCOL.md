# FedFalsify v7: Set-Conditional Structural Verification with Role-Contrast Deviations (SCSV-RCD)

Status: **FROZEN BEFORE ANY v7 SCIENTIFIC RUN**.

This document defines the first genuinely fresh successor to SCSV-Cert v6 after the sealed independent NO-GO and the post-independent RCSA/FCRRA/RCCD spent-seed diagnostics. The sealed RCCD PASS is a mechanism signal only. It is not reused as v7 evidence.

## 1. Scientific claim boundary

SCSV-RCD does **not** claim that global/local parameter decomposition, personalization, hierarchical federated learning, or mixed-effects modeling is new. Those ideas already exist in personalized and hierarchical federated learning.

The narrower target contribution is:

> privacy-preserving symbolic structure recovery in which a role-restricted mechanism is represented as a source-linked symbolic deviation from an already identified shared mechanism, jointly identified from cross-role sufficient statistics and independently certified on disjoint held-out selector and probe packets.

The proposed method combines four ingredients that must be evaluated together:

1. high-recall federated symbolic candidate-bank construction;
2. set-conditional shared-structure selection;
3. source-linked role-deviation identification under cross-role confounding;
4. independent non-destructive deviation certification.

Passing the v7 development gate will authorize only a separately frozen independent v7 validation stage. It will not authorize external SRSD confirmation until that independent stage passes.

## 2. Historical evidence boundary

Historical evidence is immutable:

- SCSV-Cert v6 development seeds `19101--19105` are spent;
- SCSV-Cert v6 independent seeds `20101--20105` are spent;
- RCCD used only the already-spent `20101--20105` and therefore remains diagnostic;
- v6 independent status remains `INDEPENDENT-NO-GO` regardless of v7 outcome;
- RCSA and FCRRA remain NO-GO diagnostics;
- RCCD remains `RCCD-MECHANISM-SIGNAL`, not confirmation.

No result from those seeds may be used to tune a v7 threshold, gate, benchmark coefficient, role fraction, noise level, or acceptance rule.

## 3. Fresh seed boundary

Engineering-only smoke seed:

- `24001`

Fresh v7 development evidence seeds:

- `24101`, `24102`, `24103`, `24104`, `24105`

These seeds were repo-search checked before this protocol freeze and had no prior use found.

The smoke seed may never appear in scientific v7 development output. The five development seeds become permanently spent when the first formal v7 development matrix begins.

A future independent v7 seed namespace is deliberately **not** allocated here. It will be selected and frozen only if the development gate passes.

## 4. Frozen shared anchor

SCSV-RCD must call the existing frozen `scsv_cert_method` with the v6 scientific settings unchanged:

- score proposer enabled;
- candidate-bank cap `10`;
- shared selector cap `6` terms including intercept;
- existing SCSV information score;
- existing selector/probe split logic;
- probe remains non-destructive for the shared anchor.

The v6-selected term set is the shared structural anchor `S`.

SCSV-RCD may add role deviations but may never delete, replace, reorder, or retune a term in `S` during the deviation decision.

## 5. v7 deviation grammar

The v7 research catalog adds the following **four** exception candidates to the existing finite grammar. All four candidates are exposed in every v7 condition, including null controls.

| deviation term | declared source term | role gate | structural class |
|---|---|---|---|
| `I(x3>1)*x3^2` | `x3^2` | `x3 > 1` | quadratic |
| `I(x1>1)*x1` | `x1` | `x1 > 1` | linear |
| `I(x2>1)*sin(x2)` | `sin(x2)` | `x2 > 1` | trigonometric |
| `I(x2<-1)*x1*x2` | `x1*x2` | `x2 < -1` | interaction |

Every deviation has explicit `source_term` metadata. A deviation is structurally eligible only if its source term is already present in the frozen shared anchor.

The algorithm receives the full v7 deviation grammar, never the identity of the true deviation.

## 6. Fresh benchmark truth families

Five primary truth families are frozen.

### 6.1 Quadratic deviation family

Shared truth:

`0.8*x1^3 + 1.0*sin(x2) + 0.6*x3^2`

Role deviation when enabled:

`+ 0.75*I(x3>1)*x3^2`

### 6.2 Linear deviation family

Shared truth:

`1.0*x1 + 0.8*x2^2 + 0.7*cos(x3)`

Role deviation when enabled:

`+ 0.70*I(x1>1)*x1`

### 6.3 Trigonometric deviation family

Shared truth:

`0.9*sin(x2) + 0.7*x1^2 + 0.6*x3`

Role deviation when enabled:

`+ 0.70*I(x2>1)*sin(x2)`

### 6.4 Interaction deviation family

Shared truth:

`1.0*x1*x2 + 0.7*x3^2 + 0.6*cos(x1)`

Role deviation when enabled:

`+ 0.65*I(x2<-1)*x1*x2`

### 6.5 Null-deviation control family

Shared truth:

`1.0*x1 + 0.8*sin(x2) + 0.6*x3^2`

No role deviation is present, while all four deviation candidates remain available in the grammar.

A separate dual-deviation stress family is defined in Section 8.

## 7. Federation and role profiles

Client counts:

- `4`, `8`, `16`

Balance profiles:

- `balanced`;
- `imbalanced`, using the frozen truth-independent geometric client-size construction already used by the independent v6 study, with the same minimum feasible client size.

Role profiles for single-deviation families:

- `single`: one terminal eligible client;
- `quarter`: the final `max(1, num_clients // 4)` clients are eligible.

Eligibility is generated by shifting the gate variable into the declared role domain for eligible clients and outside the role domain for noneligible clients. The algorithm itself never receives the role labels; it infers eligibility only from observed support of each deviation term.

The held-out eligibility floor remains:

`max(3, ceil(0.10 * local_support))`.

## 8. Dual-deviation stress family

A fresh stress family tests whether two independently gated deviations can coexist without deleting shared structure.

Shared truth:

`0.9*x1 + 0.7*sin(x2) + 0.6*x3^2`

True deviations:

- `+ 0.60*I(x1>1)*x1`;
- `+ 0.65*I(x3>1)*x3^2`.

Only client counts `8` and `16` are used for this stress family. Role profile is `quarter`; the two role groups are deterministic, truth-independent subsets derived from client index: the highest-index quarter activates the quadratic deviation and the preceding quarter activates the linear deviation. They are non-overlapping by construction.

All four deviation candidates remain in the catalog.

## 9. Noise and sample matrix

Nominal samples per client:

- `100`

Noise ratios relative to pooled noiseless target standard deviation:

- `0.10`;
- `0.30`.

The development matrix is fixed as follows.

### Single-deviation families

4 families × 3 client counts × 2 balance profiles × 2 role profiles × 2 noise levels × 5 seeds = **480 conditions**.

### Null-deviation controls

1 family × 3 client counts × 2 balance profiles × 2 noise levels × 5 seeds = **60 conditions**.

### Dual-deviation stress

1 family × 2 client counts × 2 balance profiles × 2 noise levels × 5 seeds = **40 conditions**.

Total v7 fresh development conditions: **580**.

No condition may be added, deleted, or reweighted after the first scientific v7 row is generated.

## 10. Source-linked deviation candidate set

After frozen v6 returns shared anchor `S` and candidate bank `B`, define

`D = {e in B : kind(e)=exception, e not in S, source(e) in S}`.

No exception outside `B` can be considered.

No exception whose declared source is absent from `S` can be considered.

Already-selected v6 exception terms remain untouched and are not re-certified as new deviations.

The v7 final structure cap is:

- shared anchor: at most `6` terms including intercept;
- added deviations: at most `2`;
- final structure: at most `8` terms including intercept.

If more than two source-linked missing deviations are banked, the deviation stage does **not** rank them using held-out data. Instead, all banked source-linked deviations are included in the discovery-only joint fit, but no more than two may become operational. If more than two independently pass every frozen certificate, the condition is declared `ambiguous-multi-deviation` and **no new deviation is operationally added**. This conservative rule prevents selector/probe ranking after evidence exposure.

## 11. Joint discovery identification

Let `S` be the frozen shared anchor and `D` the source-linked missing deviation candidates.

Using discovery sufficient-statistic packets only, fit one joint nested model

`M_full = S union D`.

The purpose of the joint fit is to identify shared-source coefficients from clients outside each role while estimating role-specific deviations in the same discovery system.

No selector rows, probe rows, global test rows, truth labels, or benchmark metadata indicating the true deviation may enter this fit.

## 12. Fixed-reduced coefficient contrasts

For each candidate deviation `e in D`, construct `M_-e` by copying all discovery-fitted coefficients from `M_full` and setting only the coefficient of `e` to zero.

Do not refit `M_-e`.

This tests the held-out contribution of exactly one source-linked deviation coefficient conditional on the same jointly identified shared coefficients and all other discovery-fitted candidate deviations.

## 13. Selector and independent probe certification

For each candidate `e`, selector eligibility is computed from selector packets only and probe eligibility from probe packets only.

For split `h` in `{selector, probe}`, with eligible support `N_h(e)`, define

`Delta_h(e) = log(SSE_full,h(e) / SSE_-e,h(e)) + log(N_h(e)) / N_h(e)`.

A deviation receives a split certificate iff:

`Delta_h(e) < 0`.

A deviation is certificate-positive only if both selector and probe pass.

There is no additional tuned margin, alpha threshold, p-value threshold, effect-size threshold, or exception-specific constant.

## 14. Outside-role safety

For every certificate-positive candidate deviation `e`, evaluate selector and probe clients not eligible for `e`.

The joint full model must not have greater aggregate outside-role SSE than the frozen v6 discovery anchor, up to `1e-10`, on both selector and probe splits.

Per-client outside-role changes are recorded descriptively.

A candidate failing either aggregate outside-role safety check is not operationally accepted.

## 15. Operational accepted set

Let `P` contain deviations passing:

- bank/source prerequisites;
- selector conditional certificate;
- probe conditional certificate;
- selector outside-role safety;
- probe outside-role safety.

Rules:

- `|P| = 0`: final structure is exactly `S`;
- `|P| = 1`: add that deviation;
- `|P| = 2`: add both deviations;
- `|P| > 2`: ambiguity guard activates and final structure is exactly `S`.

No shared term may be removed or replaced.

For post-decision test evaluation only, coefficients may be refit on complete training-client data after the final term set is frozen. The global synthetic test generator remains selection-blind.

## 16. Required comparators

Every fresh development condition must evaluate at least:

1. `scsv-rcd-v7-full`;
2. frozen `scsv-v6-full` anchor;
3. `legacy-certificate`;
4. `centralized-forward` upper/reference comparator.

Ablations required in the same fresh matrix:

5. `scsv-rcd-v7-no-probe`: identical discovery/selector mechanism but does not require probe certificate; descriptive ablation only and never eligible to define the v7 GO decision;
6. `scsv-rcd-v7-orphan-disabled` is the full method itself by construction; source-link removal is tested only in engineering/unit tests, not as a competing scientific algorithm because admitting orphan deviations violates the mechanism hypothesis.

The GO decision is based only on `scsv-rcd-v7-full` against preregistered gates and condition-matched frozen comparators.

## 17. Required row-level outputs

Each v7-full row must record at minimum:

- condition key and seed;
- benchmark family;
- client count, balance profile, role profile, noise ratio;
- shared truth terms and true deviation terms for evaluation only;
- frozen v6 anchor structure;
- candidate bank;
- source-linked candidate deviation set;
- discovery joint structure and coefficients;
- per-candidate source term;
- selector/probe eligible clients and support;
- selector/probe full and fixed-reduced SSE;
- selector/probe `Delta`;
- selector/probe certificate flags;
- selector/probe outside-role anchor/full SSE and safety flags;
- ambiguity guard flag;
- accepted deviations;
- final structure;
- exact recovery;
- term precision/recall;
- deviation precision/recall;
- all-true-deviations recovered;
- spurious deviation acceptance;
- test NMSE;
- runtime;
- communication bytes.

## 18. Fresh v7 development gates

SCSV-RCD v7 receives **DEVELOPMENT-GO** only if every gate A--R passes.

A. **Integrity:** exactly 580 v7-full conditions, only seeds `24101--24105`, no smoke seed, no duplicate condition keys, all required numeric outputs finite.

B. **Shared-anchor preservation:** every final v7 structure contains the entire frozen v6 shared anchor.

C. **Null safety:** null-control spurious deviation acceptance <= `0.05`.

D. **No exact harms:** zero conditions that are exact under frozen v6 become structurally inexact solely because of an accepted v7 deviation.

E. **Overall structural noninferiority:** v7 exact recovery across all 580 conditions is at least frozen v6 exact recovery minus `0.01`.

F. **Deviation-subset structural gain:** on the 520 conditions containing at least one true deviation, v7 exact recovery exceeds frozen v6 by at least `0.03` absolute.

G. **Deviation precision:** pooled accepted-deviation precision >= `0.95`.

H. **Deviation recall:** pooled true-deviation recall >= `0.90`.

I. **Family generality:** all-true-deviation recovery is at least `0.85` separately for each single-deviation structural class: quadratic, linear, trigonometric, interaction.

J. **Four-client robustness:** pooled all-true-deviation recovery on 4-client single-deviation conditions >= `0.85`.

K. **Eight-client robustness:** pooled all-true-deviation recovery on 8-client single-deviation conditions >= `0.90`.

L. **Sixteen-client robustness:** pooled all-true-deviation recovery on 16-client single-deviation conditions >= `0.90`.

M. **Imbalance robustness:** all-true-deviation recovery under imbalanced single-deviation conditions is no more than `0.08` absolute below balanced conditions.

N. **High-noise robustness:** at noise ratio `0.30`, pooled all-true-deviation recovery on single-deviation conditions >= `0.85`.

O. **Dual-deviation stress:** both true deviations are recovered together in at least `0.75` of the 40 dual-deviation conditions, with zero non-truth deviation accepted in those exact dual recoveries.

P. **Certificate integrity:** every operationally accepted deviation passes both selector and probe conditional tests and both outside-role aggregate safety checks; zero violations.

Q. **Communication:** median communication bytes of v7-full across matched conditions <= `1.50` times frozen v6 median communication.

R. **Runtime:** median unoptimized runtime of v7-full <= `2.00` times frozen v6 median runtime.

Any failed gate yields **DEVELOPMENT-NO-GO**. No subgroup rescue, gate relaxation, threshold adjustment, or seed replacement is allowed after scientific rows are generated.

## 19. Engineering smoke requirements

Before fresh seeds are released, seed `24001` only must verify:

- frozen v6 is called unchanged;
- all four deviation candidates exist and have correct source metadata;
- truth identity is never passed to the v7 selection routine;
- source-absent candidates are blocked;
- already-selected deviations are untouched;
- joint discovery fit uses discovery packets only;
- fixed-reduced candidates differ by exactly one zeroed deviation coefficient;
- selector and probe eligibility are independent;
- selector never reads probe packets;
- probe never refits discovery coefficients;
- the penalty is exactly one additional parameter per conditional test;
- outside-role safety is checked against the frozen v6 discovery anchor;
- no shared anchor term can be deleted;
- ambiguity guard activates when more than two deviations pass;
- null-control path can return the unchanged anchor;
- dual-deviation path can represent two source-linked deviations;
- smoke contains only `24001`;
- gates A--R are not evaluated in smoke mode.

Only engineering defects may be repaired after this protocol freeze and before fresh scientific execution. Scientific thresholds, truth coefficients, matrix composition, and A--R gates are frozen now.

## 20. Promotion rule

If all A--R gates pass, v7 earns only **DEVELOPMENT-GO** and the project may design a separately frozen independent v7 validation with a new untouched seed namespace and novel truth recombinations.

If any gate fails, v7 is **DEVELOPMENT-NO-GO** and these fresh seeds are permanently spent. A new successor must be separately versioned; v7 may not be tuned on the failed evidence and rerun as though confirmatory.

Only an independent v7 GO can authorize a new external-validation layer.

## 21. Prior-art boundary used for claim discipline

The protocol was frozen after checking contemporary primary literature showing that personalization and global/local decomposition are established ideas, including partially personalized FL, hierarchical Bayesian personalized FL, and privacy-preserving symbolic regression. Therefore the paper must not claim those generic concepts as novel.

Representative primary sources considered before freeze:

- Mishchenko et al., *Partially Personalized Federated Learning: Breaking the Curse of Data Heterogeneity*, arXiv:2305.18285.
- Thapa and Li, *Harnessing Heterogeneous Statistical Strength for Personalized Federated Learning via Hierarchical Bayesian Inference*, ICML 2025, PMLR 267.
- Nguyen Duy, Affenzeller, and Nikzad-Langerodi, *Towards Vertical Privacy-Preserving Symbolic Regression via Secure Multiparty Computation*, arXiv:2307.11756 / GECCO Companion 2023.

The intended novelty claim is restricted to source-linked symbolic role-deviation identification and independent structural certification inside a federated symbolic-recovery pipeline.