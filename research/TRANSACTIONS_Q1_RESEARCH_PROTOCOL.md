# FedFalsify Transactions-Scale Research Protocol

## 1. Purpose

This document governs the extension of FedFalsify from a strong synthetic confirmatory study into a serious archival Transactions submission. It is a scientific protocol, not a marketing roadmap. It defines which evidence is frozen, which analyses are post-hoc, which experiments require fresh seeds, how baseline fairness will be enforced, and which claims are permitted only after independent validation.

The intended central contribution is:

> A certificate-guided federated symbolic-discovery framework that uses cross-client falsification to reject locally predictive shortcuts, preserve an invariant symbolic core, and identify supported restricted exceptions without pooling raw client rows.

The paper must not claim universal superiority, formal causal discovery, or formal privacy unless those properties are separately proved and empirically validated.

## 2. Evidence governance

### 2.1 Study A: frozen v0.6 confirmatory evidence

The following evidence is permanently frozen:

- run ID: `v06-primary-confirmatory`;
- seeds: `9001--9020`;
- total method-runs: `2400`;
- evidence commit: `02613c79f88210d37ad1705954207283c03894b3`;
- verified result file: `results/colab/v06-primary-confirmatory/VERIFIED.json`;
- final manifest: `results/colab/v06-primary-confirmatory/final/manifest.json`;
- final Holm report: `results/colab/v06-primary-confirmatory/final/v06_confirmatory_holm.json`.

Study A may be reanalyzed, visualized, or audited. It may not be altered, selectively rerun, or used to retune the method. Any algorithmic change motivated by its failures must be developed on new seeds.

### 2.2 Study B: post-hoc semantic and failure analysis

Study B analyzes the frozen Study A CSV without rerunning the original search. It distinguishes:

1. strict structural recovery;
2. interpolation-level functional recovery;
3. client-support functional recovery;
4. mild extrapolation recovery;
5. strong extrapolation recovery;
6. strict failures that are functionally equivalent;
7. failures caused by missing, extra, surrogate, or unstable terms.

Study B is explicitly post-hoc. Threshold sensitivity must be reported at minimum for NMSE thresholds `1e-4`, `1e-3`, and `1e-2`.

### 2.3 Study C: independent Transactions-scale validation

All new method development uses development seeds beginning at `10001`. Final Transactions confirmation uses a separate untouched seed block beginning at `11001`.

Recommended seed separation:

- development and debugging: `10001--10030`;
- model-selection validation: `10501--10520`;
- final independent confirmation: `11001--11030`;
- external-dataset bootstrap seeds: `12001--12050`.

The final confirmation block must be frozen before execution. No thresholds or algorithmic settings may be changed after its first result is inspected.

## 3. Primary research questions

### RQ1: invariant mechanism recovery

Can FedFalsify recover the invariant symbolic mechanism across heterogeneous clients more reliably than centralized, local, and federated symbolic-regression baselines under matched budgets?

### RQ2: shortcut rejection

Does cross-client falsification reduce acceptance of locally predictive but globally unsupported symbolic terms?

### RQ3: exception identification

Can the framework separate a stable invariant core from restricted, support-qualified exceptions without converting every heterogeneous effect into a global term?

### RQ4: semantic fairness

Does the advantage remain when equations are judged by functional equivalence and extrapolation, rather than only by canonical term identity?

### RQ5: component necessity

Which certificates, replacement rules, and support constraints are responsible for performance, and which components are unnecessary or redundant?

### RQ6: scalability and external validity

Does the method remain reliable as client count, feature count, noise, imbalance, missing clients, and expression complexity increase, and does it produce stable useful expressions on external scientific datasets?

## 4. Claims and corresponding evidence

### Claim C1: strict structural recovery

Required evidence:

- strict exact recovery;
- term precision and recall;
- Wilson confidence intervals;
- paired McNemar tests;
- family-wise multiplicity correction.

### Claim C2: semantic recovery

Required evidence:

- deterministic interpolation NMSE;
- client-support NMSE;
- mild and strong extrapolation NMSE;
- functional-recovery rates at multiple preregistered thresholds;
- expression-complexity-normalized comparisons.

### Claim C3: shortcut rejection

Required evidence:

- nuisance-term acceptance rate;
- local predictive strength of the nuisance term;
- global and leave-one-client-out falsification evidence;
- matched comparisons against local-only and pooled-only variants.

### Claim C4: restricted exception recovery

Required evidence:

- exception detection sensitivity and specificity;
- support calibration;
- false global promotion rate;
- rare-exception stress tests;
- unsupported-exception behavior.

### Claim C5: efficiency

Required evidence:

- wall-clock time;
- candidate evaluations;
- communication bytes;
- client computation;
- server computation;
- Pareto analysis for accuracy, complexity, runtime, and communication.

### Claim C6: data locality

Permitted claim:

> Raw client rows are not pooled by the FedFalsify protocol.

Not permitted without further work:

- differential privacy;
- cryptographic confidentiality;
- resistance to reconstruction or membership inference;
- secure aggregation.

## 5. Evaluation hierarchy

### 5.1 Structural metrics

Report:

- strict exact recovery;
- canonicalized support recovery;
- term precision;
- term recall;
- coefficient relative error;
- extra-term count;
- missing-term count;
- normalized expression complexity.

### 5.2 Semantic metrics

Every reported equation is evaluated on four deterministic domains:

1. global interpolation support;
2. pooled client-support points using noiseless targets;
3. mild extrapolation with domain scale `1.25`;
4. strong extrapolation with domain scale `1.50`.

Primary semantic threshold: NMSE `<= 1e-3` on all four domains.

Sensitivity thresholds: `1e-4` and `1e-2`.

Semantic equivalence does not establish mechanistic identifiability. A functionally accurate but structurally incorrect expression must be reported as such.

### 5.3 Robustness metrics

Report:

- seed stability;
- bootstrap selection frequency;
- leave-one-client-out stability;
- client-order invariance;
- perturbation sensitivity;
- coefficient sign stability;
- equation complexity variability.

## 6. Baseline suite

The final Transactions paper requires both official external systems and controlled internal baselines.

### 6.1 Official external baselines

At minimum:

- official PySR;
- one additional mature symbolic-regression implementation, such as Operon, FEAT, or an equivalent maintained system;
- a conventional genetic-programming baseline using a documented library;
- a local-per-client symbolic-regression baseline followed by consensus aggregation.

Official software versions, commits, operators, coefficient optimizers, and hardware must be archived.

### 6.2 Controlled matched baselines

Required:

- centralized tree GP;
- federated tree-GP-style search;
- residual-counterexample tree GP;
- centralized catalog-matched selector;
- federated catalog-matched selector;
- pooled oracle-support coefficient fit;
- local-only FedFalsify;
- pooled FedFalsify without cross-client falsification.

### 6.3 Budget fairness

Two comparison regimes are mandatory:

1. equal candidate-evaluation budget;
2. equal wall-clock budget.

Also report unconstrained best-effort runs separately. Maximum expression complexity, allowed variables, operators, coefficient fitting, stopping rules, and timeout handling must be disclosed.

Unsupported operators or exception forms must be marked `unsupported`; they must not be silently counted as ordinary failures.

## 7. Ablation matrix

The following variants are required:

| Variant | Scientific question |
|---|---|
| Full FedFalsify | Reference method |
| No cross-client support | Is federation itself necessary? |
| No falsification certificate | Is the central rejection mechanism necessary? |
| No coefficient-heterogeneity certificate | Does coefficient consistency matter? |
| No client-validated replacement | Is surrogate correction necessary? |
| No non-degradation constraint | Does replacement overfit some clients? |
| No shortcut rejection | How much nuisance acceptance returns? |
| No exception module | Are restricted effects promoted globally or lost? |
| Local-only | What is gained by collaboration? |
| Pooled centralized | What is lost or gained by data locality? |
| Fixed catalog | Performance with privileged candidate support |
| Adaptive catalog | Dependence on catalog completeness |

Ablations use development and validation seeds, not Study A seeds.

## 8. Scalability and stress matrix

Minimum factors:

- clients: `3, 4, 8, 16, 32`;
- samples per client: `50, 100, 300, 1000`;
- observed features: `4, 8, 16, 32, 64`;
- irrelevant features: `0, 4, 16, 48`;
- noise ratios: `0, 0.03, 0.10, 0.20, 0.30`;
- client-size imbalance: balanced, moderate long-tail, severe long-tail;
- domain overlap: high, medium, low;
- missing clients at evaluation: `0%, 10%, 30%`;
- exception prevalence: rare, moderate, common;
- catalog misspecification: complete, partially missing, strongly incomplete.

The full Cartesian product is unnecessary. Use a preregistered fractional design that isolates main effects and selected interactions while controlling computational cost.

## 9. External validation

A Transactions submission should contain at least three external study families:

1. established symbolic-regression benchmarks with known ground truth;
2. scientific or engineering data with natural domain/client partitions;
3. a real heterogeneous dataset where stability and predictive usefulness can be assessed even without a known true equation.

Dataset inclusion criteria:

- publicly accessible or redistributable;
- documented variables and units;
- defensible client partition;
- sufficient samples per client;
- no target leakage;
- scientifically interpretable output;
- reproducible preprocessing.

