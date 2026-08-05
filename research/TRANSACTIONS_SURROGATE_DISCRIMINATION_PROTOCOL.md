# Transactions structure-aware surrogate-discrimination protocol

Status: **frozen before v2 development outcomes are inspected**

## Objective

Develop a second cross-fitted redesign that addresses the frozen Study G failure:
ordinary held-out prediction error did not distinguish high-noise polynomial truth
from correlated finite-catalog surrogates. This is a development study, not final
confirmation.

## Immutable evidence boundary

The following are not modified or rerun:

- v0.6 confirmation seeds `9001--9020`;
- official PySR validation seeds `10501--10505`;
- cross-fit redesign v1 seeds `13001--13005`;
- Beijing and SRSD external artifacts;
- untouched final-confirmation seeds `11001+`.

Development seeds for this protocol are `14001--14005` only. After execution they
are spent and may not be reused for threshold tuning.

## Algorithm v2

The redesign retains v1's disjoint local discovery/certificate folds and removes
raw score-only search from structural candidate selection.

Each client is partitioned into:

- 35% direction-A fit / direction-B certificate;
- 35% direction-B fit / direction-A certificate;
- 15% validation selector;
- 15% independent structural probe.

Candidate term sets are restricted to:

- cross-fit intersection;
- direction A;
- direction B;
- cross-fit union.

A non-intersection candidate must first pass the frozen v1 prediction gates on the
validation selector: at least 1% weighted-MSE improvement, improved complexity-
adjusted score, no more than 5% worst-client degradation, and non-degradation on
at least 60% of clients.

It must then pass an independent structural-surrogate gate on the structural
probe. For every added term:

1. correlated inactive rivals are identified without using probe outcomes;
2. marginal coefficients are estimated only on selector rows after residualizing
   against the intersection model;
3. those frozen coefficients are evaluated on probe rows;
4. the proposed term must reduce aggregate probe SSE;
5. it must beat the strongest correlated rival by at least 1% relative probe SSE;
6. it must beat that rival on at least 60% of observable clients;
7. selector coefficient signs must agree across at least 60% of observable clients.

If any added term fails, the candidate is rejected. The intersection remains the
structural output. Raw score-only search may be reported only as a predictive
comparator and can never supply the discovered structure.

## Frozen development matrix

- benchmarks: `base`, `poly3`, `nested_sine`, `trig_product`, `interaction`;
- scenarios: complementary, spurious, restricted exception;
- noise ratios: `0.03`, `0.10`, `0.20`;
- samples per client: `120`, `300`;
- clients: `4`;
- seeds: `14001--14005`;
- methods: legacy certificate, cross-fit v1 governed, cross-fit v2 structural,
  score-only predictive comparator, centralized forward upper bound.

All conditions and failures are retained. No benchmark, scenario, or seed may be
removed after execution.

## Primary development endpoints

1. exact structural recovery;
2. exact recovery on the frozen high-noise `poly3` and `interaction` subset;
3. test NMSE;
4. spurious-term acceptance;
5. restricted-exception recovery;
6. structural-probe acceptance/rejection counts and rival identities;
7. runtime and communication.

## Frozen go/no-go gate

V2 advances to an independent external redesign study only if all conditions hold:

- overall exact recovery is not more than 0.02 below legacy;
- high-noise `poly3`/`interaction` exact recovery exceeds both legacy and v1 by at
  least 0.05;
- spurious acceptance is no more than 0.01 above legacy;
- exception recovery is at least 0.97;
- no raw score-only candidate is selected as structure;
- structural continuation has zero observed exact harms relative to the v2
  intersection on activated conditions;
- runtime is below 15x and communication below 30x legacy.

Failure of any criterion is a NO-GO. Thresholds may not be changed after results
are inspected.

## Claim boundary

A positive development result would support only the statement that an
independent probe gate improved finite-catalog surrogate discrimination within the
frozen synthetic matrix. It would not establish catalog-free discovery, causal
validity, formal privacy, external superiority, or Transactions readiness.
