# Phase 3B Engineering Verification

**Date:** 2026-09-08  
**Execution branch:** `research/phase3b-scientific-implementation`  
**Frozen scientific source executed in Colab:** `b67a07371bcf244728536028593373ca7d1990b1`  
**Frozen engineering protocol SHA256:** `afcbc20da959a34b4f4e052ea0270ca98a3724fe9c8ec76edb2cc4c39b716be9`  
**Post-run reproducibility-wrapper seal head:** `6e031a78fa6a1ab4f6dfef3d46ced3efd1d8b8ee`  
**Post-run wrapper-seal CI run:** `34198093831`  
**Engineering seed:** `29300` only

## 1. Scope and decision boundary

This report records the Phase-3B engineering integration evidence for FedFalsify v12 / SCSV-NCSC. The engineering protocol was frozen before the first execution of seed `29300`. The run is an integration/reproducibility smoke, not a development-performance sample.

The only protocol-defined engineering decision is `PHASE3-ENGINEERING-PASS` or `PHASE3-ENGINEERING-FAIL`, based exclusively on test-gate, completeness, method-set, seed/firewall, integrity, artifact, and ZIP criteria. Exact recovery, NMSE, precision/recall, runtime, communication, and method comparisons are descriptive only and are not used to tune or accept the scientific method.

No scientific GO/NO-GO claim is made from seed `29300`.

## 2. Frozen scientific and seed provenance

The successful Colab execution checked out the detached scientific source commit

`b67a07371bcf244728536028593373ca7d1990b1`

and verified the protocol SHA256

`afcbc20da959a34b4f4e052ea0270ca98a3724fe9c8ec76edb2cc4c39b716be9`.

The successful execution used only seed `29300`. The following namespaces remained blocked during the engineering protocol:

- spent Phase-1 development: `29101--29105`;
- spent Phase-2 development: `29201--29205`;
- fresh Phase-3 development: `29301--29310`;
- final confirmation: `11001--11999`.

No Phase-3 fresh-development harness was created or executed as part of this verification.

## 3. Frozen comparator integrity

The frozen comparator files remain byte-identical to the sealed comparator reference. Current Git blob identities are:

| File | Git blob SHA |
|---|---|
| `src/fedfalsify/scsv_v11.py` | `2704a9447ad19964a9eb1847c4ad081732494b6f` |
| `src/fedfalsify/scsv_v11_study.py` | `35e54100107538758c056a1a9a45cd2319f7fec2` |
| `src/fedfalsify/scsv_v10_benchmarks.py` | `11c0046f53e83d9a0b188e391eba4cdec234fac8` |

The current wrapper-seal CI also ran the frozen comparator diff against `78d0ab7ca7afb1edfa4725a45dfd20ce2db39659` and passed before the remaining test groups.

## 4. Deterministic test evidence

### Pre-execution Colab gate

The successful engineering notebook ran in a clean isolated environment with:

- Python `3.13.15`;
- NumPy `2.1.3`;
- SciPy `1.16.3`;
- pandas `2.2.3`;
- joblib `1.5.3`;
- pytest `8.4.2`.

The complete pinned-source test gate passed before `29300` was authorized. The pytest progress output contains `249` test cases with zero failures. The scientific runner did not start until this gate had passed.

### Post-run reproducibility-wrapper seal

After the successful run, only the Colab infrastructure/wrapper was repaired so the checked-in notebook exactly represents the fresh-runtime execution path that succeeded. The final wrapper-seal CI run `34198093831` at head `6e031a78fa6a1ab4f6dfef3d46ced3efd1d8b8ee` passed:

- frozen comparator diff;
- frozen v11 tests: `6`;
- Batch-A focused tests: `19`;
- Batch-B focused tests: `13`;
- Batch-C focused tests: `7`;
- Batch-D engineering/wrapper focused tests: `16`;
- full current repository suite: `256` tests, zero failures.

These post-run wrapper changes do not modify the frozen scientific source executed at `b67a073...` and do not rerun seed `29300`.

## 5. Scientific invariant review

The pre-run line-by-line review and tests established the following frozen invariants:

- SCR final shared certification uses Selector evidence and Holm `alpha_shared = 0.05`.
- NCEE provisional role construction uses Discovery evidence only and BH `q_role = 0.10`.
- Localized active support floor is `10` rows per client.
- Localized FULL-model residual degrees-of-freedom floor is `5`.
- Maximum localized role fraction is `0.50`, with at least one outside client.
- Selector localized screening can only remove/screen a frozen hypothesis; it cannot create or change one.
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

Phase-3B uses the sealed sufficient-statistic and deterministic linear-algebra foundation from Phase 3A. The six-condition centralized/federated parity audit recorded these maximum absolute discrepancies:

| Quantity | Maximum absolute error |
|---|---:|
| Gram entries | `7.275957614183426e-12` |
| target cross-products | `2.7284841053187847e-12` |
| reconstructed SSE | `2.0463630789890885e-12` |

No scientific threshold was adjusted to obtain these numerical equivalences. The Phase-3B engineering package did not emit a separate new centralized/federated maximum-discrepancy table, so this report does not invent one; it records the sealed numerical foundation actually reused by Phase 3B.

## 7. Engineering matrix and integrity result

All six prespecified engineering conditions completed with exactly four method rows per condition:

1. `quadratic_role_v10 | K=4 | balanced | single | noise=0.10 | 29300`
2. `trig_role_v10 | K=4 | balanced | single | noise=0.30 | 29300`
3. `null_role_v10 | K=8 | balanced | none | noise=0.10 | 29300`
4. `anchor_contamination_null_v10 | K=8 | balanced | none | noise=0.30 | 29300`
5. `weak_source_role_v10 | K=8 | balanced | quarter | noise=0.10 | 29300`
6. `dual_role_v10 | K=8 | imbalanced | quarter | noise=0.30 | 29300`

Exact method set:

- `scsv-elrc-v11-full`;
- `scr-only`;
- `ncee-only`;
- `scsv-ncsc`.

The successful engineering integrity payload reported:

| Integrity item | Recorded result |
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

The runner therefore recorded the protocol-defined integrity decision:

**`PHASE3-ENGINEERING-PASS`**.

## 8. Successful archive identifiers

The successful run reported final ZIP SHA256:

`6e6827ae156f2057ef15b9f0feb511779d279e1ab0317d206762bdbba7a54db7`

The in-run manifest recorded:

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

The manifest intentionally excludes itself and the ZIP to avoid self-reference. The Colab wrapper independently reopened the ZIP and reported `testzip()` success after the runner package step.

### External archive-audit limitation

At the time this report was written, the chat handoff contained the complete console transcript but not the binary ZIP itself. Therefore two Task-12 archive checks are **not independently replayed outside Colab in this report**:

1. reloading `phase3_engineering_state.pkl` and `phase3_engineering_state.joblib` from the delivered archive bytes;
2. recomputing every manifest SHA256 from the delivered archive bytes and comparing them line-by-line with the manifest.

Their creation, presence, hashing, and ZIP CRC verification succeeded inside the governed run, but an external byte-level replay requires the actual `FedFalsify_PHASE3_NCSC_ENGINEERING_RESULTS.zip`. This limitation does not change the runner's protocol-defined `PHASE3-ENGINEERING-PASS`; it prevents this report from claiming an independent external archive replay that has not yet occurred.

## 9. Non-scientific infrastructure defects repaired

Before the successful `29300` execution, several Colab-only infrastructure failures were diagnosed. Every failure stopped before seed execution:

1. The original Colab test invocation was contaminated by the ambient Colab environment. A clean Python 3.13 reproduction and then the exact Colab numerical dependency versions passed the pinned source tests.
2. An intermediate recovery wrapper assumed `/content/fedfalsify_phase3_pinned` persisted across Colab runtime restarts; a fresh runtime correctly showed that `/content` is ephemeral.
3. One intermediate handoff accidentally contained notebook-builder code that attempted to write `/mnt/data`, a path belonging to the artifact-generation environment rather than Colab.
4. The successful wrapper became self-contained: it clones the exact frozen source into `/content`, checks out the detached frozen commit, verifies the protocol, creates an isolated environment, disables unrelated pytest plugin auto-loading, runs the complete test gate, and only then authorizes `29300`.

