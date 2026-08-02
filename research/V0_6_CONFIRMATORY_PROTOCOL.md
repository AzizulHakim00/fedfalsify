# FedFalsify v0.6 Confirmatory Protocol

## Status and purpose

This protocol is frozen before running the publication-facing comparison. It
separates development evidence from confirmatory evidence and prevents tuning
against confirmatory failures.

Version 0.6 does not change the v0.5 FedFalsify decision thresholds. It adds:

- controlled expression-tree symbolic-regression baselines;
- an optional adapter for the official PySR package;
- matched statistical analysis;
- runtime and communication accounting;
- certificate sensitivity probes; and
- a certificate-noise utility ablation.

The expression-tree baselines are independent project implementations. They are
not author-code reproductions of published federated GP or counterexample-guided
GP systems.

## Primary research question

> Under matched synthetic mechanisms and client partitions, does FedFalsify
> recover the exact invariant-plus-exception structure more often than controlled
> centralized, federated, and residual-counterexample expression-tree searches?

## Hypotheses

### H1: exact structure recovery

FedFalsify will have a higher exact-recovery probability than each controlled
expression-tree baseline under client heterogeneity.

### H2: shortcut rejection

FedFalsify will accept the client-local nuisance variable less often than the
controlled expression-tree baselines in the spurious scenario.

### H3: exception recovery

FedFalsify will recover the declared gated exception more often in the exception
scenario.

### H4: efficiency trade-off

FedFalsify may require fewer candidate evaluations than evolutionary baselines,
but its structured certificates and replacement queries can increase serialized
communication.

No privacy, causality, clinical, or universal symbolic-regression hypothesis is
registered.

## Methods

### Primary method

- `fedfalsify-v05`: v0.4 coefficient-heterogeneity discovery followed by the
  frozen v0.5 client-validated core-surrogate replacement stage.

### Controlled project baselines

- `centralized-tree-gp`: pooled multi-gene expression-tree evolutionary search;
- `federated-tree-gp-style`: the same search structures evaluated through
  aggregate client normal equations and local losses;
- `centralized-residual-counterexample-gp`: pooled expression-tree search with
  high-residual observations reweighted between generations.

These baselines use the same project expression constructors and search budget.
They test broad methodological families but must not be cited as exact
reproductions of Dong et al., Błądek and Krawiec, BFSR, or another author system.

### Optional official baseline

- `official-pysr`: official PySR 1.5.x through `pysr_adapter.py`.

Install with:

```bash
python -m pip install -e ".[sr]"
```

The official PySR baseline is applicable to complementary and spurious
conditions with the shared generic operators. The declared `x3 > 1` gate is not
a generic PySR operator in this protocol. Exception-condition PySR results must
therefore be marked unsupported unless a custom gate operator is frozen before
execution and applied equally to every relevant method.

## Search-space fairness

All controlled tree searches use variables, addition, multiplication, sine,
cosine, square, and the declared gate constructor. The same maximum number of
multi-gene terms is used.

Nevertheless, the comparison has an unavoidable inductive-bias asymmetry:
FedFalsify searches a finite named term catalog, whereas the tree baselines must
search combinations of generated expression trees. The paper must report this
explicitly. A result from this protocol cannot establish universal superiority
over unrestricted symbolic regression.

## Frozen confirmatory seeds

Development seeds used in v0.3--v0.6 smoke or development studies are excluded.

Primary confirmatory seeds:

```text
9001, 9002, ..., 9020
```

These seeds may not be replaced after results are observed. Failed runs remain
in the denominator. A deterministic software crash is repaired and the complete
matrix is rerun; an algorithmic failure is recorded as a failure.

## Primary matrix

### Mechanisms

- `base`
- `poly3`
- `nested_sine`
- `trig_product`
- `interaction`

### Scenarios

- complementary domains;
- single-client spurious shortcut;
- restricted-domain exception.

### Noise ratios

- `0.03`
- `0.10`

