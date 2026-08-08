# Set-Conditional Structural Verification (SCSV) exploratory protocol

Status: **frozen exploratory mechanism diagnostic; not v6 evidence**.

This diagnostic is motivated by the sealed HR-VFS v5 NO-GO and its post-hoc forensic report. It is deliberately run only on already-spent v5 development seeds and a dedicated engineering smoke seed. No fresh v6 development seed is authorized by this document.

## 1. Question

The v5 bank contained every true term in all 450 development conditions, but 251 truth-term events were lost downstream, primarily in isolated selector/probe comparisons. The diagnostic asks:

> If the same truth-independent high-recall bank is evaluated as complete candidate **sets** using one-shot federated sufficient statistics, can conditional structural verification recover terms that greedy one-at-a-time falsification rejects?

This is a mechanism diagnostic, not a confirmatory experiment.

## 2. Fixed candidate bank

Reuse HR-VFS v5 bank construction with:

- role-conditioned discovery enabled;
- path persistence enabled;
- discovery-only score proposer enabled;
- raw-correlation bundle rescue disabled because the sealed v5 ablation showed zero exact effect and zero accepted bundles;
- maximum bank size 10;
- no truth label used in bank construction.

The bank is constructed from discovery/fit partitions only.

## 3. One-shot federated sufficient-statistic packets

For a fixed ordered bank `B = (1, b1, ..., bp)`, each client computes separately on fit, selector and probe partitions:

- support `n`;
- Gram matrix `G = X_B^T X_B`;
- target cross-product `c = X_B^T y`;
- target energy `q = y^T y`.

Only these aggregate packets are transmitted. No raw observation row is transmitted.

For any subset `S` of bank columns and coefficient vector `beta_S`, SSE is reconstructed as

`q - 2 beta_S^T c_S + beta_S^T G_SS beta_S`.

Thus every admissible subset can be fitted/evaluated without repeated client communication.

## 4. Admissible set family

Enumerate every deterministic subset of nonconstant bank terms with final model size at most `max_terms = 6` including the intercept.

No truth-dependent family restriction is allowed.

The finite bank size <=10 makes this at most **638** admissible structures (intercept plus 0--5 of 10 nonconstant bank terms) under the current cap, depending on bank size.

## 5. Fit stage

For each admissible subset:

1. aggregate fit-partition sufficient statistics across clients;
2. solve ridge-stabilized normal equations using fixed numerical ridge `1e-10`, matching the existing prototype's numerical stabilization role;
3. retain fitted coefficients for selector and probe evaluation.

No selector/probe row enters coefficient fitting.

## 6. Selector ranking

For each fitted subset compute on selector sufficient statistics:

- aggregate MSE;
- worst-client MSE;
- existing catalog complexity;
- information score `log(MSE) + complexity * log(N) / N`.

Select exactly **one** candidate set: the minimum information-score subset, ties broken by lower complexity, then fewer nonconstant terms, then lexical ordered term tuple.

The probe is not used to choose among multiple selector candidates. This avoids repeated adaptive probe search.

## 7. Non-destructive probe necessity

The selected set is tested once on independent probe statistics.

For every retained nonconstant **core** term `j`:

1. fit the reduced set `S \ {j}` on fit statistics;
2. compare full versus reduced probe SSE;
3. define the aggregate necessity gain `Delta_j = SSE_reduced - SSE_full`;
4. require `Delta_j > 0`;
5. require leave-one-client-out aggregate stability: `Delta_j` remains positive after excluding each client in turn, whenever at least three observable clients exist.

This is a client-jackknife structural stability requirement. It does not require every client individually to improve and therefore differs from the v5 60% per-client win rule.

For a restricted exception term:

- evaluate necessity on eligible gated probe clients only;
- require positive eligible aggregate necessity gain;
- require global outside-domain non-degradation on selector/probe summaries;
- do not count identically-zero outside-domain basis values as failed local wins.

## 8. Surrogate-swap falsification

For each retained core term `j`, construct one-swap rivals from omitted bank terms with the same catalog `kind` and complexity no greater than `complexity(j)+1`.

For each rival `r`, fit `(S \ {j}) union {r}` on fit statistics and evaluate probe SSE.

The retained term passes swap falsification only when the selected set has lower aggregate probe SSE than every tested one-swap rival. When at least three clients are observable, the advantage must also remain positive under each leave-one-client-out aggregate.

This tests whether the selected structural term is conditionally superior to a close finite-bank substitute without requiring raw-correlation pair formation.

## 9. Diagnostic output

Record per condition:

- selected bank;
- selected set;
- exact recovery, precision, recall, NMSE;
- selector information score;
- probe necessity pass/fail per term;
- one-swap pass/fail per term;
- whether the full selected set passes all probe checks;
- communication bytes for all sufficient-statistic packets;
- runtime;
- exception diagnostics.

For diagnosis, also retain an `unverified-selector-set` result and a `probe-validated-set` result. The former measures selector capacity; the latter measures structural verification.

## 10. Exploratory seeds and matrix

### Engineering smoke

Use `18001` only.

### Spent diagnostic seeds

Use the already-spent v5 seeds:

`17101, 17102, 17103, 17104, 17105`.

These results are explicitly post-hoc exploratory and may never be promoted to fresh v6 evidence.

Run all 450 v5 benchmark conditions so the failure map is directly paired with the sealed v5 matrix:

- 5 benchmarks;
- 3 scenarios;
- 3 noise ratios;
- 2 sample sizes;
- 5 spent seeds.

## 11. Exploratory signal criteria

These are **diagnostic signal criteria**, not GO/NO-GO evidence gates.

A mechanism-level signal exists only if all are observed on spent conditions:

1. selector-set exact recovery materially exceeds v5 exact recovery (target diagnostic margin >=0.05);
2. probe-validated exact recovery exceeds v5, not merely selector-only recovery;
3. `poly3` exact recovery improves by at least 0.10 over v5;
4. no material degradation on `nested_sine` or `trig_product` (>0.02 absolute loss);
5. surrogate/nuisance precision is at least v5 precision;
6. median communication is lower than v5 because the bank statistics are transmitted once;
7. the exception path can be implemented with an explicit eligible-client rule and passes dedicated invariant tests.

Failure means SCSV is not promoted to v6. Passing permits a separately frozen v6 protocol with new untouched seeds and a new evidence workflow.

## 12. Scientific boundary

This diagnostic may guide mechanism design because it uses spent development information. It cannot support a confirmatory claim, external-validation claim, or paper headline result. Fresh v6 evidence is prohibited until a later protocol freezes the final mechanism, ablations, fresh seeds, metrics and GO/NO-GO gates.