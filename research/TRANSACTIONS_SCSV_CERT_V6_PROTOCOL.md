# FedFalsify SCSV-Cert v6 fresh-development protocol

Status: **FROZEN BEFORE V6 ENGINEERING SMOKE AND BEFORE ANY FRESH V6 DEVELOPMENT SEED**.

This protocol promotes the Set-Conditional Structural Verification (SCSV) mechanism only after the sealed spent-seed exploratory diagnostic returned `MECHANISM-SIGNAL`. The exploratory results are development evidence only and cannot support the v6 confirmatory claim. No v6 rule below may be changed after fresh development seeds begin.

## 1. Scientific question

Can a federated finite-grammar mechanism-discovery system improve exact structural recovery by replacing greedy term-by-term acceptance with truth-independent set selection over a high-recall bank, while keeping an independent structural probe as a **non-destructive certificate** rather than an operational deletion/fallback rule?

The central hypothesis is that the high-recall bank already contains the required mechanism, while path-dependent single-term validation can reject conditionally necessary terms. V6 therefore separates:

1. **structure selection** — choose one complete finite-bank structure on selector summaries;
2. **structural certification** — audit that already-selected structure on independent probe summaries;
3. **operational output** — retain the selector-chosen structure regardless of certificate outcome, while reporting the certificate status term-by-term.

The probe never selects a second-best model, never deletes a term, and never triggers an anchor fallback.

## 2. Frozen mechanism: SCSV-Cert

### 2.1 Data partitioning

Reuse the same leakage-safe partitioning family as the SCSV exploratory diagnostic:

- discovery/fit partition;
- selector partition;
- independent probe partition.

The partition seed is the condition seed. No probe row enters bank construction, coefficient fitting, or structure selection.

### 2.2 High-recall bank

Reuse the frozen v5 bank construction with:

- role-conditioned discovery enabled;
- path persistence enabled;
- discovery-only score proposer enabled;
- raw-correlation bundle rescue disabled;
- maximum bank size 10;
- no truth label used in bank formation.

### 2.3 One-shot sufficient-statistic packets

For the fixed bank `B`, each client sends partition-specific aggregate packets:

- `n`;
- `G = X_B^T X_B`;
- `c = X_B^T y`;
- `q = y^T y`;
- per-term observed support metadata.

No raw observation row is transmitted.

Any candidate subset SSE is reconstructed as

`SSE = q - 2 beta^T c + beta^T G beta`.

### 2.4 Admissible structural family

- intercept is always retained;
- at most five nonconstant terms (`max_terms = 6` including intercept);
- bank size at most 10;
- therefore at most 638 deterministic candidate structures.

No truth-dependent subset restriction is permitted.

### 2.5 Fit and selector

For every admissible subset:

1. fit coefficients from pooled federated fit sufficient statistics;
2. evaluate selector aggregate MSE and worst-client MSE;
3. compute the frozen information score

`log(MSE) + complexity * log(N) / N`;

4. choose exactly one set by minimum information score;
5. tie-break by lower catalog complexity, then fewer nonconstant terms, then lexical ordered term tuple.

The selected structure is the **v6 operational structure**.

### 2.6 Independent non-destructive certificate

The independent probe audits the already-selected set only.

For each retained core term:

- leave-one-term-out conditional necessity is evaluated on probe sufficient statistics;
- one-swap surrogate rivals from omitted bank terms are evaluated;
- the existing SCSV aggregate and leave-one-client-out diagnostics are reported unchanged.

For a restricted exception term:

- only eligible gated probe clients enter local necessity;
- outside-domain non-degradation is checked separately;
- identically-zero outside-domain basis values are not counted as local failures.

**Important:** certificate failure does not change the operational structure. It changes only `probe_certified` and the termwise audit record.

## 3. Frozen methods

The development matrix contains exactly these seven methods:

1. `legacy-certificate`;
2. `crossfit-v2-structural`;
3. `hr-v5-full`;
4. `scsv-v6-full` — primary method;
5. `scsv-v6-no-score-proposer` — one-mechanism ablation;
6. `centralized-forward` — finite-catalog upper/reference comparator;
7. `score-only-federated` — high-recall predictive comparator.

No method may be added or removed after fresh seeds begin.

## 4. Frozen benchmark matrix

- 5 benchmarks: `base`, `poly3`, `nested_sine`, `trig_product`, `interaction`;
- 3 scenarios: `complementary`, `spurious`, `exception`;
- noise ratios: `0.03`, `0.10`, `0.20`;
- samples/client: `120`, `300`;
- 4 clients;
- 5 fresh development seeds.

