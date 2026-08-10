# SCSV-RCD v7 post-development forensics

## Scientific boundary

This document is a read-only forensic analysis of the sealed fresh-development evidence for FedFalsify v7 / SCSV-RCD. It does **not** alter the v7 algorithm, benchmark grammar, A--R gates, thresholds, seeds, or the sealed DEVELOPMENT-NO-GO decision.

The fresh development seeds `24101--24105` are permanently spent. No result in this report authorizes retuning v7 on those seeds, independent-v7 evidence, or external SRSD confirmation. Any successor must be separately versioned and preregistered before any new seed is exposed.

## Provenance

- Frozen run source: `bd85a1d8990fc504908c8950547f59351ca6949e`
- Workflow run: `31395774823`
- Sealed evidence commit: `c295727cc781fb64ff038b4640e655f5eaee56c0`
- Artifact: `scsv-rcd-v7-development-evidence`
- Artifact ID: `9069609841`
- Artifact digest: `sha256:e1b2d946c3bfb496f3b7b89d200c0ca26282473711270eda3fb9ea995a4e8156`
- Rows: `2900`
- Scientific conditions: `580`
- Sealed decision: `DEVELOPMENT-NO-GO`

The sealed output hashes remain:

- `rows.csv`: `7c586cfd353726ea4e251b9ecebd1c95b9990a7d38201253d45d13c263a3f31c`
- `summary.json`: `27ffffd7c5f9c5820032ab9a218946e381de840d8b805586afdf7325de1ecefe`
- `decision.json`: `88860b9ca0b4e5fadc2a53515c5875fdf20fc39c87eb90e1cd15553bf4744164`
- `manifest.json`: `68725dc36f0616568a8b27cfc7e20b281ca3a76d6940428842836add2c75563d`

## Frozen development outcome

SCSV-RCD v7 improved exact structural recovery from `0.7086206897` for the frozen v6 anchor to `0.7758620690`, and improved exact recovery on deviation-bearing conditions from `0.6769230769` to `0.7557692308`. Pooled deviation precision was `0.996`, while pooled deviation recall was `0.8892857143`.

The all-or-nothing development decision was nevertheless NO-GO because gates D, H, I, J, and N failed:

- exact harms: `2`
- deviation recall: `0.8892857143 < 0.90`
- trig-role recovery: `0.75 < 0.85`
- 4-client recovery: `0.7875 < 0.85`
- high-noise recovery: `0.7583333333 < 0.85`

The following important safety/scaling gates passed: null spurious-deviation control, overall noninferiority, deviation precision, 8-client recovery, 16-client recovery, imbalance gap, dual-deviation recovery, certificate integrity, communication, and runtime.

## Term-level transition from v6 to v7

Across the 580 conditions there are `560` true role-deviation instances. The frozen v6 anchor recovered `449` of them and missed `111`.

SCSV-RCD v7:

- preserved all `449/449` true deviations already recovered by v6;
- rescued `49/111` previously missed true deviations;
- left `62/111` v6 deviation misses unresolved;
- lost **zero** previously recovered true deviations.

Therefore the two exact harms were not caused by deletion of a true v6 term. They were caused by false-positive augmentation in otherwise exact v6 cases.

The v7 augmentation layer accepted `51` deviations in total: `49` were true rescues and `2` were false positives.

## Exact-harm autopsy

Both exact harms are the same structural failure repeated across the two noise levels:

| Family | Clients | Balance | Role profile | Seed | Noise | False accepted term |
|---|---:|---|---|---:|---:|---|
| `null_role` | 8 | balanced | none | 24101 | 0.10 | `I(x1>1)*x1` |
| `null_role` | 8 | balanced | none | 24101 | 0.30 | `I(x1>1)*x1` |

In both rows, v6 was exactly correct with `sin(x2);x1;x3^2`. v7 added `I(x1>1)*x1`. Selector and probe conditional scores were both negative, so the false deviation passed the frozen certificate and became the only source of the exact harm.

The selector/probe deltas were nearly identical across the two noise levels because the same deterministic seed/geometry was used and the change in noise scale preserved the relative contrast.

### Mechanistic interpretation

The current v7 role detector `_role_indices` defines an eligible client from **observed support of the gated basis**, not from a separately identified client-level role. In `null_role`, naturally occurring observations can satisfy `x1>1`, so all eight clients can be treated as eligible even though the data-generating process has no coefficient deviation. With no outside clients left for this candidate, the outside-role check becomes vacuous for that false role hypothesis.

