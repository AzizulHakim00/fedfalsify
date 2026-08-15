# FedFalsify v11: SCSV-ELRC protocol

## Canonical name

**FedFalsify v11: Set-Conditional Structural Verification with Effect-Localized Role Certification (SCSV-ELRC)**

## Current authorization state

**ENGINEERING-ONLY / FRESH DEVELOPMENT BLOCKED.**

The v11 implementation and engineering smoke are preserved, but `29101--29105` are not authorized for execution. A separate `research/SCSV_V11_DEVELOPMENT_AUTHORIZATION.md` must be created only after the successor rationale is reconciled with the sealed v10 post-development forensic report.

This is Protocol Amendment A. It was made after the engineering-only `29001` smoke and before any `291xx` run. No v11 fresh-development result was available or used when making this amendment. Scientific thresholds below are retained rather than tuned from the smoke.

## Scientific status and forensic correction

V11 is a separately versioned successor to the sealed v10 `DEVELOPMENT-NO-GO`. V10 code, rows, summaries, and seeds remain frozen and are not relabeled.

The initial v11 hypothesis separated gate occurrence from response-effect localization and introduced provenance-only weak source heredity. The subsequently sealed read-only v10 post-development forensic decomposition materially corrected the motivation:

- 520 true deviation instances were present;
- 481 were recovered and 39 were missed;
- 34 misses were pooled-evidence failures;
- 5 misses were source-qualification failures;
- 0 misses were true-deviation occupancy-role failures;
- 57 additional exact-recovery failures occurred even though every true deviation was recovered, exposing a shared/core-anchor structural ceiling.

Therefore **effect-localized role discovery is retained only as a new mechanism hypothesis, not as the demonstrated dominant correction to v10**. Weak source heredity directly targets the five observed source-qualification misses. The current v11 draft does not yet directly solve the dominant high-noise pooled-evidence boundary or the shared/core-anchor ceiling, so fresh development is blocked until those mechanisms are explicitly reconciled and separately ablated.

## Seed firewall

- engineering-only smoke: `29001`;
- reserved fresh development: `29101, 29102, 29103, 29104, 29105`;
- v10 `28001` and `28101--28105` are forbidden;
- reserved final-confirmation `11001+` remains untouched.

The `291xx` namespace may be executed only through the guarded development workflow after a separate authorization document is committed. Starting any `291xx` development run permanently spends all five development seeds regardless of outcome.

## Frozen anchor and quarantine

V11 calls the unchanged v6 SCSV-Cert anchor with score proposer enabled and the same six-term shared-anchor cap. Ordinary anchor terms (`kind != 'exception'`) are immutable in the present v11 implementation. Anchor exception terms are quarantined and must be re-certified by v11 before becoming operational.

The sealed v10 forensics show that ordinary-anchor immutability is itself a likely total exact-recovery ceiling. This limitation must be explicitly addressed before fresh v11 authorization; it cannot be hidden by exception-layer gains.

## Candidate provenance

A v11 exception candidate must have a declared `source_term` and satisfy at least one structural-provenance path:

1. the source is in the ordinary/core anchor; or
2. the source is present in the v6 high-recall bank.

This is **weak structural heredity**. A source that is banked but not globally operational is provenance-only; it is not automatically inserted into the final global equation.

This mechanism is directly aligned with the five sealed v10 source-qualification misses, all of which occurred at noise ratio `0.30`.

## Gate occupancy is only an estimability guard

For candidate exception `e`, gate/nonzero support is used only to determine whether a local fold has enough active observations to estimate `e`.

For every held-out discovery fold:

- held-out active rows must be at least `2`;
- the four training folds must contain at least `8` active rows.

Gate occupancy never directly defines the client role.

This role mechanism is exploratory in v11 because sealed v10 forensics found zero true-deviation misses caused by occupancy-role failure.

## Five-fold discovery-only effect localization

The existing discovery partition of each client is deterministically split into five folds. For client `k` and held-out fold `f`:

1. freeze all ordinary core-anchor coefficients;
2. estimate only the candidate deviation coefficient on the other four discovery folds;
3. evaluate raw held-out improvement on fold `f`:

`g_kf = SSE_reduced(k,f) - SSE_full(k,f)`.

The fold is positive iff `g_kf > 0`.

A client is **effect-supported** iff all frozen conditions hold:

- at least `4/5` folds are estimable;
- at least `4/5` folds have positive held-out gain;
- median held-out gain is positive;
- coefficient-sign agreement across estimable folds is at least `0.80`.

Selector and probe data are not used during role discovery.

## Localized role rule

The role is the deterministic set of effect-supported clients. It is admissible only when:

- at least one client is effect-supported;
- at least one outside-role client remains;
- the role contains at most half of all clients.

If more than half the clients show stable effect, the candidate is not treated as a localized exception. This is a global-scope ambiguity guard, not a negative claim about the underlying variable.

## Final discovery pair

