# HR-VFS v5 sealed-evidence forensic analysis

Status: **post-hoc diagnostic analysis of sealed v5 evidence; v5 remains frozen NO-GO**.

This document analyzes the already-sealed HR-VFS v5 development artifact produced by workflow run `31271593515` at pinned source commit `6d4278c947d71f6e28a64f71a2c4b2e1101b7d01`. The retained matrix contains 4,500 rows = 450 matched conditions x 10 methods on spent seeds `17101--17105`. No result in this document changes the frozen v5 decision, thresholds, ordering, or gate.

## 1. Frozen decision

HR-VFS v5 failed 7 of 15 preregistered criteria:

- overall exact-recovery non-inferiority;
- high-noise `poly3` gain;
- high-noise `interaction` gain;
- `base` exact-recovery non-inferiority;
- conditional exception recovery;
- NMSE non-inferiority;
- runtime below 15x legacy.

The frozen decision is therefore **NO-GO**.

Primary aggregate results:

| Method | Exact recovery | Term precision | Term recall | Test NMSE |
|---|---:|---:|---:|---:|
| legacy-certificate | 0.7089 | 0.8779 | 0.8722 | 0.005224 |
| crossfit-v2-structural | 0.6622 | 0.9010 | 0.8476 | 0.019435 |
| role-v4-no-backward | 0.5867 | 0.9186 | 0.7850 | 0.050335 |
| **hr-v5-full** | **0.6200** | **0.9082** | **0.8302** | **0.031452** |
| centralized-forward | 0.9200 | 0.9770 | 0.9994 | 0.0000917 |
| score-only-federated | 0.1022 | 0.5831 | 0.9922 | 0.000311 |

The v5 communication median was 26.09x legacy and passed the frozen <30x gate. Its runtime median was 16.05x legacy and failed the frozen <15x gate.

## 2. The candidate-recall bottleneck is solved on this matrix

This is the strongest positive result from v5:

- mean candidate-bank target recall: **1.000**;
- complete-truth candidate-bank coverage: **1.000**;
- median bank size: **8** nonconstant terms;
- mean bank size: **7.38**;
- median nuisance count: **5**;
- mean nuisance count: **4.85**.

Thus every true structural term was present in the v5 bank for all 450 development conditions. The dominant failure is no longer candidate absence. The unresolved problem is **structural discrimination inside a high-recall, nuisance-rich bank**.

This sharply changes the research question. A successor should not spend its main innovation budget on enlarging candidate recall again. It should solve conditional discrimination among jointly plausible symbolic terms.

## 3. Exact-recovery matched comparisons

Paired condition-level exact-recovery comparisons for HR-VFS v5:

| Comparator | v5-only exact wins | Comparator-only exact wins | Ties | Exact McNemar/binomial p |
|---|---:|---:|---:|---:|
| legacy | 18 | 58 | 374 | 4.71e-6 |
| crossfit-v2-structural | 16 | 35 | 399 | 0.0110 |
| role-v4-no-backward | 15 | 0 | 435 | 6.10e-5 |
| stability-superset-v3 | 31 | 1 | 418 | 1.54e-8 |

Interpretation: v5 is a real improvement over v3/v4-no-backward, but it remains materially below legacy and v2. This is not a marginal gate miss that should be repaired by threshold tuning.

## 4. Benchmark localization

Exact recovery by benchmark:

| Benchmark | Legacy | v2 structural | v4 no-backward | v5 | Centralized |
|---|---:|---:|---:|---:|---:|
| base | 0.500 | 0.456 | 0.267 | 0.433 | 0.900 |
| interaction | 0.844 | 0.800 | 0.611 | 0.611 | 0.900 |
| nested_sine | 0.956 | 0.956 | 0.989 | **0.989** | 0.933 |
| poly3 | 0.244 | 0.100 | 0.067 | 0.067 | 0.933 |
| trig_product | 1.000 | 1.000 | 1.000 | **1.000** | 0.933 |

The dominant unresolved benchmark is `poly3`. v5 does not improve it over v4-no-backward despite perfect bank coverage. `interaction` also does not improve over v4-no-backward. The improvement over v4 is concentrated in `base`.

Noise localization against legacy:

| Noise ratio | Legacy exact | v5 exact |
|---|---:|---:|
| 0.03 | 0.933 | 0.700 |
| 0.10 | 0.680 | 0.593 |
| 0.20 | 0.513 | **0.567** |

