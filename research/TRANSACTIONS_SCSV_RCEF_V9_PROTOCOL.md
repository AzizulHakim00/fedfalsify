# FedFalsify v9: SCSV-RCEF protocol

## Canonical name

**FedFalsify v9: Set-Conditional Structural Verification with Role-Contrast Evidence Fusion (SCSV-RCEF)**

## Scientific status

This protocol is frozen **before** any v9 engineering or fresh-development seed is executed.

Historical boundaries remain permanent:

- v6 independent validation: `INDEPENDENT-NO-GO`;
- v7 fresh development: `DEVELOPMENT-NO-GO`;
- v8 fresh development: `DEVELOPMENT-NO-GO`;
- v8 seeds `25101--25105`: permanently spent;
- no historical result may be relabelled by v9.

V9 is a separately versioned successor motivated by the sealed v8 post-development forensics.

## Motivation fixed before evidence

The sealed v8 evidence established three facts:

1. role-contrast identification and fixed source-pair isolation removed the v7 null-role and outside-role-safety failure modes;
2. `36/52` remaining true-deviation misses were selector failures, and `26/36` of those still improved held-out selector SSE directionally but failed the selector's standalone complexity-penalized score;
3. another `15/52` misses arose before complete certification because the deviation was absent from the response-driven bank or the source was banked but absent from the anchor.

V9 therefore changes **only** these two mechanisms: held-out evidence use and candidate/source availability. It does not relax the v8 role-contrast or fixed-pair safety invariants.

## Novelty boundary

The novelty audit in `research/TRANSACTIONS_SCSV_RCEF_V9_NOVELTY_AUDIT.md` is part of this freeze. V9 does not claim generic multi-level SR, personalization, privacy-preserving SR, multiple sample splitting, or evidence aggregation as new.

## Frozen seed namespaces

Repository collision search was performed before protocol freeze.

- engineering-only smoke seed: `26001`
- fresh development seeds, reserved and untouched at freeze: `26101, 26102, 26103, 26104, 26105`

Smoke seed must never appear in fresh-development evidence. Once a fresh v9 matrix starts, all `26101--26105` become permanently spent regardless of workflow outcome.

## Frozen anchor

V9 calls the frozen SCSV-Cert v6 anchor unchanged:

- score proposer enabled;
- shared-anchor cap: 6 terms including intercept;
- no v9 logic may delete or replace an anchor term;
- v9 augmentation is monotone with respect to the anchor structure.

## Frozen role rule

For candidate deviation `e`, let client `i` have response-free gate occupancy

`rho_i(e) = observed_support_i(e) / n_i`

computed on discovery packets only.

Among all partitions with role size at most half the clients, choose the deterministic largest occupancy gap with the existing tie rule. A role is admissible only when all hold:

- role and outside-role sets are both non-empty;
- occupancy gap >= `0.50`;
- mean role occupancy >= `0.75`;
- mean outside-role occupancy <= `0.25`.

These thresholds are inherited unchanged from v8 because they achieved zero null false-role hypotheses and zero null spurious-deviation acceptance on fresh v8 development.

No outcome value or truth label enters role identification.

## Response-free role-contrast proposal channel

V8 required a missing deviation to be present in the response-driven high-recall bank. V9 adds a second proposal route.

For every exception term in the frozen finite v9 grammar:

1. read its declared `source_term` metadata;
2. require the source term to be present in the frozen v6 high-recall bank;
3. compute the response-free discovery role rule above;
4. if the role is admissible, admit the exception as a **role-contrast proposal**, even when the exception itself is absent from the response-driven bank.

The operational candidate set is the deterministic union of:

- response-driven banked source-linked exceptions; and
- response-free role-contrast proposals whose source is in the bank.

Truth identity is never passed to this mechanism.

## Frozen coefficient-isolation rule

For every candidate deviation `e` with source `phi`, unrelated shared-anchor coefficients are frozen to the v6 discovery-anchor values.

Let `U` denote all frozen unrelated anchor terms.

### Shared-source estimate

On outside-role discovery packets only, estimate

`beta_phi = argmin_beta SSE_outside(U_fixed + beta * phi)`.

### Deviation estimate

On role discovery packets only, estimate

`delta_e = argmin_delta SSE_role(U_fixed + beta_phi * phi + delta * e)`.

No selector or probe packet is used in either estimate.

### Full and reduced deviation models

The fixed full model is

`M_full = U_fixed + beta_phi * phi + delta_e * e`.

The fixed reduced model is

`M_red = U_fixed + beta_phi * phi + 0 * e`.

The two models must have identical structures and coefficients except for the tested deviation coefficient, which is exactly zero in `M_red`.

Any violation is a fatal integrity error.

## Source qualification when the source is absent from the anchor

A role-contrast proposal is allowed when its source is in the v6 bank but absent from the final anchor. V9 must not silently insert that source.