After role localization, estimate one deviation coefficient using all discovery packets from the inferred role while freezing the ordinary core anchor. FULL and REDUCED models must be identical in every term/coefficient except the tested deviation, which is exactly zero in REDUCED.

A source that is provenance-only does not receive a global coefficient merely to enable its child.

## Independent held-out certification

The current v11 implementation retains the frozen v10 selector/probe architecture. On inferred role clients compute:

`Delta_pool = log((F_s + F_p)/(R_s + R_p)) + log(N)/N`.

For each role client combine selector and probe raw improvements:

`g_i = (R_s,i - F_s,i) + (R_p,i - F_p,i)`.

The held-out certificate requires:

- `Delta_pool < 0`;
- median client gain `G_med > 0`.

There is no separate selector/probe direction veto in the v11 primary method.

**Known unresolved boundary:** the sealed v10 forensic report attributes 34 of 39 missed true deviations to this pooled-evidence stage, with 31 of those 34 occurring at noise `0.30`. The current v11 implementation retains that stage and therefore is not yet scientifically aligned enough to spend fresh development seeds. A pre-development reconciliation must add or replace the evidence-power mechanism without weakening the observed v10 false-positive control, and must preregister the corresponding ablation.

## Outside-role non-degradation

The tested deviation must not worsen aggregate selector or probe SSE on outside-role clients (numerical tolerance inherited from v8/v10). Pair-invariant failure or outside-role degradation rejects the candidate.

## Ambiguity guards

- maximum operational exceptions: `2`;
- maximum final structure size: `10` including intercept;
- multiple positive exceptions linked to the same source are all rejected for source ambiguity;
- more than two surviving positive exceptions triggers global ambiguity and rejects all new exceptions;
- ordinary anchor terms may never be deleted in the current implementation.

## Spent-v10 forensic use

`src/fedfalsify/scsv_v11_forensics.py` may read only sealed v10 rows on `28101--28105` and produce a descriptive failure taxonomy. It must never regenerate those conditions or be represented as v11 evidence.

The canonical detailed forensic interpretation is `research/TRANSACTIONS_SCSV_AQCC_V10_POST_DEVELOPMENT_FORENSICS.md`; if a simplified v11 diagnostic conflicts with that report, the sealed canonical report governs the scientific rationale.

## Reserved fresh-development matrix

If and only if a separate authorization is later committed, the v11 development matrix reuses the frozen v10 benchmark grammar but uses new seeds. It contains 600 matched conditions spanning:

- quadratic, linear, trigonometric, and interaction role deviations;
- 4, 8, and 16 clients;
- single and quarter roles where admissible;
- balanced and imbalanced client sizes;
- noise ratios `0.10` and `0.30`;
- null and anchor-contamination null families;
- weak-source and dual-deviation families.

Every fresh condition would run v11 and the frozen v10 method as a matched comparator on the same new data.

## Reserved development GO/NO-GO gates

These gates are retained as predeclared targets but **are not currently authorized for evaluation**:

- 600 unique fresh conditions using exactly `29101--29105`;
- zero implementation/integrity violations;
- pooled deviation precision >= `0.99`;
- pooled deviation recall >= `0.95`;
- null spurious-deviation acceptance <= `0.02`;
- zero exact-recovery harms relative to matched v10 successes;
- overall exact-recovery gain >= `0.02` versus fresh-seed v10 comparator;
- deviation-subset exact-recovery gain >= `0.04`;
- each main family recovery >= `0.92`;
- 4-client recovery >= `0.90`;
- 8-client recovery >= `0.93`;
- 16-client recovery >= `0.95`;
- high-noise recovery >= `0.90` and >= v10 by `0.03`;
- weak-source recovery >= `0.85`;
- dual-both recovery >= `0.90`;
- median communication and runtime each <= `8x` matched v10.

A future authorization must additionally preregister distinct ablations for:

1. high-noise evidence-power correction;
2. provenance-only weak heredity;
3. effect-localized role discovery;
4. shared/core-anchor re-certification or repair.

A GO would authorize only a separately frozen independent-validation protocol using a new untouched seed namespace. A NO-GO permanently spends `29101--29105` and forbids retuning on them.

## Claim boundary

Permitted now:

> V11 is an engineering-verified draft mechanism that separates gate estimability from response-effect localization and implements provenance-only weak heredity while preserving independent held-out certification.

> Sealed v10 forensics show that the dominant remaining measured sensitivity boundary is high-noise pooled evidence, with a smaller source-qualification boundary and a separate shared/core-anchor exact-recovery ceiling.

Not permitted now:

- describing occupancy-role failure as the dominant measured v10 failure;
- v11 superiority;
- spending `29101--29105` before a separate authorization document exists;
- final Transactions readiness;
- universal symbolic recovery;
- causal interpretation of client roles;
- privacy guarantees beyond the existing communication architecture;
- use of `11001+` final-confirmation seeds.