This is a distinct false-positive pathway and should not be confused with the recall failure described below.

## Anatomy of the 62 unresolved true deviations

The 62 residual true-deviation misses decompose exactly as follows:

| Failure stage | Count | Share of residual misses |
|---|---:|---:|
| selector outside-role safety failure | 28 | 45.16% |
| probe outside-role safety failure | 17 | 27.42% |
| source term missing from frozen anchor | 6 | 9.68% |
| probe conditional-evidence failure | 4 | 6.45% |
| selector conditional-evidence failure | 4 | 6.45% |
| deviation absent from candidate bank | 3 | 4.84% |

Thus `45/62 = 72.58%` of the residual misses are caused by **outside-role safety rejection**, not by missing discovery candidates and not by the conditional evidence test itself.

Upstream discovery/source-linking accounts for only `9/62` misses (`3` bank misses + `6` missing source anchors).

## Why the outside-role gate is the dominant failure

The frozen v7 implementation builds a `full` discovery model by fitting the entire anchor plus all source-linked candidate deviations through `_fit_from_packets`. The reduced comparator zeros only the tested deviation coefficient, but the full model itself was obtained after jointly re-estimating the shared-anchor coefficients.

In the fresh matrix the number of source-linked candidates was never greater than one per condition. Therefore the observed outside-role failures cannot be attributed to competition among multiple simultaneously added deviations. The principal remaining explanation is **shared/core coefficient drift introduced by the joint full-model refit**.

This conclusion is reinforced by the conditional scores of the rejected true deviations:

- For the `28` selector-outside failures, the selector conditional delta had median `-1.2152` and ranged from `-3.9905` to `-0.0207`. These are positive structural signals under the frozen `< 0` rule, yet the candidates were rejected because outside-role SSE increased.
- For the `17` probe-outside failures, selector delta had median `-0.6458` and probe delta median `-0.6911`; both conditional tests typically supported the true deviation. They were rejected only because probe outside-role SSE increased.

Median selector outside-SSE increase among selector-outside failures was approximately `+1.8356`; median probe outside-SSE increase among probe-outside failures was approximately `+0.5244`.

The current implementation therefore partially reintroduces the same class of confounding that earlier post-independent work tried to isolate: a role-specific candidate is judged together with changes in shared coefficients, so outside-role degradation can be caused by the shared refit rather than by the candidate deviation itself.

## Probe ablation: important but secondary

The no-probe ablation improved:

- exact recovery: `0.7758620690 -> 0.8051724138`
- deviation recall: `0.8892857143 -> 0.9267857143`

At the term level, the no-probe variant recovered exactly `21` of the `62` true deviations missed by full v7.

Those `21` are precisely:

- `4` probe conditional-evidence failures;
- `17` probe outside-role safety failures.

It did **not** rescue any bank miss, source-anchor miss, selector-evidence failure, or selector-outside-safety failure.

Therefore the probe is a real sensitivity cost, but it is not the primary mechanism. Even without the probe, `41` true-deviation misses remain; `28/41 = 68.29%` of those are selector-side outside-role safety failures.

Deleting the probe would therefore be an incomplete successor strategy and would not address the dominant failure pathway.

## Family anatomy

Residual true-deviation misses by family:

| Family | True-deviation instances | Misses | Recovery |
|---|---:|---:|---:|
| interaction role | 120 | 5 | 0.9583 |
| linear role | 120 | 12 | 0.9000 |
| quadratic role | 120 | 13 | 0.8917 |
| trig role | 120 | 30 | 0.7500 |
| dual role | 80 | 2 | 0.9750 |

The `trig_role` family contributes `30/62 = 48.39%` of all residual misses.

Its 30 misses decompose into:

- selector outside-role safety: `10`
- probe outside-role safety: `12`
- selector conditional evidence: `4`
- probe conditional evidence: `4`

So `22/30 = 73.33%` of trig misses are again outside-role-safety failures. The trig weakness is therefore not simply a weak trigonometric candidate-bank problem.

## Noise anatomy

The noise concentration is extreme:

- noise 0.10: `2/62` misses
- noise 0.30: `60/62` misses

Thus `96.77%` of residual misses occur at the high-noise setting.