For such a source `phi`:

1. estimate `beta_phi` using outside-role discovery packets with all anchor coefficients frozen;
2. define fixed source-full and source-zero models that differ only in `beta_phi`;
3. evaluate them only on outside-role selector/probe packets;
4. require the frozen evidence-fusion rule below to pass for the source itself.

Only a qualified source may support a deviation certificate.

A source that was absent from the anchor is added operationally **only together with at least one accepted linked deviation**. Source-only augmentation is not allowed in v9.

## Held-out evidence states

Discovery fixes all coefficients before held-out evidence is examined.

For each held-out view `h` in `{selector, probe}`, compute role support `N_h`, full SSE `F_h`, and reduced SSE `R_h`.

Define the per-view penalized score

`Delta_h = log(F_h / R_h) + log(N_h) / N_h`.

The view state is:

- `SUPPORTED` if `Delta_h < 0`;
- `INCONCLUSIVE-DIRECTIONAL` if `Delta_h >= 0` and `F_h < R_h`;
- `CONTRADICTED` if `F_h >= R_h`.

The same state rule is used for optional outside-role source qualification.

## Cross-view evidence fusion

V9 does not require the selector split alone to clear the complete complexity penalty.

After discovery has frozen the candidate pair, pool the two disjoint held-out views:

`N_pool = N_selector + N_probe`

`F_pool = F_selector + F_probe`

`R_pool = R_selector + R_probe`

and compute

`Delta_pool = log(F_pool / R_pool) + log(N_pool) / N_pool`.

A deviation passes held-out evidence **if and only if**:

1. selector state is not `CONTRADICTED`;
2. probe state is not `CONTRADICTED`;
3. `Delta_pool < 0`.

Thus weak but directionally consistent evidence may accumulate across the two held-out views, but an actual directional contradiction in either view vetoes acceptance.

No threshold is selected from v8 values; zero remains the frozen information-criterion boundary.

## Outside-role invariant

For deviation certification, `M_full` and `M_red` differ only in `e`. Because the role gate is zero outside role by construction, outside-role predictions should be identical up to numerical tolerance.

Selector and probe outside-role SSE equality is audited with tolerance `1e-10`. Any accepted deviation violating the invariant is a certificate failure.

For source qualification, source-full/source-zero models intentionally differ on outside-role data; therefore they use the evidence-fusion test rather than the deviation outside-role equality invariant.

## Ambiguity guards

- maximum newly accepted deviations per condition: 2;
- if more than one positive deviation is linked to the same source, reject all positives for that source (`source ambiguity`);
- if more than two deviations remain positive after source ambiguity, reject all new v9 deviations (`global ambiguity`);
- no ranking by truth, test error, or development performance is permitted.

## Operational final structure

The final v9 structure is the frozen v6 anchor plus:

- each accepted deviation;
- a qualified banked source only when that source was absent from the anchor and at least one linked deviation is accepted.

Maximum final size: 10 terms including intercept.

After the structural decision is frozen for a condition, a final coefficient refit on the available training partition is permitted. Test data never enters structural selection.

## V9 finite grammar and benchmark families

V9 uses a benchmark module separate from v8. It exposes all v9 exception candidates and distractors to every applicable family.

The four main deviation families use new source/gate combinations not used as v8 targets:

1. `quadratic_role_v9`: source `x2^2`, deviation `I(x2>0.85)*x2^2`;
2. `linear_role_v9`: source `x4`, deviation `I(x4<-0.85)*x4`;
3. `trig_role_v9`: source `sin(x3)`, deviation `I(x3<-0.85)*sin(x3)`;
4. `interaction_role_v9`: source `x1*x3`, deviation `I(x1>0.85)*x1*x3`.

Additional panels:

5. `null_role_v9`: source-rich null exposing every v9 deviation candidate;
6. `diffuse_null_v9`: diffuse within-client gate occupancy without a true client-level coefficient deviation;
7. `weak_source_role_v9`: a weak shared `x4^2` source with a stronger `I(x4>0.85)*x4^2` role deviation, designed to exercise the banked-source / missing-anchor path without truth information entering the algorithm;
8. `dual_role_v9`: two non-overlapping v9 role deviations with distinct sources.

All coefficients and generators are frozen in the benchmark module before engineering smoke.

## Fresh-development matrix

### Four main single-deviation families

For each family:

- clients: 4, 8, 16;
- balance: balanced, imbalanced;
- noise ratio: 0.10, 0.30;
- role profiles: 4 clients uses `single` only; 8 and 16 use `single` and `quarter`;
- seeds: `26101--26105`.

This gives `100` conditions per family, `400` total.

### Null family

3 client counts x 2 balances x 2 noise levels x 5 seeds = `60`.

### Diffuse-null family

Same = `60`.

### Weak-source family

Clients 8 and 16, quarter role only, 2 balances x 2 noise levels x 5 seeds = `40`.

