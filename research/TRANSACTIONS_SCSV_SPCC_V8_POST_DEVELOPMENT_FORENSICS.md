# SCSV-SPCC v8 post-development forensics

## Scientific boundary

This document is a read-only forensic analysis of the sealed fresh-development evidence for FedFalsify v8 / SCSV-SPCC. It does **not** alter the v8 algorithm, benchmark grammar, A--T gates, thresholds, or the sealed `DEVELOPMENT-NO-GO` decision.

Fresh development seeds `25101--25105` are permanently spent. No analysis below authorizes retuning v8 on those seeds, independent validation, or external SRSD confirmation. Any successor must be separately versioned, preregistered, and use a new untouched seed namespace.

## Provenance

- Frozen development authorization: `98be110c35c9d8d3770aca53b6d9cb40161da360`
- Workflow run: `31419411157`
- Sealed evidence commit: `a80477308f84c93e02108ff0e9528613f9561f90`
- Artifact: `scsv-spcc-v8-development-evidence`
- Artifact ID: `9079758497`
- Artifact digest: `sha256:87a6efdf33b97dbad56023a5e406964afb227ac8f1e947256ea571ac0c708266`
- Conditions: `540`
- Rows: `2700`
- Sealed status: `DEVELOPMENT-NO-GO`

The sealed output hashes are:

- `rows.csv`: `a28b2a82c14a94550e1a601d26192e15c6558d20f8a367f047ac2892f5a3a35c`
- `summary.json`: `e773f62f4d77cd46a106b69993ecc03eaa9b1cee84b28a188b1fb7b06db0ebb2`
- `decision.json`: `d029e10b0b32f2ffb95a5312feee61d7e64b5c4c7d18b4d88f0e5c54373ac6d5`
- `manifest.json`: `5ac9d74be1afed691410b2f06cda107c9f9392e4d8e9ed0bb6e8dcf25d4f6505`

## Frozen development outcome

SCSV-SPCC v8 improved exact recovery over both the frozen v6 anchor and the v7-style comparator:

- v6 exact: `0.6388888889`
- v7-style exact: `0.6722222222`
- v8 exact: `0.7037037037`
- v8 deviation-bearing exact: `0.8022727273`
- v6 deviation-bearing exact: `0.7227272727`
- v7-style deviation-bearing exact: `0.7636363636`
- v8 deviation precision: `1.0000`
- v8 deviation recall: `0.8916666667`
- exact harms: `0`
- null false-role hypothesis rate: `0`
- null spurious deviation acceptance: `0`
- certificate violations: `0`

The all-or-nothing decision remained NO-GO because H, I, J, K, M, and O failed. The safety and mechanism gates B, C, D, P, Q, and R all passed.

## Term-level transition from v6 to v8

Across the fresh matrix there are `480` true role-deviation instances.

The frozen v6 anchor recovered `379/480`. SCSV-SPCC v8 recovered `428/480`.

Relative to v6, v8:

- preserved all `379/379` true deviations already recovered by v6;
- rescued `49/101` deviations missed by v6;
- left `52/101` v6 misses unresolved;
- lost `0` previously recovered true deviations.

This is a strong monotonicity result: the v8 augmentation layer improved recall without deleting a true deviation already present in the frozen anchor.

Relative to the v7-style comparator, both methods recovered `428/480` true deviations in aggregate, but the identities differ: v8 rescued `22` deviations missed by v7-style and missed `22` deviations recovered by v7-style. Despite equal aggregate deviation recall, v8 produced higher exact recovery (`0.7037` vs `0.6722`) and lower test NMSE (`0.002586` vs `0.003106`). Therefore the v8 mechanism changed *which* conditions were recovered and improved structural alignment, not merely the pooled recall count.

## Exact decomposition of the 52 unresolved true deviations

The `52` unresolved true-deviation events decompose exactly as follows:

| Failure stage | Count | Share |
|---|---:|---:|
| selector not supported | 36 | 69.23% |
| deviation absent from high-recall bank | 12 | 23.08% |
| source term absent from frozen anchor | 3 | 5.77% |
| probe contradicted | 1 | 1.92% |

There are **zero** unresolved true deviations caused by:

- role-not-admissible failure after the true deviation reached the v8 diagnostic path;
- pair-invariant failure;
- selector outside-role safety failure;
- probe outside-role safety failure;
- source ambiguity;
- global ambiguity.

This is the central forensic result. The v7 dominant failure mode -- outside-role rejection caused by shared-coefficient drift -- is no longer present among unresolved true deviations.

