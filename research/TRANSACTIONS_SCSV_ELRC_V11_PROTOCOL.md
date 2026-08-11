# FedFalsify v11: SCSV-ELRC protocol

## Canonical name

**FedFalsify v11: Set-Conditional Structural Verification with Effect-Localized Role Certification (SCSV-ELRC)**

## Scientific status

This is a separately versioned successor to the sealed v10 `DEVELOPMENT-NO-GO`. V10 code, rows, summaries, and seeds remain frozen and are not relabeled.

V11 is motivated by spent-v10 forensics showing that the remaining boundary is dominated by false negatives: v10 preserved deviation precision at 1.00 and spurious-deviation acceptance at 0.00, but missed true deviations when gate occupancy did not identify the response-effect role and when a role-specific child depended on a parent that was not globally qualified.

## Seed firewall

- engineering-only smoke: `29001`;
- fresh development: `29101, 29102, 29103, 29104, 29105`;
- v10 `28001` and `28101--28105` are forbidden;
- reserved final-confirmation `11001+` remains untouched.

The `291xx` namespace may be executed only through the guarded development workflow after v11 implementation tests and the `29001` smoke pass. Starting any `291xx` development run permanently spends all five development seeds regardless of outcome.

## Frozen anchor and quarantine

V11 calls the unchanged v6 SCSV-Cert anchor with score proposer enabled and the same six-term shared-anchor cap. Ordinary anchor terms (`kind != 'exception'`) are immutable. Anchor exception terms are quarantined and must be re-certified by v11 before becoming operational.

## Candidate provenance

A v11 exception candidate must have a declared `source_term` and satisfy at least one structural-provenance path:

1. the source is in the ordinary/core anchor; or
2. the source is present in the v6 high-recall bank.

This is **weak structural heredity**. A source that is banked but not globally operational is provenance-only; it is not automatically inserted into the final global equation.

## Gate occupancy is only an estimability guard

For candidate exception `e`, gate/nonzero support is used only to determine whether a local fold has enough active observations to estimate `e`.

For every held-out discovery fold:

- held-out active rows must be at least `2`;
- the four training folds must contain at least `8` active rows.

Gate occupancy never directly defines the client role.

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

The frozen v10 selector/probe architecture is retained. On inferred role clients compute:

`Delta_pool = log((F_s + F_p)/(R_s + R_p)) + log(N)/N`.

For each role client combine selector and probe raw improvements:

`g_i = (R_s,i - F_s,i) + (R_p,i - F_p,i)`.

The held-out certificate requires:

- `Delta_pool < 0`;
- median client gain `G_med > 0`.

There is no separate selector/probe direction veto in the v11 primary method.

## Outside-role non-degradation

The tested deviation must not worsen aggregate selector or probe SSE on outside-role clients (numerical tolerance inherited from v8/v10). Pair-invariant failure or outside-role degradation rejects the candidate.

## Ambiguity guards

- maximum operational exceptions: `2`;
- maximum final structure size: `10` including intercept;
- multiple positive exceptions linked to the same source are all rejected for source ambiguity;
- more than two surviving positive exceptions triggers global ambiguity and rejects all new exceptions;
- ordinary anchor terms may never be deleted.

## Spent-v10 forensic use

`src/fedfalsify/scsv_v11_forensics.py` may read only sealed v10 rows on `28101--28105` and produce a descriptive failure taxonomy. It must never regenerate those conditions or be represented as v11 evidence.

## Fresh-development matrix

The v11 development matrix reuses the frozen v10 benchmark grammar but uses new seeds. It contains 600 matched conditions spanning:

- quadratic, linear, trigonometric, and interaction role deviations;
- 4, 8, and 16 clients;
- single and quarter roles where admissible;
- balanced and imbalanced client sizes;
- noise ratios `0.10` and `0.30`;
- null and anchor-contamination null families;
- weak-source and dual-deviation families.

Every fresh condition runs v11 and the frozen v10 method as a matched comparator on the same new data.

## Development GO/NO-GO gates

All gates must pass:

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

A GO authorizes only a separately frozen independent-validation protocol using a new untouched seed namespace. A NO-GO permanently spends `29101--29105` and forbids retuning v11 on them.

## Claim boundary

Before fresh development, permitted claim:

> V11 is a preregistered mechanism redesign that separates gate estimability from response-effect localization and replaces mandatory global parent inheritance with provenance-only weak heredity.

Not permitted before successful fresh development and independent validation:

- v11 superiority;
- final Transactions readiness;
- universal symbolic recovery;
- causal interpretation of client roles;
- privacy guarantees beyond the existing communication architecture;
- use of `11001+` final-confirmation seeds.