This is 450 matched conditions and **3,150 retained rows** across seven methods.

## 5. Seed firewall

### Engineering smoke only

`19001`

This seed may be used only for implementation verification and may never enter the development summary.

### Fresh v6 development seeds

`19101, 19102, 19103, 19104, 19105`

These seeds are untouched at protocol freeze time. Once any full-study path evaluates one of these seeds, all five are treated as spent v6 development seeds.

Prior v1-v5, SCSV exploratory, validation, final-confirmation and smoke seed blocks are prohibited.

## 6. Primary endpoint

Primary endpoint: **exact structural recovery** of the nonconstant ground-truth term set.

The operational v6 structure is the selector-chosen set, not the certificate-filtered/fallback set.

## 7. Supporting endpoints

Report for every method where applicable:

- term precision;
- term recall;
- test NMSE;
- spurious acceptance;
- exception recovery;
- runtime;
- communication bytes.

For v6 additionally report:

- bank target recall;
- complete-truth bank coverage;
- bank size and nuisance count;
- candidate sets evaluated;
- probe certification fraction;
- necessity-failure count;
- swap-failure count;
- exception eligible-client diagnostics.

The selector-vs-certificate disagreement is a **diagnostic endpoint**, not a second optimized output.

## 8. Frozen development GO/NO-GO criteria

All criteria must pass.

### Structural performance

A. Overall v6 exact recovery >= Legacy + `0.05`.

B. Overall v6 exact recovery >= HR-VFS v5 + `0.10`.

C. High-noise (`0.20`) `poly3` exact recovery >= HR-VFS v5 high-noise `poly3` + `0.10`.

D. High-noise (`0.20`) `interaction` exact recovery >= Legacy high-noise `interaction` - `0.01`.

E. `base` exact recovery >= Legacy `base` - `0.01`.

F. `nested_sine` exact recovery >= HR-VFS v5 `nested_sine` - `0.02`.

G. `trig_product` exact recovery >= HR-VFS v5 `trig_product` - `0.02`.

### Structure quality

H. Mean term precision >= `0.96`.

I. Mean term recall >= `0.95`.

J. Spurious acceptance <= `max(0.05, Legacy + 0.01)`.

K. Exception recovery >= `0.95`.

L. Candidate-bank target recall >= `0.98`.

M. Complete-truth bank coverage >= `0.95`.

### Predictive and certificate sanity

N. Mean test NMSE <= Legacy mean test NMSE.

O. Probe-certification fraction >= `0.75`.

### Engineering feasibility

P. Median communication <= HR-VFS v5 median communication on the same fresh conditions.

Q. Median runtime <= `1.50 x` HR-VFS v5 median runtime on the same fresh conditions.

Any failed criterion freezes v6 as **NO-GO**. Passing permits only a separately frozen independent scalability/external-validation stage; it does not permit a final paper claim by itself.

## 9. Statistical analysis frozen before results

Use matched condition keys `(benchmark, scenario, noise, samples_per_client, seed)`.

Report:

- exact-recovery paired win/loss/tie counts versus Legacy, v5 and v2;
- exact McNemar test for paired binary exact recovery;
- benchmark/scenario/noise/sample-size stratification;
- bootstrap 95% confidence intervals over matched conditions for exact-recovery differences;
- term-level failure taxonomy;
- probe-certificate false-negative diagnostics relative to selector correctness, clearly labeled diagnostic because truth is used only after the structure is frozen.

No subgroup may replace the global primary endpoint.

## 10. Engineering-smoke boundary

Before any v6 development seed is touched, CI must verify on seed `19001` only:

- deterministic subset enumeration;
- sufficient-statistic SSE reconstruction;
- final operational structure equals selector structure regardless of probe result;
- probe remains non-destructive;
- exception eligible-client semantics;
- no use of `19101--19105` in smoke outputs;
- development gate is not evaluated in smoke mode.

Implementation bugs may be fixed using unit fixtures and `19001` only. Scientific thresholds, ranking rules, bank rules and gates may not be changed from fresh v6 outcomes.

## 11. Claim boundary

A v6 GO means only that the SCSV-Cert mechanism replicated on a fresh synthetic development block under the frozen finite grammar. The next stage must independently test scalability, client-count heterogeneity, broader grammars and external/synthetic families under another frozen protocol.

A v6 NO-GO is preserved as a scientific result; no threshold tuning on `19101--19105` is permitted.