For real data without ground-truth equations, report:

- held-out prediction error;
- leave-one-client-out generalization;
- bootstrap expression stability;
- complexity;
- sign and unit plausibility;
- sensitivity to client partition;
- comparison with accepted domain relationships where available.

## 10. Statistical plan

### 10.1 Primary endpoints

Primary endpoint 1: semantic recovery on all evaluation domains.

Primary endpoint 2: strict structural recovery where ground truth exists.

Primary endpoint 3: nuisance-term acceptance in spurious-correlation scenarios.

### 10.2 Paired analysis

Use condition-matched comparisons. Binary recovery outcomes use exact McNemar tests. Continuous paired outcomes use percentile or bias-corrected bootstrap confidence intervals. Report effect sizes, not only p-values.

### 10.3 Multiple testing

Define families before analysis:

- primary method comparisons;
- semantic threshold sensitivity;
- ablations;
- scalability factors;
- external datasets.

Use Holm correction within each declared family. Do not pool unrelated exploratory tests into the primary claim family.

### 10.4 Hierarchical structure

Seeds are repeated across benchmark/scenario conditions, so simple row-level independence must not be assumed. The final paper should include a hierarchical robustness analysis, such as a mixed-effects logistic model or cluster bootstrap over seeds and benchmark families.

### 10.5 Missing and failed runs

- retain failed searches as failures;
- never replace a failed seed;
- record timeout, memory failure, parse failure, and unsupported grammar separately;
- perform sensitivity analyses with unsupported conditions excluded and conservatively counted as failures.

## 11. Theory obligations

The archival paper should include formal statements under explicit assumptions.

### Theorem target T1: shortcut rejection

Derive sufficient conditions under which a term that is predictive on only a limited client subset fails the global support and non-degradation certificates.

### Theorem target T2: invariant-term retention

Derive a finite-sample probability bound for accepting a true invariant term as a function of client count, sample size, effect size, noise, and certificate threshold.

### Theorem target T3: exception identifiability

State sufficient conditions under which a restricted exception is distinguishable from an invariant core term and from an unsupported local artifact.

### Proposition P1: communication complexity

Provide communication complexity in terms of clients, candidate terms, certificate dimension, rounds, and coefficient summaries.

### Proposition P2: failure boundary

Characterize observational equivalence, insufficient client support, strongly collinear substitutes, missing catalog terms, and rare exceptions that cannot be reliably identified.

Every theorem must state assumptions clearly and must be followed by a simulation that checks whether the predicted qualitative behavior appears.

## 12. Phase 1 analysis command

Run the post-hoc semantic and failure analysis on the immutable Study A CSV:

```bash
pip install -e ".[dev]"
fedfalsify-transactions-analysis \
  --input results/colab/v06-primary-confirmatory/final/v06_confirmatory.csv \
  --output-dir results/transactions_phase1 \
  --samples 4000 \
  --strict-threshold 0.001 \
  --relaxed-threshold 0.01
```

Expected outputs:

- `results/transactions_phase1/transactions_semantic_rows.csv`;
- `results/transactions_phase1/transactions_summary.json`;
- `results/transactions_phase1/fedfalsify_failure_taxonomy.csv`.

Rerun the analysis at thresholds `1e-4` and `1e-2` for sensitivity reporting. These are analyses of frozen equations, not new search experiments.

## 13. Submission go/no-go criteria

A serious Transactions submission proceeds only if all conditions below are met:

1. Study A remains cryptographically verifiable and unchanged.
2. Semantic evaluation eliminates the main representation-fairness objection.
3. FedFalsify retains a meaningful advantage against official external baselines under at least one equal-budget regime.
4. No single ablation reproduces the full method's performance, or the method is simplified accordingly.
5. At least two external scientific datasets show stable cross-client benefit; three are preferred.
6. Scalability failure regions are measured and honestly reported.
7. At least two formal results or one substantial theorem plus supporting propositions are completed.
8. Privacy wording remains limited unless a formal mechanism is added.
9. Final Transactions confirmation uses untouched seeds and a frozen protocol.
10. All code, configurations, result manifests, and exclusions are archived.

If these criteria are not met, the work should target a strong conference or a narrower journal rather than overclaiming Transactions readiness.

## 14. Permitted final claim style

A defensible final claim would be:

> Across frozen synthetic confirmation, independent Transactions-scale validation, and external heterogeneous datasets, FedFalsify improved structurally or semantically correct symbolic recovery while reducing locally supported nuisance terms. The benefit was linked by ablation to cross-client falsification and support-qualified exception handling, with explicit limitations under catalog misspecification, observational equivalence, and weak client support.

This wording is conditional on completing the protocol above.
