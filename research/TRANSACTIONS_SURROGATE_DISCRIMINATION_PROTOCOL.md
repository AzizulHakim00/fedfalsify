# Transactions structure-aware surrogate-discrimination protocol

Status: **completed frozen development protocol; scientific gate failed**

The protocol below was frozen before outcomes were inspected. Complete findings
are archived in `research/TRANSACTIONS_SURROGATE_DISCRIMINATION_FINDINGS.md`.
Development seeds `14001--14005` are spent and may not be reused.

## Objective

Develop a second cross-fitted redesign that addresses the frozen Study G failure:
ordinary held-out prediction error did not distinguish high-noise polynomial truth
from correlated finite-catalog surrogates. This was a development study, not final
confirmation.

## Immutable evidence boundary

The following were not modified or rerun:

- v0.6 confirmation seeds `9001--9020`;
- official PySR validation seeds `10501--10505`;
- cross-fit redesign v1 seeds `13001--13005`;
- Beijing and SRSD external artifacts;
- untouched final-confirmation seeds `11001+`.

Development seeds for this protocol were `14001--14005` only.

## Algorithm v2

The redesign retained v1's disjoint local discovery/certificate folds and removed
raw score-only search from structural candidate selection.

Each client was partitioned into:

- 35% direction-A fit / direction-B certificate;
- 35% direction-B fit / direction-A certificate;
- 15% validation selector;
- 15% independent structural probe.

Candidate term sets were restricted to:

- cross-fit intersection;
- direction A;
- direction B;
- cross-fit union.

A non-intersection candidate first had to pass the frozen v1 prediction gates on
the validation selector: at least 1% weighted-MSE improvement, improved
complexity-adjusted score, no more than 5% worst-client degradation, and
non-degradation on at least 60% of clients.

It then had to pass an independent structural-surrogate gate on the probe. For
every added term:

1. correlated inactive rivals were identified without probe outcomes;
2. marginal coefficients were estimated only on selector rows after
   residualizing against the intersection model;
3. those frozen coefficients were evaluated on probe rows;
4. the proposed term had to reduce aggregate probe SSE;
5. it had to beat the strongest correlated rival by at least 1% relative probe
   SSE;
6. it had to beat that rival on at least 60% of observable clients;
7. selector coefficient signs had to agree across at least 60% of observable
   clients.

If any added term failed, the candidate was rejected. Raw score-only search was a
predictive comparator only and could never supply structure.

## Frozen development matrix

- benchmarks: `base`, `poly3`, `nested_sine`, `trig_product`, `interaction`;
- scenarios: complementary, spurious, restricted exception;
- noise ratios: `0.03`, `0.10`, `0.20`;
- samples per client: `120`, `300`;
- clients: `4`;
- seeds: `14001--14005`;
- methods: legacy certificate, cross-fit v1 governed, cross-fit v2 structural,
  score-only predictive comparator, centralized upper bound, and paired v2
  intersection diagnostic.

The artifact contains 450 conditions and 2,700 rows. All failures were retained.

## Primary development endpoints

1. exact structural recovery;
2. exact recovery on the frozen high-noise `poly3` and `interaction` subset;
3. test NMSE;
4. spurious-term acceptance;
5. restricted-exception recovery;
6. structural-probe decisions and rival identities;
7. paired gains/harms relative to the v2 intersection;
8. runtime and communication.

## Frozen go/no-go gate

V2 could advance only if all conditions held:

- overall exact recovery no more than 0.02 below legacy;
- high-noise `poly3`/`interaction` exact recovery exceeded both legacy and v1 by
  at least 0.05;
- spurious acceptance no more than 0.01 above legacy;
- exception recovery at least 0.97;
- no raw score-only structural source;
- zero observed exact harms from structural continuation;
- runtime below 15x and communication below 30x legacy.

## Completed decision

The gate failed.

- overall exact recovery: v2 `0.6800`, legacy `0.7133` — non-inferiority failed;
- high-noise `poly3`/`interaction`: v2 `0.3333`, legacy `0.3333`, v1 `0.3667` —
  both required gains failed;
- spurious acceptance: v2 `0.0000` — passed;
- exception recovery: v2 `0.9778` — passed;
- continuation exact harms: `0` — passed;
- runtime ratio: `1.98x`; communication ratio: `2.18x` — passed.

**Decision: NO-GO for external evaluation or final confirmation.**

The independent probe was safe when activated: 65 activations produced 23 exact
gains, zero exact harms, and 65 test-NMSE improvements. The primary failure was
upstream candidate generation. Cross-fit intersection/directional candidates
frequently omitted the cubic term before the probe could compare it with a
surrogate. In `poly3`, v2 was 21.11 percentage points below legacy overall.
Therefore probe thresholds may not be loosened post hoc; a future redesign must
change stable candidate generation using fresh development seeds.

## Governance

- workflow run: `31020422813`;
- final artifact: `surrogate-discrimination-v2-final`;
- artifact ID: `8936544092`;
- digest: `sha256:4763a6825be0a71ae8bd1819e9334519a3dbb274dedcd3c40360d8c424bc98d5`;
- 450 matched conditions / 2,700 rows;
- no external or final-confirmation evidence was modified;
- seeds `14001--14005` are spent;
- completed workflow is frozen/manual-only;
- PR remains draft and unmerged.