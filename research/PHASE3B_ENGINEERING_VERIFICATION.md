# Phase 3B Engineering Verification

**Date:** 2026-09-08  
**Execution branch:** `research/phase3b-scientific-implementation`  
**Frozen scientific source executed in Colab:** `b67a07371bcf244728536028593373ca7d1990b1`  
**Frozen engineering protocol SHA256:** `afcbc20da959a34b4f4e052ea0270ca98a3724fe9c8ec76edb2cc4c39b716be9`  
**Engineering seed:** `29300` only  
**Post-run code/wrapper seal CI:** run `34198093831` at `6e031a78fa6a1ab4f6dfef3d46ced3efd1d8b8ee`

## 1. Scope and decision boundary

This report closes the Phase-3B engineering-integration task for FedFalsify v12 / SCSV-NCSC. The engineering protocol was frozen before the first execution of seed `29300`. The six-condition run is an integration, reproducibility, persistence, and mechanism-ledger smoke; it is **not** a development-performance sample.

The protocol-defined engineering decision is based only on test-gate, completeness, method-set, seed/firewall, artifact, checkpoint, and ZIP-integrity criteria. Exact recovery, NMSE, precision/recall, runtime, communication, and method comparisons are descriptive only and were not used to tune or accept the scientific method.

**No scientific GO/NO-GO claim is made from seed `29300`.**

## 2. Frozen scientific and seed provenance

The successful Colab execution checked out the detached scientific source commit:

`b67a07371bcf244728536028593373ca7d1990b1`

and verified protocol SHA256:

`afcbc20da959a34b4f4e052ea0270ca98a3724fe9c8ec76edb2cc4c39b716be9`.

Only seed `29300` was used by the Phase-3 engineering matrix. Fresh Phase-3 development seeds `29301--29310` and final-confirmation seeds `11001--11999` remained blocked and untouched. No fresh-development harness was created or executed as part of Phase-3B engineering verification.

## 3. Frozen comparator integrity

The frozen comparator files remain byte-identical to the sealed comparator reference:

| File | Git blob SHA |
|---|---|
| `src/fedfalsify/scsv_v11.py` | `2704a9447ad19964a9eb1847c4ad081732494b6f` |
| `src/fedfalsify/scsv_v11_study.py` | `35e54100107538758c056a1a9a45cd2319f7fec2` |
| `src/fedfalsify/scsv_v10_benchmarks.py` | `11c0046f53e83d9a0b188e391eba4cdec234fac8` |

The post-run code/wrapper seal CI passed the frozen-comparator diff against Phase-3A seal `78d0ab7ca7afb1edfa4725a45dfd20ce2db39659` before running the remaining test groups.

## 4. Deterministic test evidence

### Successful Colab pre-execution gate

The successful engineering notebook ran in an isolated environment with Python `3.13.15`, NumPy `2.1.3`, SciPy `1.16.3`, pandas `2.2.3`, joblib `1.5.3`, and pytest `8.4.2`. The complete pinned-source test gate passed before the runner authorized seed `29300`.

### Post-run code/wrapper seal

After the successful engineering run, the checked-in Colab wrapper was made self-contained for a fresh Colab runtime without changing the frozen scientific source. CI run `34198093831` at head `6e031a78fa6a1ab4f6dfef3d46ced3efd1d8b8ee` passed:

- frozen comparator diff;
- frozen v11 tests: `6`;
- Batch-A focused tests: `19`;
- Batch-B focused tests: `13`;
- Batch-C focused tests: `7`;
- Batch-D engineering/wrapper focused tests: `16`;
- full current repository suite: `256` tests, zero failures.

The post-run wrapper work did not rerun `29300` and did not modify scientific thresholds, candidate families, split roles, capacity rules, rank policy, or outside-role safety.

## 5. Scientific invariant review

The reviewed implementation preserves the frozen Phase-3B invariants:

- SCR final shared certification uses Selector evidence and Holm `alpha_shared = 0.05`.
- NCEE provisional role construction uses Discovery evidence only and BH `q_role = 0.10`.
- Localized active-support floor is `10` rows per client.
- Localized FULL-model residual-df floor is `5`.
- Maximum localized role fraction is `0.50`, with at least one outside client.
- Selector localized screening can only remove/screen a frozen hypothesis.
- Probe cannot nominate a term, change a role/source, or alter the Discovery sign.
- Final Probe localized multiplicity control is Holm `alpha_dev = 0.05` over the frozen family.
- Outside-role non-degradation tolerance is exactly `1e-10` SSE units.
- Shared capacity is at most five non-intercept terms plus intercept.
- Localized capacity is at most two accepted deviations.
- Final capacity is at most ten terms including intercept.
- Rank handling is deterministic and machine-scale; no tuned ridge or outcome-dependent rank threshold is introduced.
- Benchmark truth is evaluation metadata only and does not enter scientific acceptance functions.
- Engineering PASS does not inspect descriptive performance metrics.

