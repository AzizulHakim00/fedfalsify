# HR-VFS v5 Post-Evidence Forensic Analysis Plan

**Status:** frozen while the primary 4,500-row v5 development matrix is still running.  
**Purpose:** define the analysis that will be performed after sealed v5 evidence exists, without modifying the frozen algorithm, thresholds, candidate order, seeds, or GO/NO-GO criteria.

## 1. Scientific boundary

The primary result is the preregistered development gate in `high_recall_v5_study.py`. This forensic analysis is secondary. It may explain a GO or NO-GO result but must not retroactively change the primary decision.

The running evidence job is pinned to source commit `6d4278c947d71f6e28a64f71a2c4b2e1101b7d01`. Fresh v5 seeds `17101--17105` are considered spent once execution begins.

No post-evidence change is permitted to:

- HR-VFS proposal or acceptance rules;
- selector/probe thresholds;
- correlation threshold or bundle cap;
- bank-size or final-model-size cap;
- benchmark matrix;
- seed set;
- primary GO/NO-GO criteria.

## 2. Evidence integrity checks before analysis

Forensic analysis begins only after all of the following are true:

1. `rows.csv` contains exactly 4,500 rows;
2. ten frozen methods each contribute exactly 450 matched conditions;
3. conditions contain exactly the five benchmarks, three scenarios, three noise levels, two sample sizes and five v5 development seeds;
4. only seeds `17101--17105` appear;
5. `summary.json`, `decision.json`, `manifest.json` and `COMPLETE` exist;
6. SHA-256 digests in the manifest match the retained artifacts;
7. the manifest identifies the pinned execution commit and workflow run;
8. the primary gate has a Boolean GO/NO-GO decision.

If any integrity check fails, scientific interpretation stops and the run is classified as an execution/integrity failure, not an algorithmic result.

## 3. Primary comparisons

All paired comparisons use the matched condition key:

`(benchmark, scenario, noise_ratio, samples_per_client, seed)`.

The following comparisons are frozen:

1. `hr-v5-full` vs `legacy-certificate`;
2. `hr-v5-full` vs `role-v4-no-backward`;
3. `hr-v5-full` vs `crossfit-v2-structural`;
4. `hr-v5-full` vs `stability-superset-v3`;
5. `hr-v5-full` vs `centralized-forward`;
6. `hr-v5-full` vs `score-only-federated`.

Ablation contrasts are:

1. full vs `hr-v5-no-bundle-rescue`;
2. full vs `hr-v5-no-score-proposer`;
3. full vs `hr-v5-no-role-conditioning`.

## 4. Exact-recovery paired analysis

For every frozen comparison record:

- exact-recovery rate of each method;
- exact-only wins: full = 1, comparator = 0;
- exact-only losses: full = 0, comparator = 1;
- ties at success;
- ties at failure;
- paired exact-recovery difference.

For the paired binary discordant counts, report a two-sided exact McNemar/binomial p-value. This is descriptive secondary inference; it does not replace the preregistered gate.

The same analysis is repeated within:

- each benchmark;
- each scenario;
- each noise level;
- each sample size;
- high-noise (`0.20`) conditions;
- each benchmark × noise stratum;
- each scenario × noise stratum.

No subgroup discovered after looking at outcomes may be elevated to a primary claim.

## 5. Structural error taxonomy

Using recorded `discovered_terms` and the benchmark truth terms already used by the study evaluator, classify each non-exact HR-VFS result into mutually auditable structural components:

- missing truth term(s);
- nuisance/spurious extra term(s);
- both missing and extra terms;
- exception-specific miss;
- exact structure with predictive degradation (if observed separately by NMSE).

Report counts by truth term where possible, with special attention to the frozen mechanism targets:

- `x1`;
- `x1^2`;
- `x1^3`;
- `x3^2`;
- `x1*x2`;
- `I(x3>1)*x3^2`.

This taxonomy is explanatory only and cannot alter v5.

## 6. Candidate-bank mechanism analysis

For v5 methods report:

- mean candidate-bank target recall;
- complete-truth-bank coverage;
- median bank size;
- nuisance-bank count;
- exception candidate recall;
- accepted single-term count;
- accepted pair-bundle count;
- single exact-harm count;
- pair exact-harm count.

Mechanism questions are frozen as:

1. Did the score proposer improve truth exposure relative to the no-score ablation?
2. Did pair rescue improve exact recovery specifically where single-term routes failed?
3. Did role conditioning materially affect exception candidate recall/recovery?
4. Did any mechanism increase spurious acceptance or exact-harm events?

## 7. Ablation attribution rule

For each ablation pair, classify matched conditions as:

- full-only exact recovery;
- ablation-only exact recovery;
- both exact;
- neither exact.

A mechanism is called **supportive** only if full-only exact wins exceed ablation-only exact wins and there is no contradictory increase in the corresponding frozen harm endpoint. This wording is descriptive and is not a new gate.

## 8. Predictive performance analysis

For matched conditions report:

- mean and median test NMSE;
- paired NMSE difference;
- fraction of conditions where HR-VFS has lower NMSE;
- benchmark/scenario/noise/sample-size stratification.

A structural improvement accompanied by severe predictive degradation must be explicitly reported rather than hidden by exact-recovery gains.

## 9. Cost analysis

Report runtime and communication for every method:

- mean;
- median;
- ratio of HR-VFS median to legacy median;
- ratio by sample size (`120` vs `300`).

The preregistered runtime and communication gates remain authoritative.

## 10. GO interpretation

If the primary v5 gate passes:

- label v5 **development GO** only;
- do not claim final confirmation;
- do not reuse `17101--17105`;
- freeze a separate independent validation/scalability protocol and fresh seeds before execution;
- perform prior-art review before strong novelty language.

A development GO is not permission to tune v5 further on these data.

## 11. NO-GO interpretation

If the primary gate fails:

- label v5 **frozen NO-GO**;
- retain all failed criteria;
- identify whether the dominant failure is candidate recall, selector/probe rejection, pair necessity, exception recovery, spurious acceptance, predictive performance, or computational cost;
- separate algorithmic failure from execution/integrity failure;
- do not retune on `17101--17105`;
- any successor requires a newly frozen mechanism hypothesis and fresh development seeds.

## 12. Reporting discipline

The final findings document must contain, in order:

1. evidence identity and manifest hashes;
2. primary GO/NO-GO decision and every frozen criterion;
3. overall method table;
4. paired exact-recovery comparisons;
5. benchmark/scenario/noise/sample-size breakdowns;
6. candidate-bank and acceptance mechanism analysis;
7. ablation attribution;
8. structural failure taxonomy;
9. NMSE analysis;
10. runtime/communication analysis;
11. scientific claim boundary and next-stage decision.

No failed criterion may be omitted from the main findings narrative.