### Dual family

Clients 8 and 16, quarter role only, 2 balances x 2 noise levels x 5 seeds = `40`.

### Total

Exactly `600` fresh scientific conditions.

## Frozen methods in the development study

Exactly six methods are evaluated per condition:

1. `scsv-rcef-v9-full`;
2. `scsv-rcef-v9-no-role-proposer` -- uses only response-driven banked deviations;
3. `scsv-rcef-v9-selector-only` -- retains v9 proposal/source logic but requires selector `Delta < 0` before probe, removing evidence fusion;
4. `scsv-spcc-v8-style` -- frozen v8 mechanism applied to the v9 grammar;
5. `scsv-v6-anchor`;
6. `centralized-forward`.

Planned rows: `600 x 6 = 3600`.

## Frozen development gates A--W

All 23 gates are required. One failure means `DEVELOPMENT-NO-GO`.

A. **Integrity:** exactly 600 matched fresh conditions, 3600 rows, seeds exactly `26101--26105`, smoke seed absent.

B. **Anchor monotonicity:** every v9 final structure contains every frozen anchor term.

C. **Null precision:** pooled spurious deviation acceptance across `null_role_v9` and `diffuse_null_v9` <= `0.02`.

D. **Zero exact harms:** zero conditions that are exact under `scsv-spcc-v8-style` become inexact under v9 full.

E. **Overall noninferiority:** v9 overall exact recovery >= matched v8-style exact recovery - `0.01`.

F. **Deviation-bearing exact gain:** v9 exact recovery on all true-deviation conditions >= v8-style + `0.04`.

G. **Deviation precision:** pooled v9 deviation precision >= `0.99`.

H. **Deviation recall:** pooled v9 deviation recall >= `0.93`.

I. **Main-family floor:** each of the four main single-deviation families has recovery >= `0.90`.

J. **Weak-source recovery:** `weak_source_role_v9` true-deviation recovery >= `0.80`.

K. **4-client recovery:** main-family 4-client recovery >= `0.88`.

L. **8-client recovery:** main-family 8-client recovery >= `0.90`.

M. **16-client recovery:** main-family 16-client recovery >= `0.94`.

N. **High-noise recovery:** main-family noise-0.30 recovery >= `0.88`.

O. **Imbalance robustness:** imbalanced main-family recovery >= balanced recovery - `0.06`.

P. **Dual recovery:** both true deviations recovered in >= `0.90` of dual conditions, with zero nontruth deviation accepted among dual rows where both truths are recovered.

Q. **Role-contrast integrity:** every operational v9 deviation has a non-empty role and outside-role client set and satisfies the frozen occupancy thresholds.

R. **Source qualification integrity:** every operational source absent from the anchor was present in the v6 bank and passed outside-role source evidence fusion; zero source-qualification violations.

S. **Pair invariant:** every operational deviation full/reduced pair differs only in the tested deviation coefficient; zero violations.

T. **Evidence-fusion integrity:** every accepted deviation has selector and probe states not `CONTRADICTED` and pooled `Delta < 0`; zero violations.

U. **Mechanism superiority:** deviation-bearing exact recovery of v9 full >= v9 selector-only + `0.01` **or**, if selector-only already reaches `0.95`, v9 full must be noninferior within `0.005`. This gate tests that evidence fusion is useful without punishing a ceiling result.

V. **Communication:** median v9 communication <= `1.75x` matched v8-style communication.

W. **Runtime:** median v9 runtime <= `2.25x` matched v8-style runtime.

No gate may be relaxed after any `261xx` seed is exposed.

## Engineering firewall

Before fresh development can start, all must pass at the exact implementation SHA:

1. historical v6/v7/v8 evidence files and hashes unchanged;
2. unit tests for response-free role proposer;
3. forced path where deviation is absent from response-driven bank but proposed from X-only role contrast;
4. forced path where source is in bank but absent anchor and passes source qualification;
5. forced path where source qualification fails and blocks the deviation;
6. selector/probe pooled evidence acceptance path;
7. contradiction veto from selector;
8. contradiction veto from probe;
9. pair-invariant test;
10. null and diffuse-null rejection paths;
11. dual-deviation acceptance;
12. source-ambiguity and global-ambiguity guards;
13. engineering smoke using only seed `26001`;
14. complete repository regression.

Fresh `261xx` seeds remain untouched until the firewall is green.

## Scientific boundary after development

- `DEVELOPMENT-GO` authorizes only design and freeze of a separately versioned independent-v9 protocol with a new untouched seed namespace.
- `DEVELOPMENT-NO-GO` permanently spends `26101--26105`; only clearly labelled spent-data forensics are allowed.
- Neither outcome authorizes retroactive confirmation of v6, v7, or v8.
- External SRSD or other external confirmation remains blocked until a successor passes its own independent validation.