## 6. Numerical foundation inherited from sealed Phase 3A

Phase-3B reuses the sealed sufficient-statistic and deterministic linear-algebra foundation from Phase 3A. The centralized/federated parity audit recorded maximum absolute discrepancies:

| Quantity | Maximum absolute error |
|---|---:|
| Gram entries | `7.275957614183426e-12` |
| target cross-products | `2.7284841053187847e-12` |
| reconstructed SSE | `2.0463630789890885e-12` |

No scientific threshold was adjusted to obtain those equivalences.

## 7. Engineering matrix and integrity result

All six prespecified engineering conditions completed with exactly four rows each:

1. `quadratic_role_v10 | K=4 | balanced | single | noise=0.10 | 29300`
2. `trig_role_v10 | K=4 | balanced | single | noise=0.30 | 29300`
3. `null_role_v10 | K=8 | balanced | none | noise=0.10 | 29300`
4. `anchor_contamination_null_v10 | K=8 | balanced | none | noise=0.30 | 29300`
5. `weak_source_role_v10 | K=8 | balanced | quarter | noise=0.10 | 29300`
6. `dual_role_v10 | K=8 | imbalanced | quarter | noise=0.30 | 29300`

Exact method set per condition:

- `scsv-elrc-v11-full`
- `scr-only`
- `ncee-only`
- `scsv-ncsc`

The delivered integrity payload records:

| Integrity item | Result |
|---|---:|
| expected conditions | `6` |
| complete conditions | `6` |
| expected primary rows | `24` |
| primary rows | `24` |
| valid primary rows | `24` |
| duplicate/partial rows | `0` |
| integrity violations | `0` |
| seed set | `[29300]` |
| test gate passed before execution | `true` |
| base artifacts OK | `true` |
| ZIP verified | `true` |

The protocol-defined engineering decision is therefore:

**`PHASE3-ENGINEERING-PASS`**.

## 8. Independent external archive replay — COMPLETE

The delivered binary archive `FedFalsify_PHASE3_NCSC_ENGINEERING_RESULTS.zip` was independently replayed outside Colab after upload to the verification environment.

### ZIP-level checks

- archive size: `130217` bytes;
- external ZIP SHA256: `6e6827ae156f2057ef15b9f0feb511779d279e1ab0317d206762bdbba7a54db7`;
- the external SHA exactly matches the SHA printed by the governed Colab run;
- `zipfile.ZipFile(...).testzip()` returned `None`;
- archive contains the expected 14 members: 13 hash-governed artifacts plus `phase3_engineering_sha256.txt`; the ZIP itself is naturally external to its own archive.

### Manifest replay

The manifest contains 13 non-self-referential SHA256 entries. Every delivered artifact independently recomputed to exactly the recorded SHA:

| Artifact | SHA256 |
|---|---|
| `FROZEN_PHASE3_ENGINEERING_PROTOCOL.md` | `afcbc20da959a34b4f4e052ea0270ca98a3724fe9c8ec76edb2cc4c39b716be9` |
| `phase3_engineering_ablation_summary.csv` | `1d3e037cb7f73e59b110c0706a325a028e8ef8cb21fce7c7a8932604f2d82150` |
| `phase3_engineering_checkpoint.csv` | `8e24de9c9ebdf649c542b3340f6dea1d5f344c6036e138cf7b6590469c2c9e97` |
| `phase3_engineering_decision.json` | `023c11a4f18c755a50d7fd9930a8c10aee2c2e4f50d359de27d57da14cb51908` |
| `phase3_engineering_environment.json` | `0c04130828915fff529acba4cd95eee87be05a285a3002ccfcabf7a09387dcd0` |
| `phase3_engineering_integrity.json` | `e54d6fde865fe965e16e4faaf0f12e755d8193e32a61b734a7de8079e290cac5` |
| `phase3_engineering_localized_diagnostics.csv` | `a957a189c828fea8adfd2b9aa39bdbd172cf70501b40aca0fe10a56d03e98d42` |
| `phase3_engineering_method_summary.csv` | `708f9fcc0b5f5e1826ffd349c0f23ef9ab22b0089aa906c4a92c4aa25bc7153e` |
| `phase3_engineering_report.txt` | `e9c0449a26dbc43dcd1e1b68e2ec61baa09fa832d03a5429cfd0f008bf57a776` |
| `phase3_engineering_rows.csv` | `8e24de9c9ebdf649c542b3340f6dea1d5f344c6036e138cf7b6590469c2c9e97` |
| `phase3_engineering_shared_diagnostics.csv` | `459d28549ab798507164d818a3617823b1c2571cd436092801a475827d5f9485` |
| `phase3_engineering_state.joblib` | `880cf82b41fcb25b550e1b28b8755059ba6adb63f2baf1d487a22b3eb809cfc9` |
| `phase3_engineering_state.pkl` | `8e0d7b6e20e66f5650291439711bd037954509ce45945b104bb3e84e9526d9d2` |

All 13 comparisons passed exactly.

