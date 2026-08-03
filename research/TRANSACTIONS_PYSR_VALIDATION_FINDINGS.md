# Transactions official-PySR validation findings

Status: **validation complete; not final confirmation**

This document reports the frozen validation study preregistered in
`TRANSACTIONS_PYSR_VALIDATION_PROTOCOL.md`. The matrix, seeds, operator grammar,
budgets and primary endpoint were fixed before the complete artifact was
examined.

## Evidence identity

- workflow run: `30858917065`;
- artifact: `transactions-pysr-validation-v2-final`;
- artifact ID: `8873692394`;
- artifact digest:
  `sha256:def0e4aba3534d38d67318d8250e967331fa4d1c989a5bc24115f128ee6a0399`;
- archived source commit: `d660b57a37f522ec979ff0f6fca3bf8d440f8a50`;
- rows: `400`;
- matched method pairs: `200`;
- validation seeds: `10501--10505`;
- final confirmation seeds `11001+`: untouched.

The environment was Python `3.11.15`, Julia `1.11.9`, PySR `1.5.10` and
SymbolicRegression.jl `1.11.3`.

## Frozen comparison

The study covered:

```text
5 benchmarks × 2 scenarios × 2 noise levels × 5 validation seeds
= 100 scientific conditions
```

Each condition was evaluated in compact and quality PySR regimes. FedFalsify
was paired with the same condition in both regimes, producing 200 matched pairs.

The primary endpoint was all-domain semantic recovery at normalized MSE
`1e-3` under the quality regime. A success required the equation to pass all
four deterministic domains: interpolation, noiseless client support, mild
extrapolation and strong extrapolation.

PySR pooled raw observations. FedFalsify used aggregate federated messages and
did not pool observation rows. This is an algorithmic/data-locality comparison,
not a privacy proof.

## Primary quality-regime result

| Method | All-domain semantic recovery @ `1e-3` | Wilson 95% interval | Recovery @ `1e-2` | Strong-extrapolation NMSE | Runtime | Complexity |
|---|---:|---:|---:|---:|---:|---:|
| **FedFalsify v0.5** | **0.92** | [0.8500, 0.9589] | **0.96** | **0.001151** | **0.187 s** | **6.08** |
| Official PySR | 0.71 | [0.6146, 0.7899] | 0.74 | 0.099246 | 1.754 s | 15.54 |

Paired semantic outcomes at `1e-3`:

- FedFalsify-only successes: `29`;
- PySR-only successes: `8`;
- discordant pairs: `37`;
- exact McNemar value: `0.0007528971`;
- Holm-adjusted value: `0.0007528971`.

The primary validation endpoint therefore supports a statistically significant
advantage for FedFalsify in this controlled, grammar-supported matrix.

This result does **not** imply universal symbolic-regression superiority. The
finite catalog contains the benchmark components, while PySR searches an
adaptive expression space. The benchmark-stratified results expose this scope
clearly.

## Extrapolation and runtime

The paired estimate for

```text
PySR strong-extrapolation NMSE - FedFalsify strong-extrapolation NMSE
```

was `0.098095`, with percentile-bootstrap 95% interval
`[0.032704, 0.208499]`. Lower NMSE is better, so the interval favors
FedFalsify on the frozen all-domain evaluation.

The paired runtime difference

```text
PySR runtime - FedFalsify runtime
```

was `1.5671` seconds, with bootstrap interval `[1.4474, 1.6872]` seconds.
PySR installation and one-time Julia compilation were excluded from model-fit
runtime by an unmeasured warm-up. The measured runtime comparison therefore
concerns post-warm-up model search only.

Communication is not directly comparable: PySR pooled raw data and reports zero
federated communication, whereas FedFalsify explicitly records aggregate
messages.

## Benchmark-specific result

Quality-regime all-domain semantic recovery at `1e-3`:

| Benchmark | FedFalsify | Official PySR | Scientific interpretation |
|---|---:|---:|---|
| `base` | **1.00** | 0.55 | FedFalsify reliably retained the mixed linear, sine and quadratic mechanism. |
| `nested_sine` | **0.95** | 0.45 | The finite named catalog was substantially more reliable at the frozen budget. |
| `trig_product` | **1.00** | 0.95 | Both methods were strong; the difference was small. |
| `interaction` | **1.00** | 0.60 | PySR often retained extra nonlinear dependence, hurting all-domain recovery. |
| `poly3` | 0.65 | **1.00** | PySR completely solved the principal FedFalsify failure family. |

