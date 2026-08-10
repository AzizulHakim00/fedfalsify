# FedFalsify v8 — SCSV-SPCC

## Set-Conditional Structural Verification with Source-Pair Contrast Certification

### Scientific status

This document freezes the successor design motivated by the sealed SCSV-RCD v7 DEVELOPMENT-NO-GO and the sealed post-v7 forensic decomposition. It is a **new versioned development protocol**, not a reinterpretation of v7 and not a continuation of v7 evidence.

The v7 development seeds `24101--24105` are permanently spent and are prohibited from all v8 scientific evidence. The engineering-only v8 seed is `25001`. The reserved fresh v8 development seeds are `25101--25105`; they must remain untouched until this protocol, the implementation, the invariants, the dedicated engineering smoke, and the complete repository regression are all green at one exact source SHA.

Historical facts remain immutable:

- SCSV-Cert v6 independent validation remains `INDEPENDENT-NO-GO`.
- RCCD remains a post-independent spent-seed mechanism signal only.
- SCSV-RCD v7 remains `DEVELOPMENT-NO-GO`.
- Nothing in v8 can retrospectively change those decisions.
- External SRSD/Feynman confirmation remains blocked until a future v8 independent-validation stage itself passes a separately frozen protocol.

### Motivation fixed before v8 evidence

The sealed v7 forensics localized the dominant failure mechanism:

1. v7 left `62` true deviations unresolved;
2. `45/62` residual misses were outside-role safety rejections;
3. most rejected candidates already had favorable selector/probe conditional evidence;
4. the v7 full model jointly re-estimated all shared-anchor coefficients before testing a deviation, so outside-role degradation could be caused by shared/core coefficient drift rather than by the deviation under test;
5. the two v7 exact harms came from a separate null-role failure: support-based role eligibility could classify naturally occurring gated samples as a client-level role and could leave no genuine outside-role client for falsification;
6. simply deleting the independent probe was insufficient because most remaining misses were selector-side outside-role failures.

Therefore v8 does **not** loosen v7 thresholds and does **not** remove independent certification. It changes the identification architecture.

---

# 1. Scientific claim boundary

SCSV-SPCC v8 must not claim novelty for any of the following by themselves:

- shared global structure with group-specific parameters;
- personalized/global-local parameter decomposition;
- mixed/random effects;
- personalized federated learning;
- federated sufficient-statistic estimation.

The only candidate methodological contribution to test is narrower:

> A federated symbolic certificate for a banked, source-linked gated deviation that (i) identifies the client-level role from response-free cross-client gate concentration, (ii) estimates the shared source and role deviation as an isolated two-parameter source pair while freezing unrelated shared terms, and (iii) uses disjoint selector/probe evidence to distinguish support, inconclusive directional evidence, and direct contradiction without allowing unrelated shared-coefficient movement to contaminate the certificate.

Whether this contribution is publishably novel is a literature question separate from whether the mechanism works.

---

# 2. Frozen symbolic form

Let the frozen SCSV-Cert shared anchor be

\[
f_S(x)=\sum_{j\in S}\beta_j\phi_j(x).
\]

A banked source-linked deviation has the form

\[
e(x)=g(x)\phi_s(x),
\]

where `source_term(e) = phi_s` and `phi_s` already belongs to the frozen anchor.

The v8 source-pair model is

\[
f_{S,e}(x)=\sum_{j\in S\setminus\{s\}}\beta_j^{(0)}\phi_j(x)
+\beta_s^{(out)}\phi_s(x)
+\delta_e\,e(x).
\]

All unrelated coefficients `beta_j^(0)` are frozen from the discovery-side SCSV anchor during certification.

Only the source coefficient `beta_s^(out)` and the deviation coefficient `delta_e` may be estimated for this candidate certificate.

---

# 3. Response-free role identification

v8 may not define a role from outcome values or from residual improvement.

For each source-linked deviation `e`, compute on **discovery X only** the client-level gate occupancy

