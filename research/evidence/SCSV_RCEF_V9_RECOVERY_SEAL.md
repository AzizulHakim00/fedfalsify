# SCSV-RCEF v9 sharded recovery evidence seal

Status: **DEVELOPMENT-NO-GO**

This record preserves the scientifically complete result from GitHub Actions run `31465220024` at authorization SHA `a39c5a11ae8d40855a917d62b910f986612ed191`.

## Technical integrity

All five fresh recovery shards (`27101`, `27102`, `27103`, `27104`, `27105`) completed successfully. Each shard contained exactly 120 matched conditions and 720 rows across the six frozen methods. The aggregate step verified exactly 600 unique conditions and 3,600 unique method-condition rows, evaluated the frozen A--W criteria once, generated `rows.csv`, `summary.json`, and `decision.json`, created `manifest.json`, `SHA256SUMS`, and `COMPLETE`, and uploaded the sealed combined artifact successfully.

The workflow's final red status was caused only by the repository-write command: `git add results/scsv_v9_recovery` was rejected because that path is ignored by `.gitignore`. This happened after the scientific evidence had already been audited and uploaded. Therefore it is a technical repository-write failure, not an evidence-generation failure and not a reason to discard or rerun the fresh seeds.

Combined artifact:

- artifact name: `scsv-rcef-v9-sharded-recovery-evidence`
- artifact ID: `9092985067`
- artifact ZIP SHA-256: `117f545834b45902860d4fdc9a270e7d68661e66cf93ae149b6136187077abd1`
- retained by the workflow for 30 days

Sealed output hashes from `manifest.json`:

- `rows.csv`: `69e5367d2e91856b2d734d86cc043dd68fdace8ac049099d93d46aca4507ece1`
- `summary.json`: `c5fc1e76645a98d9c5e729b2fd83104d58d7851a1194ce2f057f30e4906e16e2`
- `decision.json`: `b917c68cab7e8c53b916e0aaa105bcbd6e3389c29f54e6598f1feaf4613acae9`

## Frozen scientific decision

`decision.json` states `DEVELOPMENT-NO-GO`. Seven of the 23 preregistered gates failed:

- C: null spurious-deviation acceptance <= 0.02 — **FAIL**, observed `0.3666666667`.
- D: zero exact harms — **FAIL**, observed `1` exact harm.
- F: deviation-bearing exact gain >= 0.04 over matched v8-style — **FAIL**; v9 `0.8604166667` versus v8-style `0.8479166667`, gain `0.0125`.
- G: pooled deviation precision >= 0.99 — **FAIL**, observed `0.9166666667`.
- K: 4-client main-family recovery >= 0.88 — **FAIL**, observed `0.85`.
- N: high-noise main-family recovery >= 0.88 — **FAIL**, observed `0.875`.
- P: dual both-deviation recovery >= 0.90 with no spurious deviations — **FAIL**, observed both-deviation recovery `0.75` (spurious count when both recovered was `0`).

The remaining gates passed, including 600-condition integrity, anchor monotonicity, overall noninferiority, pooled deviation recall, every main-family floor, weak-source recovery, 8-client and 16-client recovery, imbalance robustness, all role/source/pair/evidence-fusion integrity checks, mechanism-superiority, communication, and runtime.

## Permanent boundary

Seeds `27101--27105` are permanently spent. They may be used only for explicitly labelled read-only spent-data forensics. V9 must not be retuned, threshold-adjusted, rerun as fresh evidence, or promoted to independent validation.

Historical labels remain unchanged:

- v6 independent validation: `INDEPENDENT-NO-GO`
- v7 fresh development: `DEVELOPMENT-NO-GO`
- v8 fresh development: `DEVELOPMENT-NO-GO`
- original v9 run `31435708338`: `INFRASTRUCTURE-CANCELLED / NO SCIENTIFIC VERDICT`
- v9 sharded recovery run `31465220024`: `DEVELOPMENT-NO-GO`