Noise is scaled relative to the pooled noiseless target standard deviation.

### Sample size and client count

- 300 observations per client;
- 4 clients.

### Methods

- FedFalsify v0.5;
- centralized tree GP;
- federated tree-GP-style search;
- centralized residual-counterexample GP.

Total primary matrix:

```text
5 mechanisms × 3 scenarios × 2 noise levels × 20 seeds × 4 methods
= 2,400 method-runs
```

## Secondary robustness matrix

Run only after the primary matrix is complete and archived.

- mechanisms: `base`, `poly3`, `interaction`;
- scenarios: all three;
- noise: `0.03`;
- samples/client: `120`, `1000`;
- clients: `4`, `8`, `16`;
- seeds: `9101`--`9110`;
- all four controlled methods.

This matrix examines data scarcity and client scaling. It is secondary and must
not replace the primary endpoint.

## Frozen controlled-search budget

Unless an implementation defect is found before confirmatory execution:

```text
population size: 48
generations: 12
maximum genes: 4
maximum expression complexity: 7
elite fraction: 0.20
complexity weight: 0.015
worst-client weight: 0.35
counterexample fraction: 0.20
counterexample boost: 4.0
```

A separate budget-sensitivity appendix may use larger budgets. It must not be
used to retroactively select the best baseline budget per benchmark.

## Outcomes

### Primary outcome

Exact symbolic recovery:

```text
predicted active term set == ground-truth active term set
```

The intercept is excluded. Coefficients with absolute magnitude below `1e-3`
are inactive.

### Secondary outcomes

- term precision and recall;
- normalized global-test MSE;
- client-local nuisance acceptance;
- gated-exception recovery;
- runtime;
- candidate evaluations;
- serialized communication bytes;
- discovered expression and stop reason.

## Statistical analysis

For every comparator, use matched condition-seed pairs.

- exact recovery: two-sided exact McNemar test;
- exact-recovery rate: Wilson 95% interval;
- NMSE and runtime: paired percentile-bootstrap mean-difference intervals;
- multiple exact-recovery comparisons: Holm step-down correction;
- report discordant counts, not only p-values;
- report all effect estimates even when not statistically significant.

Primary familywise alpha:

```text
0.05
```

No result is called significant from an uncorrected exploratory subgroup test.

## Confirmatory commands

Primary controlled comparison:

```bash
fedfalsify-confirmatory \
  --benchmarks base,poly3,nested_sine,trig_product,interaction \
  --scenarios complementary,spurious,exception \
  --noise 0.03,0.10 \
  --samples 300 \
  --clients 4 \
  --seeds 9001,9002,9003,9004,9005,9006,9007,9008,9009,9010,9011,9012,9013,9014,9015,9016,9017,9018,9019,9020 \
  --population-size 48 \
  --generations 12 \
  --max-genes 4 \
  --bootstrap-resamples 10000 \
  --output results/v06_primary_confirmatory.csv \
  --summary results/v06_primary_confirmatory_summary.json
```

Smoke testing is only a pipeline check:

```bash
fedfalsify-confirmatory --smoke
```

## Exclusion and failure rules

- no algorithmic failure is deleted;
- no benchmark is removed for being difficult;
- non-finite output is a failed run and is separately flagged;
- unsupported official-PySR gate conditions are marked `unsupported`, not
  converted to failures or wins;
- hardware interruption permits rerunning the identical seed and configuration;
- changing a threshold, grammar, or budget after reading confirmatory outcomes
  creates a new version and requires new seeds.

## Interpretation boundary

A positive result supports only the project-specific claim that structured
aggregate certificates are effective on the registered synthetic mechanisms
under the registered finite catalog and heterogeneity conditions.

It does not prove:

- general superiority over PySR or genetic programming;
- novelty of federated symbolic regression or counterexample guidance;
- differential privacy;
- causal discovery;
- clinical validity; or
- discovery of a scientific law.
