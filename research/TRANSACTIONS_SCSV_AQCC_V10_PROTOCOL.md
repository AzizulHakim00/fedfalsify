# FedFalsify v10: SCSV-AQCC protocol

## Canonical name

**FedFalsify v10: Set-Conditional Structural Verification with Anchor Quarantine and Client Consensus (SCSV-AQCC)**

## Scientific status

This protocol is frozen before any v10 engineering smoke or fresh-development seed is executed.

Permanent historical boundaries:

- v6 independent validation: `INDEPENDENT-NO-GO`;
- v7 fresh development: `DEVELOPMENT-NO-GO`;
- v8 fresh development: `DEVELOPMENT-NO-GO`;
- original v9 fresh attempt on `26101--26105`: `INFRASTRUCTURE-CANCELLED / NO SCIENTIFIC VERDICT`;
- sharded v9 recovery on `27101--27105`: `DEVELOPMENT-NO-GO`;
- all historical development/recovery seeds remain permanently spent.

V10 is a separately versioned successor motivated only by the sealed v9 post-recovery forensic report. It does not relabel v9.

## Frozen seed namespaces

Repository collision search was performed before this protocol was frozen.

- engineering-only smoke: `28001`;
- fresh development: `28101, 28102, 28103, 28104, 28105`.

The smoke seed may never appear in fresh evidence. Once any fresh `281xx` matrix starts, all five development seeds become permanently spent regardless of workflow outcome.

## Frozen v6 anchor call

V10 calls the same v6 SCSV-Cert anchor with:

- score proposer enabled;
- maximum shared-anchor size 6 including intercept;
- unchanged target-MSE/min-repair-score interface;
- no truth or test data in selection.

The anchor is used as a proposal/starting structure, not as an irrevocable final structure for exception terms.

## Anchor classification

Each selected anchor term is classified from catalog metadata only.

### Ordinary shared/core anchor term

A term is ordinary when `kind != 'exception'`. Ordinary anchor terms are immutable in v10 and must remain in the final structure.

### Anchor exception term

A selected anchor term with `kind == 'exception'` and a declared `source_term` is placed in **quarantine**. It is not operationally inherited until re-certified.

This classification is response-independent once the anchor has been produced; no truth label enters it.

## Quarantined-anchor re-certification

Every quarantined anchor exception is tested exactly like a newly proposed deviation:

1. infer a response-free client role from discovery gate occupancy;
2. require a non-vacuous admissible role under the frozen v8/v9 occupancy rule;
3. require its declared source to be present in the v6 high-recall bank;
4. if the source is absent from the ordinary/core operational anchor, qualify the source on outside-role data;
5. estimate a fixed source/deviation pair on discovery packets only;
6. evaluate the pair with the frozen v10 client-consensus held-out certificate;
7. retain the exception only if the complete certificate passes.

A quarantined exception that fails any stage is removed from the operational final structure. This is the only permitted deletion path. Ordinary anchor terms can never be deleted.

## Frozen response-free role rule

For exception candidate `e`, client `i` has discovery occupancy

`rho_i(e) = observed_support_i(e) / n_i`.

Among role sizes up to half the clients, choose the deterministic largest adjacent occupancy gap, ties broken by smaller role size and lexical client IDs.

A role is admissible iff:

- role and outside sets are both non-empty;
- occupancy gap >= `0.50`;
- role mean occupancy >= `0.75`;
- outside mean occupancy <= `0.25`.

These thresholds are inherited unchanged from v8/v9 and are not tuned in v10.

## Candidate proposal union

The operational exception candidate set is the deterministic union of:

1. quarantined exceptions selected by the v6 anchor;
2. response-driven banked exceptions linked to a banked source;
3. response-free role-contrast proposals from the finite v10 grammar whose source is present in the v6 bank.

No truth identity is passed to proposal logic.

## Fixed source/deviation pair

For candidate exception `e` with source `phi`:

- freeze all unrelated ordinary/core anchor coefficients at v6 discovery-anchor values;
- estimate `beta_phi` on outside-role discovery packets only;
- estimate `delta_e` on role discovery packets only after fixing `beta_phi`;
- define FULL and REDUCED models that are identical in every term and coefficient except `delta_e`, which is exactly zero in REDUCED.

Any pair-invariant violation is fatal.

## Source qualification

If `phi` is absent from the operational ordinary/core anchor but present in the v6 bank, source qualification uses outside-role packets only.