The `poly3` result is a decisive counterexample to any universal superiority
claim. It confirms the earlier diagnosis that finite-catalog FedFalsify suffers
from high-noise correlated polynomial-surrogate ambiguity. Official PySR's
adaptive algebraic search recovered the polynomial family in all 20 quality
conditions.

The correct scientific conclusion is therefore complementary:

- FedFalsify is stronger across most controlled heterogeneous families under
  the frozen budget and deterministic all-domain criterion;
- official PySR is stronger on the polynomial family that constitutes
  FedFalsify's main failure boundary;
- an unrestricted/adaptive search component remains necessary for a broader
  Transactions contribution.

## Scenario and noise behavior

Quality-regime semantic successes at `1e-3`:

| Scenario | Noise | FedFalsify | PySR | Conditions |
|---|---:|---:|---:|---:|
| Complementary | 0.03 | 25 | 19 | 25 |
| Complementary | 0.10 | 21 | 19 | 25 |
| Spurious | 0.03 | 25 | 15 | 25 |
| Spurious | 0.10 | 21 | 18 | 25 |

The largest method separation occurred in the low-noise spurious scenario,
consistent with FedFalsify's cross-client shortcut-rejection design. Both
methods lost performance at higher noise, but the direction of the pooled
primary endpoint remained unchanged.

## Compact-budget sensitivity

| Method | Semantic recovery @ `1e-3` | Recovery @ `1e-2` | Completed rows |
|---|---:|---:|---:|
| FedFalsify | **0.92** | **0.96** | 100/100 |
| Official PySR | 0.22 | 0.27 | 96/100 |

Compact-regime paired outcomes at `1e-3`:

- FedFalsify-only successes: `76`;
- PySR-only successes: `6`;
- Holm-adjusted exact McNemar value: `3.14e-16`.

The compact regime is a low-compute sensitivity analysis, not an exactly
wall-clock-matched claim. Its main role is to show the strong dependence of
adaptive expression search on sufficient search budget.

## Retained incomplete PySR rows

Four compact-regime PySR rows produced equations that the deterministic
semantic parser could not evaluate because they contained fourth powers of
nontrivial subexpressions. These rows were retained as failures, as required by
the preregistration:

1. seed `10501`, `interaction`, complementary, noise `0.03`;
2. seed `10502`, `interaction`, complementary, noise `0.10`;
3. seed `10502`, `interaction`, spurious, noise `0.10`;
4. seed `10505`, `interaction`, complementary, noise `0.10`.

No quality-regime PySR row was incomplete. Continuous summaries excluded
non-finite values and reported finite-pair counts, while all binary semantic
endpoints retained these rows as zero successes.

The parser limitation is also a study limitation: the exported equations were
not manually simplified or selectively repaired after observing outcomes.
Extending the parser is legitimate future infrastructure work, but it requires
a separately named analysis and cannot replace the frozen primary artifact.

## Claim boundary after this study

Permitted:

> On 100 fresh grammar-supported validation conditions, finite-catalog
> FedFalsify achieved 92% deterministic all-domain semantic recovery versus 71%
> for official PySR under the frozen quality budget, while keeping observation
> rows local. Official PySR nevertheless achieved 100% recovery on the
> polynomial family where FedFalsify was weakest.

Not permitted:

- universal state-of-the-art superiority;
- superiority on indicator-gated exception grammars;
- claims that PySR is an inferior symbolic-regression system generally;
- formal privacy guarantees;
- causal discovery claims;
- final Transactions readiness.

## Research decision

This study closes the mandatory official-PySR baseline gate and materially
strengthens the paper. It also sharpens the remaining novelty requirement:
FedFalsify must address catalog misspecification or integrate a successful
adaptive search mechanism without losing its client-level falsification
properties.

The Q1 Transactions decision remains **NO-GO** until at least the following are
complete:

1. a second maintained external symbolic-regression implementation;
2. external scientific datasets with natural client partitions;
3. theory-aligned sample splitting or cross-fitting;
4. scalability across client count, overlap, imbalance and feature dimension;
5. hierarchical benchmark/seed inference;
6. independent final confirmation using untouched seeds `11001+`.