### Checkpoint and primary-row replay

- `phase3_engineering_checkpoint.csv` and `phase3_engineering_rows.csv` are byte-identical;
- primary table has `24` rows and `35` columns;
- the six condition keys are present exactly once as complete four-method groups;
- every group contains the exact four-method set;
- duplicate `(condition, method)` rows: `0`;
- row-level integrity-violation values: all `0`;
- seed values: only `29300`.

### PKL/joblib replay

Both `phase3_engineering_state.pkl` and `phase3_engineering_state.joblib` loaded successfully. Each contains the same state dictionary with:

- `schema_version`;
- `engineering_seed = 29300`;
- the exact four-method tuple;
- `6` completed condition keys;
- `24` persisted primary rows.

The PKL and joblib objects compare equal. When compared with the CSV representation, the only parser-level representation difference is that empty `accepted_deviations` strings become `NaN` under default pandas CSV parsing; this is not a scientific or state-content discrepancy.

### Summary reconstruction

`phase3_engineering_method_summary.csv` was independently reconstructed from `phase3_engineering_rows.csv` using means for the declared accuracy/NMSE metrics and medians for runtime/communication. It matches the delivered summary to floating-point roundoff, with maximum absolute numerical discrepancy no larger than approximately `1.11e-16` across direct summary metrics.

`phase3_engineering_ablation_summary.csv` was then independently reconstructed from the method summary relative to v11. It matches to floating-point roundoff, with maximum absolute discrepancy no larger than approximately `2.22e-16`.

The shared-diagnostics table contains `80` rows and the localized-diagnostics table contains `128` rows; both contain only seed `29300` and the exact four governed method IDs.

**External archive replay result: PASS.**

## 9. Non-scientific infrastructure defects repaired

Before the successful `29300` execution, several Colab-only infrastructure failures were diagnosed. Every failed attempt stopped before scientific seed execution. The final successful wrapper became self-contained: it clones the exact frozen source into ephemeral `/content`, checks out the detached frozen commit, verifies the protocol, creates an isolated environment, disables unrelated pytest plugin auto-loading, runs the complete test gate, and only then authorizes `29300`.

No scientific constant, hypothesis family, split rule, capacity, rank rule, outside-role tolerance, candidate grammar, or evaluation target changed during those repairs. Seed `29300` was not rerun for the later repository wrapper-seal work.

## 10. Descriptive engineering observations — not a decision gate

The six-condition engineering sample produced:

| Method | Exact recovery | Shared recall | Deviation recall | Test NMSE | Runtime ratio vs v11 | Communication ratio vs v11 |
|---|---:|---:|---:|---:|---:|---:|
| `scsv-elrc-v11-full` | `0.666667` | `0.944444` | `0.833333` | `0.005910` | `1.000000` | `1.000000` |
| `scr-only` | `0.333333` | `0.944444` | `0.500000` | `0.022968` | `1.002378` | `1.001794` |
| `ncee-only` | `0.333333` | `0.944444` | `0.333333` | `0.088480` | `0.985799` | `0.933391` |
| `scsv-ncsc` | `0.333333` | `0.944444` | `0.500000` | `0.022968` | `0.986501` | `0.934300` |

These observations are engineering-only and are too small for scientific inference. They do not justify a post-hoc rule change, scientific rejection, or superiority claim.

## 11. Prospective scientific-review items recorded without tuning

The mechanism ledger exposes issues that should be considered only in a **separate prospective review before any fresh-development protocol is frozen**:

- In some localized-role geometries, an exception basis can become rank-collinear with its source term on a role client when that client's entire local support lies inside the exception scope; the NCEE ledger can then record `STRUCTURAL-RANK-AMBIGUOUS`. This is an identifiability/design question, not evidence for threshold tuning.
- The engineering sample shows that SCR/NCEE can change exact recovery relative to v11. Because `29300` was not a development sample, those outcomes cannot be used to choose new alpha levels, BH thresholds, support floors, capacities, or safety tolerances.
- The next research action must therefore be a prospective fresh-development protocol review, not an immediate parameter optimization pass.

## 12. Final Phase-3B engineering conclusion

All protocol-defined engineering integrity checks pass, and the delivered archive has now passed an independent byte-level replay.

**PHASE3B-ENGINEERING-SEALED.**

This seal establishes that:

1. the frozen v12 scientific implementation is reproducibly executable under the governed engineering protocol;
2. the six-condition `29300` matrix completed with correct method grouping and no seed/integrity violations;
3. the final archive, hashes, checkpoint, PKL/joblib state, CSV summaries, diagnostics, and ZIP are mutually consistent;
4. the frozen v11 comparator remains unchanged;
5. `29301--29310` and `11001--11999` remain untouched.

This seal **does not** establish scientific superiority or scientific development GO. The next permitted research activity is a separate, prospective review and freeze of the fresh Phase-3 development protocol. No fresh-development or final-confirmation seed may be executed until that separate protocol is approved and frozen.