The source-full/source-zero pair is frozen from discovery and is evaluated by the same v10 held-out pooled/client-consensus rule below, using outside-role clients as its evidence clients.

A source absent from both anchor and bank cannot be inserted. A qualified source may be added only together with at least one accepted linked exception.

## Fixed held-out packets

V10 retains the single predeclared partitioning architecture:

- discovery/fit packets;
- selector packets;
- probe packets.

V10 does **not** generate additional random resamples or repeated split searches after evidence begins.

## Pooled information criterion

For evidence clients `R`, let selector/probe full and reduced SSE be `F_s, R_s, F_p, R_p`, with total held-out support `N`.

`Delta_pool = log((F_s + F_p)/(R_s + R_p)) + log(N)/N`.

The pooled evidence requirement is `Delta_pool < 0`.

## Client-level contradiction persistence

For each evidence client `i`, compute fixed held-out raw improvement after combining selector and probe within that same client:

`g_i = (R_s,i - F_s,i) + (R_p,i - F_p,i)`.

Define

`G_med = median_i(g_i)`.

The client-consensus requirement is `G_med > 0`.

V10 full accepts held-out evidence iff both hold:

1. `Delta_pool < 0`;
2. `G_med > 0`.

There is no separate selector-state or probe-state veto in v10 full. A contradiction is persistent only when the client-combined median is non-positive or the pooled penalized evidence is non-supporting.

For a one-client role, `G_med` is that role client's combined selector+probe improvement. This removes arbitrary split direction as a separate veto while retaining held-out direction and complexity control.

## Split-veto ablation

The preregistered ablation `scsv-aqcc-v10-split-veto` uses the same quarantine/proposal/source logic but restores the v9 rule: selector and probe may not be `CONTRADICTED`, and pooled delta must be negative.

This ablation isolates the contribution of client-level contradiction persistence.

## Outside-role invariant

For deviation certification, FULL and REDUCED differ only in the gated exception coefficient. Outside-role predictions must therefore be identical up to numerical tolerance `1e-10` on selector and probe packets.

Any accepted deviation violating this invariant is a certificate failure.

## Ambiguity guards

- maximum newly operational exceptions after quarantine/certification: 2 beyond ordinary anchor terms;
- if more than one positive exception is linked to the same source, reject positives for that source;
- if more than two positive exception terms remain, reject all new/quarantined exceptions for that condition;
- no ranking by truth, test NMSE, or development performance.

## Final structure

Final structure =

- all ordinary/core v6 anchor terms;
- each quarantined anchor exception that passes v10 certification;
- each newly accepted exception;
- each separately qualified source required by an accepted exception.

Maximum final size: 10 terms including intercept. Final coefficient refit after structural decisions is allowed on training/validation data; test data never enters structural selection.

## Frozen v10 benchmark grammar

V10 uses a new finite grammar so fresh development does not simply repeat the exact v9 target gates.

1. `quadratic_role_v10`: source `x3^2`, exception `I(x3<-0.90)*x3^2`;
2. `linear_role_v10`: source `x1`, exception `I(x1<-0.90)*x1`;
3. `trig_role_v10`: source `cos(x2)`, exception `I(x2>0.90)*cos(x2)`;
4. `interaction_role_v10`: source `x1*x2`, exception `I(x2>0.90)*x1*x2`;
5. `null_role_v10`: source-rich null exposing all v10 exception candidates;
6. `anchor_contamination_null_v10`: no true role deviation, but a high-noise source/gate geometry intended to test whether an exception selected upstream is quarantined rather than inherited blindly;
7. `weak_source_role_v10`: weak shared `x4^2` source with exception `I(x4<-0.90)*x4^2`;
8. `dual_role_v10`: non-overlapping quadratic and linear role deviations with distinct sources.

The contamination panel is a falsification panel, not a tuning panel. Passing it requires the full frozen certificate, not term-name special casing.

## Fresh development matrix

### Four main single-deviation families

For each family:

- clients: 4, 8, 16;
- balance: balanced, imbalanced;
- noise ratio: 0.10, 0.30;
- role profiles: 4 clients uses `single`; 8 and 16 use `single` and `quarter`;
- seeds: `28101--28105`.

= 100 conditions per family, 400 total.

### Null and anchor-contamination-null

Each: 3 client counts x 2 balances x 2 noise levels x 5 seeds = 60.

= 120 total.

### Weak-source and dual

Each: clients 8/16, quarter role, 2 balances x 2 noise x 5 seeds = 40.

= 80 total.

### Total