The two low-noise misses are both the same 4-client balanced quadratic condition duplicated by the single/quarter role labels and rejected by selector outside-role safety despite very strong negative selector/probe deltas.

High noise therefore magnifies the shared-refit/outside-safety instability and the smaller conditional-evidence failures.

## Client-count anatomy

Residual misses by client count:

| Clients | Misses |
|---:|---:|
| 4 | 34 |
| 8 | 16 |
| 16 | 12 |

The 4-client misses decompose into `18` selector outside-safety, `6` probe outside-safety, `4` probe evidence, `2` selector evidence, and `4` source-anchor misses.

This is consistent with the failed 4-client recovery gate (`0.7875`): the smallest federation gives the least stable cross-role separation and the greatest sensitivity to shared-coefficient movement.

## 4-client role-profile redundancy

A design redundancy was found in the fresh matrix. For `num_clients=4`, both role profiles map to one eligible client:

- `single` -> 1 eligible client
- `quarter` -> `max(1, 4//4) = 1` eligible client

For the four single-deviation families, this creates `80` single/quarter pairs whose data, predictions, structures, diagnostics, NMSE, and train MSE are identical; only the role-profile label differs. The sealed gate correctly counted them as distinct preregistered condition keys, so the official DEVELOPMENT-NO-GO must not be changed retrospectively.

However, these are not independent data-generating geometries and they double-weight the 4-client one-role setting in pooled metrics.

A descriptive de-duplication that keeps only one of each identical 4-client single/quarter pair leaves `500` unique data-generating geometries and yields approximately:

- exact recovery: `0.8080`
- deviation precision: `0.9954`
- deviation recall: `0.90625`
- high-noise recovery: `0.8000`
- 4-client recovery: `0.7875`
- trig-role recovery: `0.7800`

These descriptive values do **not** overturn the NO-GO: 4-client, trig-role, high-noise, and exact-harm problems remain. The finding should instead change the design of any future protocol so logically identical role geometries are not counted twice.

## Dominant mechanism conclusion

The v7 failure is not best described as “the probe is too strict.” The evidence supports a more precise hierarchy:

1. **Primary residual bottleneck:** outside-role safety is evaluated on a jointly refitted full model, so shared/core coefficient drift can reject a true role deviation even when its conditional selector/probe evidence is strong. This accounts for `45/62` residual misses.
2. **Secondary bottleneck:** requiring an independent probe removes another `21` true deviations relative to no-probe, but most of these (`17/21`) are again outside-role-safety failures rather than direct contradiction by the probe.
3. **Small upstream component:** only `9/62` residual misses are due to bank/source-anchor incompleteness.
4. **Separate precision failure:** the two exact harms come from a null-role false-positive pathway in which support-based eligibility treats naturally occurring gated samples as a role and leaves no true outside-role clients for falsification.
5. **Stress concentration:** `60/62` residual misses occur at 30% noise, and `30/62` occur in the trig family.

## Successor hypothesis permitted by these forensics

No successor is authorized by this report alone, but the evidence supports a specific design hypothesis for preregistration:

**Do not test a role deviation using a globally re-estimated full anchor.** A successor should isolate the source/deviation contrast while preventing unrelated shared coefficients from moving during the conditional certificate.

A principled candidate design would:

1. freeze all unrelated shared-anchor coefficients;
2. use non-role evidence to identify the shared source coefficient;
3. use eligible-role evidence to identify the additional source-linked deviation coefficient;
4. evaluate selector/probe evidence on this constrained source-pair contrast rather than on a full shared-model refit;
5. define role eligibility from cross-client distributional concentration/contrast rather than merely nonzero sample support of a gated basis;
6. retain an independent certificate, but distinguish direct contradiction from weak/inconclusive evidence instead of simply deleting the probe;
7. avoid duplicate role geometries in the next preregistered matrix.

This is a mechanism hypothesis, not a tuned v8 rule. Thresholds, exact equations, admissibility rules, and a new seed namespace must be frozen in a separately versioned protocol before any new evidence is generated.

## Required next step

The scientifically correct next step is **successor design on paper only**: specify a constrained source-pair / cross-role certificate, prove its invariants, define null-role protection, preregister a nonredundant benchmark matrix and all-or-nothing gates, then perform engineering smoke on a new engineering-only seed. Fresh successor seeds must remain untouched until that protocol and implementation pass the complete pre-evidence firewall.