## The v8 role-contrast fix worked

For every unresolved true deviation that reached the SPCC diagnostic stage:

- the response-free role hypothesis was admissible;
- a non-empty outside-role client set existed;
- the fixed source/deviation pair invariant held;
- selector outside-role safety held;
- probe outside-role safety held.

The null families also had:

- false-role hypothesis rate `0`;
- spurious deviation acceptance `0`.

Therefore the v8 cross-client occupancy rule solved the specific null-role failure seen in v7, where ordinary within-client gate support could be mistaken for a true client-level role.

## The pair-isolation fix also worked

The v7 post-development forensics showed that jointly refitting the whole shared anchor caused `45/62` residual misses through outside-role safety rejection. In v8, the source-pair construction freezes unrelated shared coefficients and changes only the source/deviation pair.

Among the `52` unresolved v8 true deviations, outside-role safety contributes `0` misses. This is direct evidence that constrained pair isolation removed the previous shared-coefficient-drift bottleneck on this development matrix.

## New dominant bottleneck: selector sensitivity

The dominant remaining failure is now the selector itself: `36/52 = 69.23%` of all unresolved true deviations.

All `36` selector failures occur at noise ratio `0.30`.

More importantly, the selector failures split into two qualitatively different groups:

- `26/36 = 72.22%` have **lower held-out selector SSE under the full source-pair model than under the reduced model**, but the frozen complexity-penalized selector score remains non-negative;
- `10/36 = 27.78%` have actual selector worsening (`SSE_full >= SSE_reduced`).

For the 26 directional-but-rejected cases, selector delta ranges above zero even though the held-out loss direction favors the true deviation. Thus the principal v8 sensitivity problem is not false role identification or outside-role damage; it is that a small noisy role subset must independently overcome a full information-criterion penalty on the selector split.

The 36 selector misses by family are:

| Family | Selector misses |
|---|---:|
| quadratic | 18 |
| trig | 9 |
| linear | 4 |
| dual | 4 |
| interaction | 1 |

Within the 18 quadratic selector misses, `17` are directional held-out improvements rejected by the penalty. This is especially strong evidence that the current binary selector criterion is conservative in high-noise source-linked settings.

## Probe is no longer the main sensitivity problem

Only `1/52` unresolved true deviations is rejected because the v8 probe actively contradicts the candidate.

The strict-probe ablation recovered `421/480` deviations, while full v8 recovered `428/480`. Therefore the three-state probe (`SUPPORTED`, `INCONCLUSIVE-DIRECTIONAL`, `CONTRADICTED`) recovers seven additional true deviations relative to the strict probe while preserving pooled deviation precision `1.0`.

This means the v8 probe redesign had the intended effect. Removing the probe is not justified by these data; the remaining sensitivity problem lies primarily upstream at selector support and candidate availability.

## Upstream candidate/source incompleteness is now the second bottleneck

`15/52 = 28.85%` unresolved true deviations never receive a complete SPCC test because:

- `12` true gated deviations are absent from the high-recall bank;
- `3` have their source term absent from the frozen anchor.

These failures cannot be repaired by changing selector/probe evidence alone.

A successor therefore needs a separately justified high-recall role-contrast proposal mechanism, rather than only a more sensitive certificate. The proposal must remain truth-independent and should not use development labels or target identities.

## Family anatomy

True-deviation recovery by family is:

| Family | True deviation instances | Misses | Recovery |
|---|---:|---:|---:|
| interaction | 100 | 1 | 0.99 |
| linear | 100 | 9 | 0.91 |
| quadratic | 100 | 18 | 0.82 |
| trig | 100 | 15 | 0.85 |
| dual term-level | 80 | 9 | 0.8875 |

The official dual *both-deviations* condition-level recovery is `0.825`, which failed the frozen `0.90` gate.

The dual misses are not caused by ambiguity guards. Across the entire v8 fresh matrix, no source-ambiguity or global-ambiguity guard fired. The dual failures are instead composed of selector misses, bank misses, and one source-anchor miss.

## Noise anatomy

The concentration at high noise is extreme:

- noise `0.10`: `2/52` unresolved true-deviation events;
- noise `0.30`: `50/52` unresolved events.

Thus `96.15%` of remaining misses occur at high noise.

The two low-noise misses are both trig-family bank-absence events. Every selector failure occurs at high noise.

This shows that v8's safety mechanism generalizes much better than its evidence power: precision remains perfect, but role-local evidence becomes underpowered as noise rises.

## Client-count anatomy

The official frozen recovery gates report:

- 4 clients: `0.825`
- 8 clients: `0.8625`
- 16 clients: `0.95625`

The 16-client regime passes comfortably, while 4- and 8-client regimes fail their preregistered floors. This supports the interpretation that v8's remaining problem is evidence power under limited federated support rather than systematic false positives.

## Descriptive two-view aggregation check -- spent data only

A purely descriptive diagnostic was computed on the `36` selector-failure events using the already spent development evidence. It is **not** a v9 rule and cannot be used as fresh confirmation.

If selector and probe held-out SSEs are pooled after the discovery-fitted pair is frozen, while retaining the same information-criterion form on the combined held-out support, `10/36` selector misses would become negative under the combined score. If one additionally requires both held-out views to individually improve in direction, `6/36` would satisfy both-directional evidence plus the combined negative score.

This diagnostic is insufficient by itself to solve v8 and is not a license to adopt those numbers. It does, however, support a principled successor hypothesis: independent held-out views may be better used as a predeclared evidence aggregation/falsification system rather than requiring the small selector split alone to clear the complete complexity penalty.

## Dominant mechanism conclusion

The v8 NO-GO is scientifically different from the v7 NO-GO.

1. **Solved from v7:** null-role false eligibility. V8 has zero null false-role hypotheses and zero spurious deviation acceptance.
2. **Solved from v7:** shared/core coefficient drift during outside-role safety. V8 has zero true misses caused by outside-role safety.
3. **Solved substantially:** probe over-conservatism. Only one unresolved true deviation is actively probe-contradicted; the three-state probe improves recall over strict-probe without losing precision.
4. **New primary bottleneck:** high-noise selector sensitivity. `36/52` misses occur at selector support, and `26/36` still improve held-out SSE directionally.
5. **Secondary bottleneck:** candidate/source availability. `15/52` misses never receive a complete SPCC test.
6. **Stress concentration:** `50/52` misses occur at 30% noise; quadratic and trig families account for `33/52` misses.
7. **Dual failure is not ambiguity-driven:** ambiguity guards did not fire; dual misses arise from selector and upstream candidate/source incompleteness.

## Successor hypothesis permitted by the forensics

The evidence supports a two-part successor hypothesis. It does **not** authorize implementation or fresh evidence until a separate protocol is frozen.

### 1. Cross-fit evidence aggregation instead of a selector-only hard information-criterion gate

Keep discovery, role identification, source-pair isolation, and outside-role invariants frozen in spirit. Estimate the source/deviation pair only on discovery data, then treat selector and probe as two independent held-out evidence views. A successor should aggregate predeclared directional evidence across those views without refitting the pair and without allowing a weak view to erase an actual contradiction.

The key scientific distinction should be:

- directional but individually underpowered evidence;
- genuine held-out contradiction.

This addresses the `26` directional selector failures without simply loosening the frozen v8 threshold.

### 2. Response-free role-contrast proposal channel

A successor should reduce dependence on the response-driven high-recall bank for gated deviations. A candidate exception from the finite grammar may be proposed when its client-level gate occupancy exhibits a preregistered non-vacuous contrast, using only `X`/support information.

If the source term is absent from the frozen anchor, the successor must not silently insert it. Instead, it should require a separate outside-role source-necessity certificate before allowing a source/deviation pair to become operational.

This directly targets the `12` bank-absence and `3` source-anchor misses while preserving the v8 safety philosophy.

## Non-negotiable invariants for any v9

Any successor should retain at minimum:

- frozen v6/v8 historical evidence boundaries;
- no deletion of anchor terms by the augmentation layer;
- unrelated shared coefficients fixed during deviation certification;
- response-free role identification with non-empty role and outside-role client sets;
- fixed full/reduced pair differing only in the tested deviation coefficient;
- explicit rejection of genuinely contradictory held-out evidence;
- null-role and diffuse-null stress panels;
- dual-deviation panels;
- zero exact-harm target;
- at least `0.99` deviation precision target;
- new untouched engineering and fresh-development seed namespaces;
- no external SRSD confirmation until a successor passes a separately frozen development and independent-validation sequence.

## Required next step

The scientifically correct next step is **v9 design on paper only**. The design should formalize a cross-fit evidence-aggregation certificate and a response-free role-contrast proposal channel, prove the coefficient and non-vacuous-role invariants, define a new nonredundant benchmark matrix, freeze all gates, audit a new seed namespace for collisions, and only then implement engineering smoke.

No v9 fresh-development seed should be exposed before that complete pre-evidence firewall passes.