The v5 mechanism is comparatively more useful in the highest-noise aggregate regime, but it loses too much low-noise structural exactness. This argues against simply weakening validation/probe thresholds.

## 5. Missing-truth event taxonomy

Across the 450 v5 conditions there are **251 missing-truth term events**. Because the bank contains all truth terms, every one of these losses occurs after bank construction.

Stage classification:

| Failure stage | Missing truth events |
|---|---:|
| independent probe rejected | **169** |
| selector rejected | **81** |
| final-size cap before test | 1 |
| **Total** | **251** |

Term-specific counts:

| Truth term | Missing total | Probe rejected | Selector rejected | Size cap |
|---|---:|---:|---:|---:|
| `x3^2` | 59 | 54 | 4 | 1 |
| `x1^2` | 59 | 52 | 7 | 0 |
| `x1^3` | 54 | 21 | 33 | 0 |
| `I(x3>1)*x3^2` | 34 | 9 | 25 | 0 |
| `x1` | 26 | 20 | 6 | 0 |
| `sin(x2)` | 18 | 12 | 6 | 0 |
| `sin(x1)` | 1 | 1 | 0 | 0 |

By benchmark:

| Benchmark | Probe-rejected truth events | Selector-rejected truth events | Size cap |
|---|---:|---:|---:|
| poly3 | **98** | **49** | 0 |
| base | 49 | 17 | 1 |
| interaction | 21 | 15 | 0 |
| nested_sine | 1 | 0 | 0 |
| trig_product | 0 | 0 | 0 |

This establishes the principal v5 failure mode: **conditional structural acceptance, especially probe discrimination, not candidate discovery**.

## 6. Probe failure anatomy

Among the 169 probe-rejected missing truth events:

- 91: correlated rival matched or beat the proposed improvement;
- 37: proposed term did not beat the rival on enough clients;
- 35: proposed term did not reduce aggregate probe SSE;
- 6: selector coefficient signs were unstable across clients.

The largest term-specific rival-confusion counts were:

- `x3^2`: 39 correlated-rival rejections;
- `x1^2`: 26 correlated-rival rejections;
- `x1`: 17 correlated-rival rejections;
- `sin(x2)`: 7 correlated-rival rejections.

The evidence therefore supports a **surrogate-equivalence / conditional-identifiability problem**. A true term can enter the bank but lose an isolated one-term comparison to a correlated finite-catalog surrogate.

## 7. Pair-rescue mechanism failed structurally

V5 attempted **1,344** correlation bundles and accepted **zero**.

Failure stages:

| Pair outcome | Count |
|---|---:|
| selector rejected | **1,194** |
| joint probe rejected | 88 |
| joint probe passed but necessity failed | 62 |
| accepted | **0** |

The most common selector failures were insufficient validation-MSE gain (901) and failure to improve the complexity-adjusted validation score (215).

More importantly, the discovery-only raw-correlation rule built the wrong kinds of bundles for the key polynomial failure. Across all `poly3` conditions the retained pair types included:

- `x1^2` with `cos(x1)`: 90;
- `x1` with `x1^3`: 71;
- `x1` with `sin(x1)`: 42;

but **`x1^2` with `x1^3` was never formed**. Thus the mechanism designed to rescue jointly necessary polynomial siblings did not actually expose the key sibling pair.

Raw column correlation is therefore not an adequate definition of a structural symbolic family.

## 8. A useful signal hidden inside failed pair tests

Among pair proposals that passed both selector and joint probe, the necessity patterns were:

- neither member necessary: 42;
- exactly one member necessary: 20;
- both members necessary: 0.

Of those 20 one-necessary cases, the uniquely necessary member was a **true term in 18 cases** and a nuisance in only 2. Example: `x3^2 + cos(x3)` can pass jointly, after which leave-one-member-out evidence identifies `x3^2` as necessary and `cos(x3)` as unnecessary.

V5 nevertheless rejects the entire pair because it requires **both** members to be necessary. A post-hoc non-confirmatory simulation that admits the uniquely necessary member would raise exact recovery only from 0.6200 to approximately 0.6289 (4 newly exact conditions, zero exact harms). Therefore selective member admission is promising but insufficient by itself.

The stronger successor mechanism must operate at **set/family level**, not only on retained raw-correlation pairs.

## 9. Single-term acceptance is safe in one sense but not sufficient

V5 made 2,552 single-term attempts and accepted 219.

- 177 accepted additions were true terms;
- 42 were nuisance/surrogate terms.

