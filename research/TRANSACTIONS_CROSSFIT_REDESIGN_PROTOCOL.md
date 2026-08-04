# Transactions cross-fitted certificate redesign protocol

Status: **frozen before redesign result inspection**

## 1. Scientific question

The completed external studies identified two reproducible failure boundaries of the
current full FedFalsify path:

1. conservative certificate/target-MSE stopping on the UCI Beijing 12-station
   prediction task;
2. a linear surrogate replacing the squared-energy mechanism in SRSD
   `feynman-ii.27.18`.

This study asks whether theory-aligned sample separation and governed
validation-based continuation can reduce underfitting **without increasing local
shortcut acceptance**. It is a development study, not final confirmation.

Existing Beijing and SRSD artifacts are immutable and are not used for parameter
selection.

## 2. Frozen redesign

Each client is partitioned deterministically into:

- cross-fit discovery fold A: 40% of local observations;
- cross-fit discovery fold B: 40%;
- validation partition: 20%.

The partition seed is derived from the preregistered development seed and client
identifier. Partitions are disjoint and collectively exhaustive.

Two sample-split discovery directions are executed:

- direction A fits coefficients on fold A and creates falsification certificates
  only on fold B;
- direction B fits on fold B and certifies only on fold A.

The primary cross-fit term set is the intersection of the two nonzero discovered
term sets plus the intercept. Coefficients are refitted from aggregate normal
summaries over both discovery folds.

### Governed continuation/fallback

The following candidates are generated without inspecting validation outcomes:

- cross-fit intersection;
- cross-fit union;
- direction-A term set;
- direction-B term set;
- score-only federated forward search on the combined discovery folds.

A non-primary candidate may replace the cross-fit intersection only if all frozen
conditions hold:

1. validation MSE improves by at least 1% relative;
2. validation information score improves after finite-catalog complexity penalty;
3. worst-client validation MSE is no more than 5% worse;
4. at least 60% of clients are non-degraded within a 2% tolerance;
5. every newly added term has cross-client residual support on the validation
   partitions: at least half of observable clients support it and weighted sign
   agreement is at least 0.5.

Among admissible candidates, the lowest validation information score is selected.
If none is admissible, the cross-fit intersection remains final. After term
selection, coefficients are refitted once on all local development observations.
No observation rows are transmitted.

## 3. Frozen development matrix

Fresh development seeds: `13001--13005`.

The matrix contains:

- benchmarks: `base`, `poly3`, `nested_sine`, `trig_product`, `interaction`;
- scenarios: `complementary`, `spurious`, `exception`;
- requested noise ratios: `0.03`, `0.10`, `0.20`;
- samples per client: `120`, `300`;
- clients: `4`;
- maximum finite terms: `6`.

This gives 450 matched conditions. The compared methods are:

- legacy certificate-guided FedFalsify;
- cross-fit intersection without governed continuation;
- proposed cross-fit governed method;
- score-only federated forward search;
- centralized finite-catalog forward search.

Frozen confirmatory seeds `9001--9020`, PySR validation seeds `10501--10505`, and
untouched final-confirmation seeds `11001+` are prohibited.

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

The benchmark/seed condition, not individual observations, is the inferential
unit.

## 5. Frozen success and failure interpretation

The proposed method is considered promising for later independent confirmation
only if all conditions hold:

- overall exact recovery is not more than 0.02 below legacy;
- mean global-test NMSE is lower than legacy;
- spurious acceptance is not more than 0.01 above legacy;
- exact recovery on the `poly3`/`interaction` high-noise subset improves by at
  least 0.05 over legacy;
- fallback does not activate disproportionately on spurious scenarios.

Failure of any criterion is retained and blocks final confirmation of the
redesign. These thresholds are development gates, not claims of statistical
significance.

## 6. Governance

- no external-study rows are used for tuning;
- no benchmark, seed, or failed method row may be removed;
- non-finite output is a visible failure;
- all settings and source files are hashed in the result manifest;
- a smoke test may validate software behavior but cannot replace the complete
  matrix;
- final-confirmation seeds remain untouched even if development results are
  positive;
- the PR remains draft and unmerged until all remaining Transactions gates are
  complete.