Exactly **600 fresh conditions**.

## Frozen methods

Exactly six methods per condition:

1. `scsv-aqcc-v10-full`;
2. `scsv-aqcc-v10-no-quarantine` -- preserves anchor exceptions and tests only new exceptions with v10 consensus;
3. `scsv-aqcc-v10-split-veto` -- v10 quarantine with v9 selector/probe contradiction veto;
4. `scsv-rcef-v9-style` -- frozen v9 mechanism applied to the v10 grammar;
5. `scsv-v6-anchor`;
6. `centralized-forward`.

Planned rows: **600 x 6 = 3,600**.

## Frozen development gates A--Y

All 25 gates are required. One failure means `DEVELOPMENT-NO-GO`.

A. Integrity: exactly 600 conditions, 3,600 rows, seeds exactly `28101--28105`, smoke seed absent.

B. Ordinary-anchor preservation: every ordinary/core v6 anchor term remains in v10 final structure.

C. Quarantine integrity: every anchor-selected exception appearing in v10 final structure has a complete passing v10 certificate; zero uncertified inherited exceptions.

D. Null precision: pooled spurious deviation acceptance across `null_role_v10` and `anchor_contamination_null_v10` <= `0.02`.

E. Zero exact harms: zero conditions exact under matched v9-style that become inexact under v10 full.

F. Overall exact gain: v10 full overall exact recovery >= matched v9-style + `0.02`.

G. Deviation-bearing exact gain: v10 full exact recovery on true-deviation conditions >= matched v9-style + `0.04`.

H. Deviation precision: pooled v10 deviation precision >= `0.99`.

I. Deviation recall: pooled v10 deviation recall >= `0.95`.

J. Main-family floor: every one of the four main single-deviation families recovery >= `0.92`.

K. Weak-source recovery >= `0.85`.

L. Four-client main-family recovery >= `0.90`.

M. Eight-client main-family recovery >= `0.93`.

N. Sixteen-client main-family recovery >= `0.95`.

O. High-noise main-family recovery >= `0.90`.

P. Imbalance robustness: imbalanced main-family recovery >= balanced recovery - `0.05`.

Q. Dual both-recovered >= `0.90`, with zero nontruth deviations among dual rows where both truths are recovered.

R. Quarantine mechanism superiority: on `anchor_contamination_null_v10`, v10 full spurious-deviation rate <= `0.02` and at least `0.20` lower than `scsv-aqcc-v10-no-quarantine` unless the no-quarantine ablation is already <= `0.02`, in which case full must be noninferior.

S. Client-consensus mechanism superiority: on noise-0.30 true-deviation conditions, v10 full exact recovery >= split-veto ablation + `0.02`, or if split-veto already >= `0.95`, full must be noninferior within `0.005`.

T. Role integrity: zero accepted exceptions with vacuous/failed frozen role criteria.

U. Source-qualification integrity: zero unqualified inserted sources.

V. Pair invariant: zero accepted exceptions whose FULL/REDUCED pair differs outside the tested exception coefficient.

W. Client-consensus integrity: every accepted v10-full exception/source has negative pooled delta and strictly positive median client held-out improvement.

X. Communication: median v10 communication <= `1.85x` matched v9-style communication.

Y. Runtime: median v10 runtime <= `2.50x` matched v9-style runtime.

No gate may be altered after any `281xx` seed begins.

## Engineering firewall

Before fresh development all must pass at one exact implementation SHA:

1. historical v6/v7/v8/v9 evidence boundaries unchanged;
2. seed collision audit clean;
3. forced ordinary-anchor preservation;
4. forced contaminated anchor exception quarantine and removal;
5. forced true anchor exception re-certification and retention;
6. forced new role-proposed exception acceptance;
7. forced source qualification pass and fail;
8. forced client-consensus rescue where selector/probe directions disagree but within-client combined evidence is persistent;
9. forced client-median contradiction rejection;
10. pooled-delta rejection;
11. pair invariant and outside-role invariant;
12. null rejection;
13. dual acceptance;
14. source/global ambiguity guards;
15. engineering smoke using only `28001`;
16. full repository regression.

Fresh `281xx` seeds remain untouched until all firewall items are green.

## Post-development boundary

- GO authorizes only a separately frozen v10 independent-validation protocol with a new untouched seed namespace.
- NO-GO permanently spends `28101--28105`; only explicitly labelled spent-data diagnostics are allowed.
- Neither outcome authorizes retroactive confirmation of v6-v9 or historical external studies.
