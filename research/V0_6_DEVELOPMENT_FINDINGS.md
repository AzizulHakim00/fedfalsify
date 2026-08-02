# FedFalsify v0.6 Broader Development Findings

## Scope

This note records a frozen development comparison used to validate the v0.6
runner before the registered confirmatory study. It is not the confirmatory
matrix because it uses development seeds, one noise level, 120 observations per
client, and moderate controlled-GP budgets.

## Matrix

```text
5 mechanisms
× 3 heterogeneity scenarios
× 3 seeds
× 4 methods
= 180 method-runs
```

Settings:

```text
noise ratio: 0.03
samples/client: 120
clients: 4
seeds: 6001, 6002, 6003
tree population: 24
tree generations: 5
maximum genes: 4
```

The methods were FedFalsify v0.5, controlled centralized tree GP, controlled
federated tree-GP-style search, and controlled residual-counterexample GP.

## Aggregate results

| Method | Exact recovery | 95% Wilson interval | Precision | Recall | Global NMSE | Spurious accepted | Exception recovered | Runtime (s) | Communication (bytes) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| FedFalsify v0.5 | **0.933** | **[0.821, 0.977]** | **0.981** | **0.987** | **0.000010** | **0.000** | **1.000** | **0.213** | 282,689 |
| Controlled centralized tree GP | 0.156 | [0.077, 0.288] | 0.381 | 0.409 | 0.07312 | 0.222 | 0.800 | 0.356 | 0 |
| Controlled federated tree-GP-style | 0.156 | [0.077, 0.288] | 0.381 | 0.409 | 0.07312 | 0.222 | 0.800 | 0.478 | 341,518 |
| Controlled residual-counterexample GP | 0.156 | [0.077, 0.288] | 0.378 | 0.381 | 0.08872 | 0.244 | 0.778 | 0.370 | 0 |

FedFalsify recovered 42 of 45 matched conditions. Each controlled tree baseline
recovered 7 of 45.

## Paired development tests

Against each controlled tree baseline:

```text
FedFalsify-only exact successes: 35
Comparator-only exact successes: 0
discordant pairs: 35
raw exact McNemar p: 5.82e-11
Holm-adjusted p: 1.75e-10
```

These values describe the frozen development matrix. They are not publication-
facing confirmatory p-values because the methods, grammar, software, and budgets
were developed before this run and official PySR was not included.

## Scenario breakdown

### Complementary domains

- FedFalsify exact recovery: 14/15;
- each controlled tree baseline: 3/15.

### Single-client spurious shortcut

- FedFalsify exact recovery: 15/15;
- each controlled tree baseline: 4/15;
- FedFalsify nuisance acceptance: 0/15;
- centralized/federated tree baseline nuisance acceptance: 4/15;
- residual-counterexample baseline nuisance acceptance: 4/15.

### Restricted-domain exception

- FedFalsify exact recovery: 13/15;
- each controlled tree baseline: 0/15;
- FedFalsify exception recovery: 15/15;
- centralized/federated tree baseline exception recovery: 6/15;
- residual-counterexample baseline exception recovery: 5/15.

## FedFalsify failures retained

### Failure 1

```text
benchmark: poly3
scenario: complementary
seed: 6002
reported: sin(x1), x1^2, x1^3
missing: x1
extra surrogate: sin(x1)
```

### Failure 2

```text
benchmark: poly3
scenario: exception
seed: 6002
reported: I(x3>1)*x3^2, sin(x1), x1^2, x1^3
missing: x1
extra surrogate: sin(x1)
```

### Failure 3

```text
benchmark: interaction
scenario: exception
seed: 6003
reported: I(x3>1)*x3^2, x1*x2, x3, x3^2
all true terms recovered
extra surrogate: x3
```

The failures reinforce the remaining limitation: restricted-domain collinearity
can still make a nonlinear or lower-order surrogate survive the conservative
replacement stage.

## Important fairness limitations

The large gap must not be interpreted without these limitations:

1. FedFalsify searches a named finite catalog containing the relevant benchmark
   terms.
2. The controlled tree baselines search generated expression combinations.
3. Five generations and population 24 are moderate development budgets, not a
   definitive GP benchmark budget.
4. The controlled implementations are not official PySR, Dong et al., BFSR, or
   formal counterexample-driven GP implementations.
5. The declared exception gate is directly represented in the project grammar.
6. Only three development seeds and one noise level were used.

Consequently, the correct interpretation is:

> The v0.6 matched runner detects a strong advantage for FedFalsify under the
> current finite-catalog synthetic setting and exposes clear weaknesses of the
> moderate-budget controlled tree searches. The result justifies running the
> registered confirmatory matrix and official package baselines; it does not
> establish universal symbolic-regression superiority.

## Efficiency observation

Within this matrix, FedFalsify used approximately 17.2% fewer estimated
serialized bytes than the controlled federated tree-GP-style baseline and had a
lower mean measured runtime. Centralized methods report zero network bytes by
definition, so they cannot be compared as communication competitors.

These are development observations, not hardware-independent complexity
results.

## Raw evidence

The corrected aggregate summary is archived at:

```text
research/results/V0_6_DEVELOPMENT_SUMMARY.json
```

The GitHub Actions run also archived the raw 180-row CSV and raw/corrected JSON
reports as workflow artifact `v06-development-results` with SHA-256 digest:

```text
19b346620a977ff8167f12ce62977e753f50c4dac2ea0ca8e1ee87b7f5543fd6
```
