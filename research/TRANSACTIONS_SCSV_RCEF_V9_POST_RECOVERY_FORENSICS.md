# FedFalsify v9 post-recovery forensics

Status: **SPENT-DATA / NON-CONFIRMATORY FORENSIC REPORT**

This report analyzes only the sealed SCSV-RCEF v9 sharded infrastructure-recovery evidence from GitHub Actions run `31465220024`. It does not retune v9, does not alter any A--W gate, and does not convert the frozen `DEVELOPMENT-NO-GO` result into a GO.

## Evidence identity

- authorization/source commit: `a39c5a11ae8d40855a917d62b910f986612ed191`
- workflow run: `31465220024`
- fresh recovery seeds: `27101--27105` (permanently spent)
- conditions: 600
- methods: 6
- rows: 3,600
- combined sealed artifact: `scsv-rcef-v9-sharded-recovery-evidence`
- artifact ID: `9092985067`
- artifact ZIP SHA256: `117f545834b45902860d4fdc9a270e7d68661e66cf93ae149b6136187077abd1`
- scientific verdict: `DEVELOPMENT-NO-GO`

All five 120-condition shards completed successfully. The aggregate job verified exactly 600 unique matched conditions, 3,600 unique method rows, seeds exactly `27101--27105`, six frozen methods per condition, and finite required numeric fields. Combination, A--W evaluation, evidence audit, sealing, and artifact upload all passed. The final repository-commit step failed only because `results/scsv_v9_recovery` is ignored by `.gitignore`; this does not change the sealed scientific verdict because the combined artifact had already been finalized and uploaded.

## Frozen A--W outcome

Sixteen of 23 gates passed and seven failed.

Failed gates:

- C null/diffuse-null spurious deviation acceptance <= 0.02: **FAIL**, observed `0.3666666667`.
- D zero exact harms: **FAIL**, observed `1` exact harm relative to matched v8-style.
- F deviation-bearing exact gain >= +0.04 over v8-style: **FAIL**; v9 `0.8604166667`, v8-style `0.8479166667`, gain only `+0.0125`.
- G pooled deviation precision >= 0.99: **FAIL**, observed `0.9166666667`.
- K 4-client main-family recovery >= 0.88: **FAIL**, observed `0.85`.
- N high-noise main-family recovery >= 0.88: **FAIL**, observed `0.875`.
- P dual both-recovered >= 0.90 with no spurious deviations: **FAIL**, observed both-recovered `0.75`; the no-spurious part itself passed (`0` spurious among exact-both dual rows).

Important passed values include deviation recall `0.9307692308`, family recovery quadratic `0.90`, linear `0.95`, trig `0.90`, interaction `1.00`, weak-source recovery `1.00`, 8-client recovery `0.9375`, 16-client recovery `0.98125`, and zero role/source/pair/evidence-fusion integrity violations.

Overall exact recovery was `0.7883333333` for v9 full versus `0.7783333333` for matched v8-style and `0.705` for the frozen v6 anchor.

## Forensic decomposition of the precision failure

The pooled v9 full deviation counts were:

- true positives: 484
- false positives: 44
- false negatives: 36

All **44 false-positive deviations** occurred in `null_role_v9` or `diffuse_null_v9`. There were 22 in each family. Every one occurred at noise ratio `0.30`; there were zero such false positives at noise `0.10`.

The false-positive term was the same in all 44 cases:

`I(x4>0.85)*x4^2`

Crucially, this term was already present in the frozen **v6 anchor structure** in those rows. The v6 anchor, v8-style, and v9 full have exactly the same null/diffuse-null spurious-deviation flag on all 120 null-panel conditions, and exactly the same final discovered terms in those rows. Therefore these 44 false positives were **not introduced by the v9 role proposer or by evidence fusion**.

This exposes a structural protocol conflict in this fresh matrix: gate B requires anchor monotonicity (v9 may not delete an anchor term), while gate C requires absolute null spurious acceptance <= 0.02. On these data the frozen anchor itself has null/diffuse-null spurious acceptance `44/120 = 0.3666666667`. Hence a monotone successor that cannot audit/remove an already-selected exception term cannot satisfy gate C on these rows. This observation does not invalidate the frozen gate; it explains why v9 cannot pass it and why v9 remains `DEVELOPMENT-NO-GO`.

The same inherited 44 anchor false positives account for the pooled precision failure: v9 had 484 TP, 44 FP, and 36 FN, giving precision `484/(484+44) = 0.9166666667`. No deviation-bearing family produced a false-positive deviation under v9 full.

## Forensic decomposition of the sensitivity failure

All 36 missed true deviations occurred at noise ratio `0.30`. There were **zero true-deviation misses at noise `0.10`**.

Failure mechanisms among the 36 misses:

- `HELDOUT-CONTRADICTION`: 27
- `POOLED-NOT-SUPPORTED`: 8
- `SOURCE-NOT-QUALIFIED`: 1

The 27 contradiction misses break down as:

- selector `INCONCLUSIVE-DIRECTIONAL`, probe `CONTRADICTED`: 9
- selector `SUPPORTED`, probe `CONTRADICTED`: 9
- selector `CONTRADICTED`, probe `INCONCLUSIVE-DIRECTIONAL`: 6
- selector `CONTRADICTED`, probe `CONTRADICTED`: 2
- selector `CONTRADICTED`, probe `SUPPORTED`: 1

Thus the contradiction veto is the dominant residual v9 false-negative pathway under high noise. It is not a role-identification, pair-isolation, outside-role, or certificate-integrity problem: the frozen Q--T integrity gates all passed with zero violations.

Miss counts by family were:

- quadratic: 10 (8 contradiction, 2 pooled-not-supported)
- linear: 5 (3 contradiction, 2 pooled-not-supported)
- trig: 10 (8 contradiction, 1 pooled-not-supported, 1 source-not-qualified)
- dual: 11 (8 contradiction, 3 pooled-not-supported)
- interaction: 0
- weak-source: 0

The single source-qualification miss occurred in a 4-client, balanced, noise-0.30 trig condition (seed `27103`): the source `sin(x3)` was banked but absent from the anchor, and the outside-role source certificate was not supported because selector evidence contradicted the source while probe evidence was only directional.

## Four-client and high-noise concentration

Main-family recovery by client count was:

- 4 clients: `0.85`
- 8 clients: `0.9375`
- 16 clients: `0.98125`

All misses were at noise `0.30`; main-family high-noise recovery was `0.875`, missing gate N by 0.005. Twelve of the 36 total missed true deviations occurred in 4-client conditions, where held-out role support is smallest and the contradiction/source-certification decisions are least statistically stable.

## Dual-role failure

Dual-role both-recovered performance was `0.75` (30/40 conditions). Low-noise dual recovery was perfect: 20/20 at noise `0.10`. At noise `0.30`, both-recovered fell to 10/20.

The high-noise dual breakdown was especially poor for 8 clients: balanced `1/5`, imbalanced `1/5`; 16-client balanced was `3/5`, while 16-client imbalanced was `5/5`. Across dual rows, 11 true deviations were missed, with 8 contradiction failures and 3 pooled-not-supported failures.

There was one exact harm versus matched v8-style: dual-role, noise `0.30`, 16 clients, balanced, seed `27102`. V8-style recovered both deviations. V9 retained the quadratic deviation but rejected `I(x4<-0.85)*x4` because selector was `SUPPORTED`, probe was `INCONCLUSIVE-DIRECTIONAL`, but pooled delta was slightly positive (`0.0029070375`), so the frozen pooled certificate rejected it.

## Evidence-fusion contribution

Relative to the selector-only v9 ablation, full evidence fusion produced seven exact-recovery gains and one exact-recovery loss. The seven gains occurred only at noise `0.30` (five trig, one linear, one dual). The one loss was the dual seed `27102` case described above.

This is why gate U (mechanism superiority) passed even though gate F did not: evidence fusion has a real positive mechanism signal, but its net exact-recovery gain over v8-style was only `+0.0125`, below the preregistered `+0.04` requirement.

## Scientific interpretation

The v9 experiment supports three narrow mechanism conclusions only:

1. The v9 role/source/pair isolation machinery is technically sound on the fresh matrix: Q--T all passed with zero integrity violations.
2. Cross-view evidence fusion improves high-noise recall relative to selector-only in several cases, but the gain is not large enough for the frozen development claim and it causes one exact harm.
3. The dominant precision failure is upstream anchor contamination by a role-exception term, not v9 augmentation. Because v9 freezes every anchor term as mandatory, v9 has no legal mechanism to repair that contamination.

These are spent-data diagnostic findings. They do not authorize retuning v9, reusing `27101--27105`, independent validation, or external confirmation.

## Successor hypothesis (paper-first only)

Any successor should address **two distinct mechanisms** rather than tuning v9 thresholds:

1. **Anchor exception quarantine / re-certification:** preserve monotonicity for ordinary shared/core anchor terms, but do not automatically treat anchor-selected role/exception terms as irrevocable. Exception terms inherited from the anchor should pass an independent role-aware certificate before becoming mandatory in the operational final structure. This directly targets the 44 inherited null false positives without changing ordinary shared-anchor terms.
2. **High-noise contradiction handling:** retain fixed-pair/source isolation, but replace the current single selector/probe contradiction logic with a separately preregistered high-noise evidence design that can distinguish sampling-direction instability from genuine contradiction without using spent v9 outcomes to tune a threshold. Any such design needs a fresh prior-art audit and a completely new seed namespace before implementation.

No successor fresh evidence is authorized by this forensic report alone.