No scientific constant, hypothesis family, split rule, capacity, rank rule, outside-role tolerance, candidate grammar, or evaluation target changed during these repairs.

After the successful run, the repository's checked-in builder/notebook and tests were updated solely to preserve that successful fresh-runtime wrapper path. TDD for this post-run infrastructure seal first demonstrated that the old checked-in wrapper failed the strengthened fresh-runtime tests; the corrected wrapper then passed focused and full CI. Seed `29300` was not rerun for this wrapper-seal work.

## 10. Descriptive engineering observations — not a decision gate

The six-condition smoke produced the following descriptive averages:

| Method | Exact recovery | Shared recall | Deviation recall | Test NMSE | Runtime ratio vs v11 | Communication ratio vs v11 |
|---|---:|---:|---:|---:|---:|---:|
| `scsv-elrc-v11-full` | `0.666667` | `0.944444` | `0.833333` | `0.005910` | `1.000000` | `1.000000` |
| `scr-only` | `0.333333` | `0.944444` | `0.500000` | `0.022968` | `1.002378` | `1.001794` |
| `ncee-only` | `0.333333` | `0.944444` | `0.333333` | `0.088480` | `0.985799` | `0.933391` |
| `scsv-ncsc` | `0.333333` | `0.944444` | `0.500000` | `0.022968` | `0.986501` | `0.934300` |

Per-condition exact recovery in this engineering-only sample was:

| Condition | v11 | SCR-only | NCEE-only | SCSV-NCSC |
|---|---:|---:|---:|---:|
| quadratic role, noise 0.10 | 1 | 0 | 0 | 0 |
| trig role, noise 0.30 | 0 | 0 | 0 | 0 |
| null role, noise 0.10 | 1 | 1 | 1 | 1 |
| anchor-contamination null, noise 0.30 | 1 | 1 | 1 | 1 |
| weak-source role, noise 0.10 | 1 | 0 | 0 | 0 |
| dual role, noise 0.30 | 0 | 0 | 0 | 0 |

These six observations are too small and were explicitly designated as engineering-only. They do not justify a scientific rule change, a scientific rejection, or a superiority claim.

## 11. Prospective scientific-review items recorded without tuning

The mechanism ledger exposes questions that should be reviewed **prospectively before any fresh Phase-3 development protocol is frozen**, without changing the current method in response to `29300`:

- In some localized-role geometries, an exception basis can be rank-collinear with its source term on a role client when that client's entire local support lies inside the exception scope. The NCEE ledger then records `STRUCTURAL-RANK-AMBIGUOUS`. This is a structural identifiability question, not evidence for post-hoc threshold tuning.
- SCR can independently remove a true ordinary term or retain an extra ordinary term in difficult conditions. The appropriate prospective question is whether the prespecified shared hypothesis family and independent partial-F estimand are structurally aligned with the benchmark target, not whether `alpha_shared` should be tuned from `29300`.
- The dual-role difficult condition remained unresolved by all branches in this smoke. No rescue mechanism may be introduced from this one engineering condition.

These items are recorded only to define what a separate fresh-development protocol review must reason about before spending `29301--29310`.

## 12. Engineering conclusion and stop condition

The governed Colab run itself satisfies the protocol-defined engineering integrity gate and records:

**`PHASE3-ENGINEERING-PASS`**.

The scientific implementation is therefore suitable to **freeze as an engineering integration artifact and enter a separate prospective fresh-development protocol review**. This statement is not a scientific GO and does not authorize immediate execution of `29301--29310`.

At this checkpoint:

- `29300` is spent for engineering integration and may not be used for tuning;
- `29301--29310` remain untouched and unauthorized pending a separately reviewed frozen development protocol;
- `11001--11999` remain untouched and blocked;
- no final-confirmation run is authorized;
- no scientific superiority claim is authorized.

For a fully independent external archive seal, upload the successful `FedFalsify_PHASE3_NCSC_ENGINEERING_RESULTS.zip` and replay the two binary/hash checks listed in Section 8 before labeling the archive handoff independently verified.
