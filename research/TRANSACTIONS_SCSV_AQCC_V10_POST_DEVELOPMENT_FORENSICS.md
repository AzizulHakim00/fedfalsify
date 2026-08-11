# SCSV-AQCC v10 post-development forensic report

Status: **SPENT-DATA / NON-CONFIRMATORY**

This report is a read-only forensic decomposition of the sealed v10 fresh-development evidence. It does not alter the v10 scientific verdict, does not authorize retuning, and must not be presented as independent validation or confirmation.

## Frozen scientific boundary

The v10 sharded study was executed from run commit `da9010592538693fb8deba13353f62e8e62ca6ad`, with the scientific implementation pinned to `06697f65a3f234bd93fe72cf882ecdfaa1040304`.

The sealed evidence commit is `0b3cecb0369a2da5e9265b3f1de534970b43ed20`.

Fresh seeds `28101, 28102, 28103, 28104, 28105` are permanently spent.

Historical labels remain unchanged:

- v6 independent validation: `INDEPENDENT-NO-GO`;
- v7 development: `DEVELOPMENT-NO-GO`;
- v8 development: `DEVELOPMENT-NO-GO`;
- v9 sharded recovery: `DEVELOPMENT-NO-GO`;
- v10 development: `DEVELOPMENT-NO-GO`.

## Evidence integrity

All five v10 shard jobs completed successfully. Each shard contained 120 unique conditions and 720 method rows. Aggregation completed successfully with exactly 600 unique conditions, exactly six methods per condition, and exactly 3,600 rows.

Seeds in the sealed matrix are exactly `28101--28105`; engineering seed `28001` is absent.

The sealed artifact digest is:

`sha256:0002841c3f95bf64f5c6898717ac496068183856233470109e99102c759db577`

The repository seal contains `rows.csv`, `summary.json`, `decision.json`, `manifest.json`, `SHA256SUMS`, and `COMPLETE`.

Verified output hashes:

- `rows.csv`: `9ec5f8469035169a39a0e62a3c5a0c5258bfb5e8944e2313609dfa58fba2052b`;
- `summary.json`: `9df58fed65bfa148bb915df9ca6114d4dd4149830dceab81850e67d720a9748e`;
- `decision.json`: `766393fc8ebcfd746c8673a679fd07f8664f76ea9541e5454f3d12ea904f2921`;
- `manifest.json`: `287fa05973d6308f9d25758f9ca9fada73c8b84f6ef479ec5ae7dd3b80ee55fc`.

## Frozen A--Y decision

V10 passed 15 of 25 gates and failed 10. Therefore the only valid scientific verdict is:

**DEVELOPMENT-NO-GO**

Failed gates were:

- E: zero exact harms;
- F: overall exact gain >= 0.02;
- G: deviation-subset exact gain >= 0.04;
- I: deviation recall >= 0.95;
- J: every main family recovery >= 0.92;
- L: four-client recovery >= 0.90;
- N: sixteen-client recovery >= 0.95;
- O: high-noise recovery >= 0.90;
- Q: dual-both recovery >= 0.90 with no spurious deviations;
- S: client-consensus mechanism superiority.

The successful gates are still scientifically informative: deviation precision was `1.000`, null spurious-deviation acceptance was `0.000`, weak-source recovery was `1.000`, and all role/source/pair/client-consensus integrity violation counts were zero.

## Primary numerical findings

V10 full exact recovery was `0.8400`; matched v9-style exact recovery was `0.8367`. The absolute improvement was only `+0.0033`, far below the preregistered `+0.0200` requirement.

On deviation-bearing conditions, v10 exact recovery was `0.8271` versus `0.8229` for v9-style, an absolute gain of only `+0.0042`, far below the required `+0.0400`.

Pooled deviation recall was `0.9250`, below the required `0.9500`.

Main-family recovery was:

- interaction: `0.990`;
- linear: `0.970`;
- quadratic: `0.860`;
- trigonometric: `0.860`.

Client-count recovery was:

- 4 clients: `0.8750`;
- 8 clients: `0.93125`;
- 16 clients: `0.93125`.

High-noise main-family recovery was `0.8500`.

Dual-both recovery was `0.8250`.

Balanced and imbalanced recovery were both `0.920`, so imbalance was not the dominant failure axis.

## True-deviation failure taxonomy

Across the sealed v10 full rows there were 520 true deviation instances. V10 recovered 481 and missed 39.

The 39 misses decompose exactly as:

- `34` pooled-evidence failures;
- `5` source-qualification failures;
- `0` true-deviation occupancy-role failures;
- `0` true-deviation pair-invariant failures;
- `0` true-deviation outside-role invariant failures;
- `0` true-deviation client-median failures.

By family, the 34 pooled-evidence misses were:

- quadratic: 13;
- trigonometric: 12;
- dual: 5;
- linear: 3;
- interaction: 1.

The five source-qualification misses were:

- dual: 2;
- trigonometric: 2;
- quadratic: 1.

All five source-qualification misses occurred at noise ratio `0.30`.

All but three pooled-evidence misses occurred at noise ratio `0.30`: pooled-evidence misses were 3 at noise `0.10` and 31 at noise `0.30`.

This is the dominant v10 sensitivity diagnosis: **held-out pooled evidence becomes too weak under high noise for quadratic/trigonometric and dual deviations, with a smaller secondary failure from global source qualification.**

## High-noise localization

True-deviation recovery by family and noise was:

- quadratic: `1.00` at noise `0.10`, `0.72` at `0.30`;
- trigonometric: `0.96` at `0.10`, `0.76` at `0.30`;
- dual-both: `0.95` at `0.10`, `0.70` at `0.30`;
- linear: `1.00` at `0.10`, `0.94` at `0.30`;
- interaction: `1.00` at `0.10`, `0.98` at `0.30`;
- weak-source: `1.00` at both noise levels.

For the four main families, recovery by client count at noise `0.30` was:

- 4 clients: `0.7500`;
- 8 clients: `0.8625`;
- 16 clients: `0.8875`.

Single-role conditions were harder than quarter-role conditions at noise `0.30` (`0.8167` versus `0.9000`).

Therefore the remaining sensitivity problem is concentrated in sparse-role, high-noise evidence rather than general imbalance.

## Client-consensus mechanism contribution

Compared with the frozen split-veto ablation, v10 full improved exact recovery in exactly four conditions and harmed none. All four improvements were at noise ratio `0.30`.

However, the preregistered superiority gate still failed because the high-noise true-deviation exact recovery was only `0.6750` for v10 full versus `0.6583` for split-veto, an absolute improvement of `+0.0167`, below the required `+0.0200`.

Thus client-level selector/probe combination is directionally useful, but its effect is too small to resolve the dominant high-noise failure.

## Quarantine mechanism forensic result

The rotated v10 matrix produced zero spurious deviation acceptance for both v10 full and the no-quarantine ablation on the anchor-contamination panel.

More importantly, all 410 quarantined anchor exceptions in the sealed matrix were true deviations; there were **zero false anchor exceptions available for quarantine to remove**. Of those 410 true quarantined exceptions, 409 were re-certified and one was removed.

Consequently, the v10 contamination panel did not reproduce the upstream false-anchor mechanism that motivated quarantine. Gate R passed because both full and no-quarantine already had zero spurious deviation acceptance. This is a non-informative success for the quarantine mechanism, not evidence that quarantine solved the v9 inherited-false-positive mechanism.

The single rejected true quarantined anchor exception occurred in `dual_role_v10`, noise `0.10`, 8 clients, imbalanced, seed `28104`. Its pooled delta was `+0.04235` despite a positive client median gain. Removing it created one of the exact harms.

## Exact harms

There were exactly two conditions that were exact under matched v9-style but inexact under v10 full. Both were dual-role, 8-client, imbalanced conditions:

1. noise `0.10`, seed `28104`: the true linear gated deviation was an anchor exception, quarantined, and removed because pooled evidence was not negative;
2. noise `0.30`, seed `28105`: the true linear gated deviation was not accepted because pooled evidence remained positive (`+0.02775`) despite positive client median gain.

These harms reinforce that the current bottleneck is the pooled evidence criterion, not false-positive control.

## Shared/core structure remains a major ceiling

V10 exact recovery failed in 96 of 600 conditions. Only 39 of those failures involved a missed true deviation; 57 failures occurred even though all true deviations were recovered.

A direct structural decomposition shows the shared/core part of the final v10 equation was exact in only about `84.5%` of conditions, almost identical to the v6 anchor shared/core exact rate of about `84.33%`.

Frequent shared/core errors included missing `sin(x1)`, `cos(x2)`, or `x3^2`, and selecting distractors such as `x2`, `x3`, or `cos(x3)`.

Therefore v10's exception-layer improvements cannot by themselves drive total exact recovery substantially higher while ordinary anchor terms remain immutable. **Shared-anchor structural error is now a second major ceiling, independent of deviation certification.**

## Correction to the successor rationale

Any successor must preserve the following forensic fact:

> In the sealed v10 rows, none of the 39 missed true deviations failed because the occupancy-based role rule could not identify a role. The misses were 34 pooled-evidence failures and 5 source-qualification failures.

Therefore a successor justified primarily as fixing `ROLE-NOT-IDENTIFIED` for true v10 deviations is not directly supported by this spent-data decomposition. Response-effect localization may still be a scientifically interesting new hypothesis, but it must be treated as a new mechanism hypothesis rather than as the demonstrated dominant v10 failure mechanism.

Likewise, weak source heredity directly addresses the five source-qualification misses, but it does not address the 34 pooled-evidence misses or the approximately 15.5% shared/core structural-error rate.

## Successor design requirements

A scientifically aligned successor should be paper-first and should target three separable mechanisms:

1. **high-noise evidence power without precision loss**: replace or augment the single pooled complexity-penalized decision with a preregistered evidence model that can accumulate repeated client-level effect evidence while preserving the observed 1.00 deviation precision;
2. **provenance-only parent support**: allow a banked source to justify a local gated child without requiring that source to become a globally operational term, directly targeting the five source-qualification misses;
3. **shared-anchor re-certification/repair**: introduce a separately governed mechanism for ordinary shared terms rather than treating the v6 ordinary anchor as permanently immutable, because shared/core error explains 57 exact failures even when deviation recovery is complete.

These mechanisms must be separated by ablation. No threshold may be selected from `28101--28105`.

## Relationship to the existing v11 draft

The repository currently contains a separately versioned draft successor, **SCSV-ELRC v11**, with fresh engineering seed `29001` and reserved development seeds `29101--29105`. Its effect-localized role certification and provenance-only weak heredity are legitimate new hypotheses, but the first mechanism should not be described as the measured dominant v10 failure because the sealed v10 true-deviation taxonomy contains zero occupancy-role misses.

Before any `291xx` fresh-development run is authorized, the v11 rationale and gate design should be reconciled with this forensic result, and the shared/core anchor ceiling should be explicitly acknowledged. V10 seeds must never be reused to tune that reconciliation.

## Final forensic verdict

V10 achieved a strong precision correction but not a sufficient recovery improvement.

The most defensible interpretation is:

- **precision problem: solved on the v10 matrix** (`1.00` pooled deviation precision, `0.00` null spurious acceptance);
- **sensitivity problem: unresolved**, concentrated in high-noise pooled evidence and a small number of source-qualification failures;
- **total exact-recovery ceiling: also constrained by shared/core anchor errors**;
- **quarantine benefit: not demonstrated by the rotated v10 matrix**, because no false anchor exception was selected;
- **v10 verdict remains permanently `DEVELOPMENT-NO-GO`**.

This report is descriptive only. It does not authorize v10 retuning, independent-validation claims, or reuse of `28101--28105`.
