# Transactions cross-fitted certificate redesign protocol

Status: **completed; frozen development protocol; scientific gate failed**

The protocol below was frozen before result inspection. Completed evidence is in
`research/TRANSACTIONS_CROSSFIT_REDESIGN_FINDINGS.md`. Development seeds
`13001--13005` are spent and may not be used for further tuning.

## 1. Scientific question

The completed external studies identified two reproducible failure boundaries of the
current full FedFalsify path:

1. conservative certificate/target-MSE stopping on the UCI Beijing 12-station
   prediction task;
2. a linear surrogate replacing the squared-energy mechanism in SRSD
   `feynman-ii.27.18`.

This study asked whether theory-aligned sample separation and governed
validation-based continuation could reduce underfitting **without increasing local
shortcut acceptance**. It was a development study, not final confirmation.

Existing Beijing and SRSD artifacts were immutable and were not used for parameter
selection.

## 2. Frozen redesign

Each client was partitioned deterministically into:

- cross-fit discovery fold A: 40% of local observations;
- cross-fit discovery fold B: 40%;
- validation partition: 20%.

The partition seed was derived from the preregistered development seed and client
identifier. Partitions were disjoint and collectively exhaustive.

Two sample-split discovery directions were executed:

- direction A fit coefficients on fold A and created falsification certificates
  only on fold B;
- direction B fit on fold B and certified only on fold A.

The primary cross-fit term set was the intersection of the two nonzero discovered
term sets plus the intercept. Coefficients were refitted from aggregate normal
summaries over both discovery folds.

### Governed continuation/fallback

The following candidates were generated without inspecting validation outcomes:

- cross-fit intersection;
- cross-fit union;
- direction-A term set;
- direction-B term set;
- score-only federated forward search on the combined discovery folds.

A non-primary candidate could replace the cross-fit intersection only if all frozen
conditions held:

1. validation MSE improved by at least 1% relative;
2. validation information score improved after finite-catalog complexity penalty;
3. worst-client validation MSE was no more than 5% worse;
4. at least 60% of clients were non-degraded within a 2% tolerance;
5. every newly added term had cross-client residual support on the validation
   partitions: absolute residual correlation at least `0.05`, at least half of
   observable clients supporting it, and weighted sign agreement at least `0.5`.

Among admissible candidates, the lowest validation information score was selected.
If none was admissible, the cross-fit intersection remained final. After term
selection, coefficients were refitted once on all local development observations.
No observation rows were transmitted.

## 3. Frozen development matrix

Fresh development seeds: `13001--13005`.

The matrix contained:

- benchmarks: `base`, `poly3`, `nested_sine`, `trig_product`, `interaction`;
- scenarios: `complementary`, `spurious`, `exception`;
- requested noise ratios: `0.03`, `0.10`, `0.20`;
- samples per client: `120`, `300`;
- clients: `4`;
- maximum finite terms: `6`.

This gave 450 matched conditions. The compared methods were:

- legacy certificate-guided FedFalsify;
- cross-fit intersection without governed continuation;
- proposed cross-fit governed method;
- score-only federated forward search;
- centralized finite-catalog forward search.

Frozen confirmatory seeds `9001--9020`, PySR validation seeds `10501--10505`, and
untouched final-confirmation seeds `11001+` were prohibited.

## 4. Endpoints

Primary endpoints:

1. exact structural recovery;
2. noiseless global-test NMSE;
3. spurious-variable acceptance;
4. exception recovery.

Secondary endpoints:

- term precision and recall;
- fallback activation rate and selected source;
- validation-to-test concordance;
- worst-client validation error;
- runtime and aggregate communication bytes;
- results stratified by benchmark, scenario, noise, and sample count.

The benchmark/seed condition, not individual observations, was the inferential
unit.

## 5. Frozen success and failure interpretation

The proposed method was considered promising for later independent confirmation
only if all conditions held:

- overall exact recovery was not more than `0.02` below legacy;
- mean global-test NMSE was lower than legacy;
- spurious acceptance was not more than `0.01` above legacy;
- exact recovery at noise ratio `0.20` on the `poly3` and `interaction` subset
  improved by at least `0.05` over legacy;
- fallback activation on spurious scenarios was no more than `0.10` above its
  activation rate on complementary scenarios.

The fourth criterion failed: both legacy and governed exact recovery were `0.35`
on the frozen high-noise subset, for an observed gain of `0.00`. Therefore the
redesign is **NO-GO for final confirmation**.

## 6. Governance

- no external-study rows were used for tuning;
- no benchmark, seed, or failed method row was removed;
- non-finite output was a visible failure;
- all settings and source files were hashed in the result manifest;
- final-confirmation seeds remained untouched;
- completed heavy workflows are frozen;
- another redesign requires a new protocol and fresh development seeds;
- the PR remains draft and unmerged.
