# RC-DES v4 Post-hoc Failure Forensics

> Status: **diagnostic only**. This report reuses the sealed v4 development matrix. It creates no new evidence, changes no v4 threshold, and does not reopen the v4 NO-GO decision.

## Evidence integrity

- Rows: **4500**.
- Seeds: `16101, 16102, 16103, 16104, 16105`.
- Ten preregistered methods, 450 matched conditions per method.

## Method snapshot

| Method | Exact | Recall | Precision | NMSE | Exception | Spurious |
|---|---:|---:|---:|---:|---:|---:|
| centralized-forward | 0.9844 | 1.0000 | 0.9963 | 7.4387e-05 | 1.0000 | 0.0000 |
| legacy-certificate | 0.7156 | 0.8759 | 0.8861 | 0.00539807 | 1.0000 | 0.0000 |
| crossfit-v2-structural | 0.6600 | 0.8576 | 0.9077 | 0.0149054 | 0.9444 | 0.0000 |
| stability-superset-v3 | 0.5644 | 0.7770 | 0.9117 | 0.0488263 | 0.8444 | 0.0000 |
| role-v4-no-backward | 0.6111 | 0.8017 | 0.9263 | 0.0423481 | 0.8667 | 0.0000 |
| role-v4-full | 0.5022 | 0.6839 | 0.8778 | 0.19416 | 0.8044 | 0.0000 |
| role-v4-no-path-persistence | 0.4911 | 0.6461 | 0.8570 | 0.207554 | 0.7889 | 0.0000 |
| role-v4-no-role-conditioning | 0.4022 | 0.6246 | 0.8678 | 0.266032 | 0.6667 | 0.0000 |
| role-v4-anchor | 0.5200 | 0.7217 | 0.9070 | 0.088716 | 0.8444 | 0.0000 |
| score-only-federated | 0.1244 | 0.9887 | 0.5954 | 0.000257811 | 1.0000 | 0.3844 |

## Where true terms were lost

Across 1140 truth-term opportunities, 457 were absent from the final thresholded support.

| Failure stage | Missing truth terms |
|---|---:|
| backward_removed_anchor_truth | 156 |
| candidate_bank_miss | 137 |
| structural_probe_rejected_truth | 114 |
| selector_rejected_truth | 46 |
| backward_removed_forward_truth | 4 |

## Term-specific failure map

| Truth term | Stage counts |
|---|---|
| `I(x3>1)*x3^2` | backward_removed_anchor_truth=27, backward_removed_forward_truth=1, candidate_bank_miss=51, selector_rejected_truth=4, structural_probe_rejected_truth=5 |
| `sin(x1)` | backward_removed_anchor_truth=6 |
| `sin(x2)` | backward_removed_anchor_truth=12, candidate_bank_miss=34, structural_probe_rejected_truth=2 |
| `x1` | backward_removed_anchor_truth=74, selector_rejected_truth=4, structural_probe_rejected_truth=18 |
| `x1^2` | backward_removed_anchor_truth=5, candidate_bank_miss=41, selector_rejected_truth=4, structural_probe_rejected_truth=30 |
| `x1^3` | backward_removed_anchor_truth=2, backward_removed_forward_truth=1, selector_rejected_truth=34, structural_probe_rejected_truth=20 |
| `x3^2` | backward_removed_anchor_truth=30, backward_removed_forward_truth=2, candidate_bank_miss=11, structural_probe_rejected_truth=39 |

## Paired ablation diagnosis

| A | B | A-only exact | B-only exact | Δ exact | post-hoc McNemar p |
|---|---|---:|---:|---:|---:|
| role-v4-no-backward | role-v4-full | 49 | 0 | +0.1089 | 3.55e-15 |
| role-v4-no-backward | legacy-certificate | 7 | 54 | -0.1044 | 4.32e-10 |
| role-v4-no-backward | crossfit-v2-structural | 10 | 32 | -0.0489 | 0.000941 |
| role-v4-no-backward | stability-superset-v3 | 22 | 1 | +0.0467 | 5.72e-06 |
| role-v4-full | role-v4-no-role-conditioning | 45 | 0 | +0.1000 | 5.68e-14 |
| role-v4-full | role-v4-no-path-persistence | 5 | 0 | +0.0111 | 0.0625 |

## Mechanism conclusion

1. **Backward pruning is rejected for continuation.** The preregistered v4 gate already showed 49 exact harms and zero exact gains. The paired ablation is therefore treated as mechanistic support for a forward-only successor, not as permission to retune v4.
2. **Candidate completeness remains the primary target.** A successor must expose more plausible truth terms before the independent selector/probe gates, especially correlated polynomial siblings and restricted-domain exceptions.
3. **Role conditioning and path persistence are retained as hypotheses.** They are not claimed as independently confirmed contributions from this post-hoc report.
4. **Score-only search may propose but never decide structure.** Its very high recall and low NMSE coexist with poor exact recovery and high spurious acceptance.
5. **No final-seed work is authorized.** Any successor requires a new frozen protocol and fresh development seeds.

## Scientific boundary

These statistics reuse the spent v4 development matrix and are post-hoc mechanism diagnostics. They must not be represented as preregistered confirmatory evidence or used to retune v4.