\[
p_i(e)=\frac{\#\{n: |e(x_{in})|>10^{-12}\}}{N_i}.
\]

Sort occupancies ascending:

\[
p_{(1)}\le\cdots\le p_{(m)}.
\]

For every split that leaves at least one client on each side and assigns at most half the federation to the candidate role, compute the adjacent separation gap

\[
d_k=p_{(m-k+1)}-p_{(m-k)},\qquad
1\le k\le \lfloor m/2\rfloor.
\]

Choose `k*` by maximum `d_k`; ties choose the smaller role set, then lexicographic client-id order.

The role hypothesis is **admissible** only if all are true:

1. `d_k* >= 0.50`;
2. mean occupancy among proposed role clients is `>= 0.75`;
3. mean occupancy among outside clients is `<= 0.25`;
4. at least one role client exists;
5. at least one outside client exists.

If any rule fails, the candidate is `ROLE-NOT-IDENTIFIED` and cannot be structurally accepted.

The discovered client IDs are frozen for that candidate and reused unchanged on selector and probe packets. Selector/probe data do not redefine the role.

This rule is intentionally stronger than sample-support eligibility. It represents a **client-level distributional role**, not the mere presence of some gated observations.

---

# 4. Constrained source-pair estimation

For candidate source `s`, let the frozen unrelated-anchor residual on discovery client `i` be

\[
r_i=y_i-\sum_{j\in S\setminus\{s\}}\beta_j^{(0)}\phi_j(X_i).
\]

## 4.1 Shared source coefficient

Use **outside-role discovery packets only**:

\[
\hat\beta_s^{(out)}=
\frac{\sum_{i\in O}\phi_s(X_i)^\top r_i}
{\sum_{i\in O}\phi_s(X_i)^\top\phi_s(X_i)+10^{-10}}.
\]

No role client contributes to this estimate.

## 4.2 Role-deviation coefficient

For role clients `R`, define

\[
\tilde r_i=r_i-\hat\beta_s^{(out)}\phi_s(X_i).
\]

Then estimate

\[
\hat\delta_e=
\frac{\sum_{i\in R}e(X_i)^\top\tilde r_i}
{\sum_{i\in R}e(X_i)^\top e(X_i)+10^{-10}}.
\]

No unrelated shared coefficient may move during these two estimations.

---

# 5. Fixed reduced comparator

For every candidate, define two discovery-fitted coefficient vectors:

- `FULL`: frozen unrelated anchor + `beta_s^(out)` + `delta_e`;
- `REDUCED`: identical to FULL except `delta_e = 0`.

The following must be bitwise/equality checked in implementation within floating serialization tolerance:

- same active anchor terms;
- same intercept;
- same unrelated shared coefficients;
- same source coefficient;
- only the tested deviation coefficient differs.

This is the core anti-confounding invariant.

---

# 6. Selector evidence

The selector uses the frozen discovery-fitted FULL/REDUCED pair without coefficient re-estimation.

For the frozen role-client set, with total selector support `N_R`, compute

\[
\Delta J_{sel}=
\log\frac{SSE_{FULL,sel}}{SSE_{RED,sel}}
+\frac{\log N_R}{N_R}.
\]

Selector state is:

- `SUPPORTED` iff `Delta J_sel < 0`;
- otherwise `NOT-SUPPORTED`.

A deviation cannot be accepted without selector `SUPPORTED`.

---

# 7. Independent three-state probe certificate

The probe uses the same discovery-fitted FULL/REDUCED pair and the same frozen role IDs.

Compute

\[
\Delta J_{probe}=
\log\frac{SSE_{FULL,probe}}{SSE_{RED,probe}}
+\frac{\log N_R}{N_R}.
\]

Probe state is frozen as:

1. `SUPPORTED` if `Delta J_probe < 0`;
2. `INCONCLUSIVE-DIRECTIONAL` if `Delta J_probe >= 0` **and** `SSE_FULL,probe < SSE_RED,probe - 1e-12`;
3. `CONTRADICTED` otherwise.

Thus a small directional improvement that fails the one-parameter information penalty is not treated as active falsification, while zero improvement or worsening is contradiction.

No tunable probe margin exists.

---

# 8. Isolated outside-role safety

Outside-role safety is evaluated between the same FULL and REDUCED source-pair models, not against a separately refitted global model.

For selector and probe separately:

\[
SSE_{FULL,O}\le SSE_{RED,O}+10^{-10}.
\]

Because FULL and REDUCED differ only in `delta_e`, any outside-role difference is attributable to the candidate deviation itself rather than drift in unrelated shared coefficients.

Both selector and probe outside-role safety must pass.

---

# 9. Frozen acceptance rule

A source-linked deviation is structurally positive iff all are true:

1. role hypothesis admissible;
2. source exists in frozen anchor;
3. candidate exists in frozen high-recall bank;
4. selector state = `SUPPORTED`;
5. selector outside-role safety passes;
6. probe state is `SUPPORTED` or `INCONCLUSIVE-DIRECTIONAL`;
7. probe outside-role safety passes.

`CONTRADICTED` probe evidence always rejects the deviation.

No result-dependent rescue or threshold tuning is allowed.

---

# 10. Multiple-deviation governance

- Maximum added deviations: `2`.
- Frozen SCSV shared anchor terms are never deleted, replaced, or reordered by v8.
- If more than two deviations are positive, all v8 augmentation is rejected and the frozen anchor is restored (`GLOBAL-AMBIGUITY`).
- If two or more positive deviations share the same source term, all positives attached to that source are rejected (`SOURCE-AMBIGUITY`).
- Remaining unambiguous positives, up to two total, may be added simultaneously.
- Structural acceptance is decided before any final coefficient refit.

After structural acceptance only, the selected final structure may be refit on the ordinary frozen training/validation pool for prediction reporting. That refit cannot change structural membership and is not used to decide acceptance.

---

# 11. Frozen invariants

Implementation tests must prove:

A. historical v6, v7, RCCD, and sealed evidence blobs are unchanged;

B. role inference uses X/gate occupancy only and never y/residuals;

C. every accepted role has at least one role client and one outside client;

D. selector/probe role IDs equal the discovery role IDs exactly;

E. unrelated shared coefficients are invariant between FULL and REDUCED;

F. only tested deviation coefficient is zeroed in REDUCED;

G. source coefficient is estimated from outside discovery clients only;

H. deviation coefficient is estimated from role discovery clients only;

I. selector and probe never refit coefficients;

J. selector acceptance requires `Delta J < 0`;

K. probe state implements the exact three-state rule;

L. contradicted probe evidence can never be accepted;

M. selector and probe outside safety compare FULL versus REDUCED pair only;

N. frozen anchor structure is a subset of every non-ambiguous final structure;

O. source ambiguity and >2-positive ambiguity both restore/protect the anchor;

P. truth labels are absent from all algorithmic calls;

Q. engineering seed `25001` cannot enter scientific output;

R. scientific seeds `25101--25105` cannot be used by smoke/test code.

---

# 12. Frozen v8 benchmark grammar

The v8 development benchmark is separate from v7 and uses new source/gate combinations. The finite grammar must expose all four source-linked deviation candidates in every condition so the algorithm is not handed the truth.

Planned source-linked deviations:

1. `I(x1<-0.75)*x1^2`, source `x1^2`;
2. `I(x3>0.75)*x3`, source `x3`;
3. `I(x1>0.75)*cos(x1)`, source `cos(x1)`;
4. `I(x2<-0.75)*x1*x2`, source `x1*x2`.

The four single-deviation families each use exactly one of these as truth while all four remain visible distractors.

A null family contains none.

A diffuse-null family deliberately allows ordinary within-client gate occupancy without any client-level coefficient deviation and must be rejected by the role-contrast rule.

A dual family contains two non-overlapping source-linked deviations with distinct source terms.

No v7 truth equation is copied verbatim.

---

# 13. Nonredundant development matrix

All conditions use nominal `100` samples/client before imbalance transformation.

Noise ratios: `0.10`, `0.30`.

Balance: `balanced`, `imbalanced`.

Clients: `4`, `8`, `16` as specified below.

Fresh seeds: exactly `25101--25105`.

## 13.1 Single-deviation families

Four families.

- 4 clients: `single` role only; no duplicate `quarter` label.
- 8 clients: `single` and `quarter` roles.
- 16 clients: `single` and `quarter` roles.

Count:

- 4 clients: `4 families x 2 balance x 1 role-profile x 2 noise x 5 seeds = 80`;
- 8 clients: `4 x 2 x 2 x 2 x 5 = 160`;
- 16 clients: `4 x 2 x 2 x 2 x 5 = 160`.

Single-deviation total = `400`.

## 13.2 Standard null

`3 client counts x 2 balance x 2 noise x 5 seeds = 60`.

## 13.3 Diffuse-null stress

4 and 8 clients only:

`2 client counts x 2 balance x 2 noise x 5 seeds = 40`.

## 13.4 Dual-deviation stress

8 and 16 clients:

`2 client counts x 2 balance x 2 noise x 5 seeds = 40`.

## 13.5 Total

Exactly **540 scientific conditions**.

No duplicate role geometries are counted under different labels.

---

# 14. Frozen methods

Every scientific condition is evaluated by exactly these five methods:

1. `scsv-spcc-v8-full` — three-state probe;
2. `scsv-spcc-v8-strict-probe` — same pair estimator and role guard, but probe must be `SUPPORTED`; this is an ablation only;
3. `scsv-rcd-v7-style` — v7 joint-refit certificate applied to the v8 grammar; comparator baseline, not historical evidence;
4. `scsv-v6-anchor` — frozen SCSV-Cert anchor;
5. `centralized-forward` — centralized finite-grammar comparator.

Expected sealed row count: `540 x 5 = 2700`.

---

# 15. Frozen metrics

Primary:

- exact structural recovery;
- term precision;
- term recall;
- pooled deviation precision;
- pooled deviation recall;
- all-true-deviations recovered;
- exact harms relative to matched v6 exact successes;
- null/diffuse-null spurious deviation acceptance;
- test NMSE.

Mechanism diagnostics:

- bank presence;
- source-anchor presence;
- role hypothesis state;
- role/outside client counts;
- occupancy separation gap;
- selector state and Delta J;
- probe state and Delta J;
- selector/probe raw SSE changes;
- selector/probe outside safety;
- source estimate;
- deviation estimate;
- source ambiguity;
- global ambiguity;
- final structure.

Efficiency:

- communication bytes;
- runtime.

---

# 16. Frozen all-or-nothing development gates A--T

A. **Integrity:** exactly 540 unique scientific conditions, exactly 2700 rows, only seeds `25101--25105`, no required NaN/Inf, exact five methods.

B. **Anchor monotonicity:** every v8 final structure contains the frozen v6 anchor structure unless an ambiguity guard restores the anchor exactly.

C. **Null precision:** pooled standard-null + diffuse-null spurious deviation acceptance `<= 0.02`.

D. **Zero exact harms:** zero matched conditions where v6 is exact and v8 becomes structurally inexact.

E. **Overall noninferiority:** v8 exact recovery `>= v6 exact - 0.01`.

F. **Deviation-subset gain:** v8 exact recovery on deviation-bearing conditions `>= v6 + 0.05`.

G. **Deviation precision:** pooled deviation precision `>= 0.99`.

H. **Deviation recall:** pooled deviation recall `>= 0.93`.

I. **Family floor:** each of the four single-deviation families has all-true-deviation recovery `>= 0.90`.

J. **4-client floor:** single-deviation recovery at 4 clients `>= 0.88`.

K. **8-client floor:** single-deviation recovery at 8 clients `>= 0.92`.

L. **16-client floor:** single-deviation recovery at 16 clients `>= 0.92`.

M. **High-noise floor:** single-deviation recovery at noise `0.30` `>= 0.88`.

N. **Imbalance robustness:** imbalanced recovery `>= balanced recovery - 0.06`.

O. **Dual recovery:** both true deviations recovered in `>= 0.90` of dual conditions, with zero spurious deviation among exact dual recoveries.

P. **Role-contrast integrity:** every accepted deviation has at least one role and one outside client, separation gap `>= 0.50`, role mean occupancy `>= 0.75`, outside mean occupancy `<= 0.25`; false role-hypothesis rate on null families `<= 0.02`.

Q. **Certificate integrity:** every accepted deviation has selector `SUPPORTED`, probe not `CONTRADICTED`, selector/probe isolated outside safety pass, and no FULL/REDUCED coefficient-invariance violation.

R. **Mechanism superiority:** deviation-bearing exact recovery for v8 full `>= scsv-rcd-v7-style + 0.03`, and v8 exact harms are no greater than v7-style harms.

S. **Communication:** median v8 communication `<= 1.50 x` matched v6 median communication.

T. **Runtime:** median v8 runtime `<= 2.00 x` matched v6 median runtime.

**Development GO requires all A--T. Any single failure means DEVELOPMENT-NO-GO.**

There is no partial-credit reinterpretation.

---

# 17. Pre-evidence firewall

Before fresh development authorization:

1. protocol commit exists;
2. v8 implementation complete;
3. v8 benchmark generator complete;
4. study harness computes A--T automatically;
5. unit/invariant tests pass;
6. forced-path tests cover:
   - true single-deviation acceptance;
   - true dual-deviation acceptance;
   - null-role rejection;
   - diffuse-null rejection;
   - probe `SUPPORTED`;
   - probe `INCONCLUSIVE-DIRECTIONAL`;
   - probe `CONTRADICTED` rejection;
   - source ambiguity;
   - >2-positive ambiguity;
   - coefficient-isolation invariant;
7. dedicated engineering smoke uses seed `25001` only;
8. smoke artifact proves zero scientific seeds used;
9. complete repository regression passes at the same exact source state;
10. only then may a separate authorization commit containing `[run-v8-development]` release `25101--25105`.

Once the first scientific v8 row is generated, `25101--25105` become permanently spent regardless of technical/scientific outcome.

---

# 18. Decision after development

If A--T all pass:

- status `DEVELOPMENT-GO`;
- v8 code, thresholds, grammar, and development seeds freeze permanently;
- only then design a separately versioned independent-validation protocol with a new untouched seed namespace and new truth recombinations.

If any gate fails:

- status `DEVELOPMENT-NO-GO`;
- seeds `25101--25105` remain spent;
- no threshold/gate retuning on them;
- perform read-only forensic decomposition before any successor.

Neither outcome authorizes external SRSD retrospectively.
