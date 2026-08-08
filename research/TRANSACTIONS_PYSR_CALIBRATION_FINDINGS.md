# Transactions Official PySR Calibration Findings

## Status

This is a fresh-seed development calibration of the official Julia-backed PySR package. It is not a final baseline comparison and does not support a superiority claim.

- workflow run: `30854002620`;
- artifact ID: `8871793219`;
- artifact digest: `sha256:8114b1f6ac237c830e8a0d127a4f14aa4a525f702daaba79b15bfb349581efb6`;
- source commit: `e5c95ba34f4b389a83454688f797732a402d1304`;
- Python: `3.11.15`;
- official PySR: `1.5.10`;
- Julia: `1.11` workflow environment;
- seed: `10001`;
- samples per client: `300`;
- clients: `4`;
- budget: `20` iterations, `4` populations, population size `30`, max size `18`;
- nominal population updates: `2400` per condition;
- semantic evaluation points: `1000` per domain.

The matrix contains eight supported conditions:

```text
2 benchmarks × 2 scenarios × 2 noise levels × 1 seed = 8 runs
```

The restricted indicator-gated exception grammar was intentionally excluded from this calibration because the shared official PySR operator set does not represent that structure.

## Results

| Benchmark | Scenario | Noise | All-domain semantic 1e-3 | All-domain semantic 1e-2 | Strong extrapolation NMSE | Runtime (s) | Complexity |
|---|---|---:|---:|---:|---:|---:|---:|
| base | complementary | 0.03 | 0 | 0 | 0.211569 | 13.216 | 30 |
| base | complementary | 0.10 | 0 | 0 | 0.056901 | 1.540 | 22 |
| base | spurious | 0.03 | 1 | 1 | 3.00e-09 | 1.463 | 18 |
| base | spurious | 0.10 | 0 | 1 | 0.002975 | 1.450 | 30 |
| poly3 | complementary | 0.03 | 1 | 1 | 1.69e-07 | 1.465 | 13 |
| poly3 | complementary | 0.10 | 1 | 1 | 2.29e-07 | 1.091 | 13 |
| poly3 | spurious | 0.03 | 1 | 1 | 1.16e-06 | 1.208 | 13 |
| poly3 | spurious | 0.10 | 1 | 1 | 2.39e-06 | 1.381 | 13 |

Aggregate calibration outcomes:

- all-domain semantic recovery at `1e-3`: `5/8 = 62.5%`;
- all-domain semantic recovery at `1e-2`: `6/8 = 75.0%`;
- `poly3` semantic recovery at `1e-3`: `4/4 = 100%`;
- `base` semantic recovery at `1e-3`: `1/4 = 25%`;
- post-warm-up median runtime: approximately `1.45 s` per condition;
- first-run runtime: `13.22 s`, dominated by one-time compilation and initialization effects.

## Main scientific finding

Official PySR directly challenges the most important FedFalsify failure region. Under this calibration budget, PySR recovers all four `poly3` conditions semantically, including both high-noise cases. In contrast, the frozen FedFalsify analysis identified high-noise polynomial surrogate ambiguity as its principal failure boundary.

This means a serious Transactions paper cannot rely only on the controlled internal tree-GP baselines. Official PySR must be included across the full supported benchmark matrix, and results must be reported by benchmark family rather than only as an aggregate average.

At the same time, PySR is not uniformly strong. It fails both `base` complementary conditions at the relaxed `1e-2` all-domain threshold and succeeds strongly on the low-noise spurious condition. The calibration therefore supports the broader SRBench observation that no single symbolic-regression system should be assumed to dominate across all problem families.

## Runtime interpretation

The first condition includes a large one-time Julia/PySR warm-up cost. Fair reporting must separate:

1. environment and compilation warm-up;
2. amortized per-condition search runtime;
3. end-to-end runtime for a fresh process;
4. candidate or population-update budget.

The 20-iteration post-warm-up runtime is roughly three times the frozen FedFalsify mean runtime. Therefore the final comparison requires at least two regimes:

### Regime A — equal wall-clock

Calibrate a smaller PySR iteration budget whose post-warm-up median runtime is close to FedFalsify and the controlled competitors. The budget must be fixed before the full matrix is inspected.

### Regime B — higher-quality fixed PySR budget

Use the successful calibration budget:

```text
20 iterations × 4 populations × population size 30
```

This regime asks how a mature official SR system performs with a meaningful but more expensive search.

A third best-effort regime may be included in the supplement only if computationally affordable and preregistered.

## Full comparison requirements

The full supported matrix should use fresh seeds and include:

- all five benchmark families;
- complementary and spurious scenarios;
- noise ratios `0.03` and `0.10`;
- at least five development seeds for calibration and ten or more untouched validation seeds;
- deterministic semantic evaluation on interpolation, client-support, mild extrapolation, and strong extrapolation domains;
- equation complexity;
- search runtime;
- warm-up time reported separately;
- unsupported exception conditions excluded from the ordinary success denominator and reported in a separate grammar-support table.

## Claim boundary

Permitted:

> A small fresh-seed official PySR calibration showed strong polynomial recovery and heterogeneous performance across benchmark families, motivating a full equal-budget comparison.

Not permitted:

- FedFalsify outperforms official PySR;
- official PySR outperforms FedFalsify;
- the eight calibration runs represent a final benchmark;
- nominal population updates are exact candidate-evaluation counts;
- unsupported exception conditions are PySR failures.