The frozen `single_exact_harms` endpoint is zero, meaning no accepted single addition turned an already exact structure into a non-exact structure. However, that endpoint does not mean all accepted singles were structurally correct: 42 nuisance additions occurred while the model was already non-exact.

Therefore a successor must improve recall **without simply relaxing single-term acceptance**, because weaker gates would plausibly increase surrogate contamination.

## 10. Ablation interpretation

- Removing bundle rescue changes exact recovery by **0/450 matched conditions**. Pair rescue is experimentally inert in v5.
- Full v5 versus no-score-proposer: 4 v5-only exact wins, 0 reverse wins. The score proposer materially solves bank recall, but most added candidates still fail downstream discrimination.
- Full v5 versus no-role-conditioning: 3 v5-only exact wins, 0 reverse wins. Role conditioning helps, especially for the exception task, but the remaining exception path still fails the gate.

The score channel and role conditioning should be retained as proposal mechanisms; raw-correlation atomic pair rescue should not.

## 11. Restricted-exception implementation audit

The frozen v5 protocol states that the restricted exception should retain the eligible-client selector/probe denominator and that structural acceptance should be evaluated on eligible gated selector/probe clients.

The implementation first calls the generic `_admissible_fallback` on **all selector partitions**, including `_validation_term_support`, and only after that gate passes does `_role_probe_profile` filter the structural probe to eligible gated clients. This matters because 25 of 34 missing exception events are selector failures, including 22 generic cross-client-support failures.

The earlier v4 clarification explicitly allowed outside-domain clients to remain relevant to selector non-degradation safeguards while excluding them from the structural-probe win/sign denominator. The v5 wording is stronger and therefore creates an ambiguity/mismatch that must be resolved **before any successor evidence run**.

Scientific consequence: the sealed v5 run remains a valid test of the exact committed implementation and remains NO-GO. However, it should not be described as definitive evidence that every intended role-conditioned selector interpretation fails. The exception-selector semantics must be made explicit in the next frozen protocol and invariant tests.

## 12. Successor mechanism hypothesis

The evidence supports replacing greedy single-term + atomic pair rescue with **Set-Conditional Structural Verification (SCSV)**:

1. retain the v5 high-recall bank, because it achieved complete truth coverage;
2. transmit one-shot aggregate sufficient statistics for the fixed bank on fit/selector/probe partitions;
3. compare admissible candidate **sets**, not isolated terms;
4. use selector data to rank a deterministic, complexity-bounded subset frontier;
5. use independent probe data for non-destructive leave-one-out and one-swap structural contrasts;
6. accept a candidate set only when every retained term is conditionally necessary and no tested lower-complexity/surrogate set explains the probe data equivalently;
7. do not sequentially delete terms after acceptance;
8. handle exception terms with explicitly frozen eligible-client support semantics;
9. keep final model size <= 6 and bank size <= 10.

This directly attacks the failure observed in v5: the true set exists in the bank but greedy one-term structural discrimination suppresses members that are only identifiable conditionally.

## 13. Why this is not merely best-subset tuning

The research hypothesis is not "enumerate subsets until one works." The proposed contribution is a federated falsification architecture that separates:

- high-recall proposal;
- aggregate sufficient-statistic set fitting;
- selector-based structural frontier construction;
- independent probe-based conditional necessity;
- role-aware exception verification;
- privacy/communication accounting.

Any novelty claim remains prohibited until a systematic prior-art review is completed. Structured/orthogonal matching-pursuit literature already documents failures of greedy residual selection under correlated predictors, so the contribution must be framed specifically around **federated symbolic structural falsification with disjoint proposal/selector/probe evidence**, not generic correlated-feature selection.

## 14. Next executable step

Do **not** spend fresh successor seeds yet.

Run an exploratory SCSV mechanism diagnostic using only already-spent development conditions and/or a dedicated engineering seed. The diagnostic must answer:

- Does set-level selection materially improve `poly3` and `interaction` exact recovery over v5?
- Does it preserve `nested_sine` and `trig_product`?
- Can it resolve `x3^2` versus `cos(x3)` and polynomial sibling families without accepting nuisance terms?
- Does one-shot sufficient-statistic messaging reduce communication below v5?
- Can restricted-exception selector semantics be made unambiguous and testable?

Only after this diagnostic shows a mechanism-level signal should a v6 protocol, fresh seeds, and GO/NO-GO gate be frozen.