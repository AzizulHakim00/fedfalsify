# FedFalsify v0.4 Development Findings

## Scope

This note records the first fixed 100-run development comparison between the
v0.3 ablation and the v0.4 coefficient-heterogeneity certificate. It is not a
confirmatory paper result.

## Aggregate results

| Method | Exact recovery | Term precision | Term recall | Global NMSE | Exception recovery |
|---|---:|---:|---:|---:|---:|
| v0.3 without heterogeneity certificate | 0.580 | 0.942 | 0.878 | 0.03249 | 0.600 |
| v0.4 coefficient-heterogeneity certificate | **0.940** | **0.984** | **0.985** | **0.00021** | **1.000** |

The matrix contains 100 runs:

```text
5 mechanisms × 2 sample sizes × 5 seeds × 2 methods
```

Both methods used the same grammar, maximum reported term budget, data,
noise level, and seeds.

## Strongest result

The v0.4 method recovered the restricted exception in all 50 evaluated v0.4
runs. The ablation recovered it in 30 of 50 runs.

On the low-sample `base` surrogate-trap smoke subset:

- v0.3 exception recovery: 0/3;
- v0.4 exception recovery: 3/3;
- v0.4 exact recovery: 3/3.

## Remaining failures

v0.4 was not perfect. Three of 50 v0.4 runs did not exactly recover the full
mechanism:

1. `base`, seed 2030, 120 samples/client:
   the exception was recovered, but `x3` and `cos(x3)` substituted for the
   ungated `x3^2` component.
2. `poly3`, seed 2028, 120 samples/client:
   the exception was recovered, but the linear `x1` term was missed.
3. `poly3`, seed 2029, 300 samples/client:
   the exception was recovered, but trigonometric surrogates entered and
   `x1^2` was missed.

These failures are retained because they expose a separate weakness:
finite-basis greedy core discovery can still select correlated surrogates even
when exception identification succeeds.

## Interpretation

The development evidence supports a narrow claim:

> Conditional cross-client coefficient-shift evidence materially improves
> restricted-exception identification within the current finite-grammar
> FedFalsify prototype.

It does not establish that the method is superior to published symbolic
regression systems, nor that the certificate is private or causal.

## Next confirmatory study

Use disjoint seeds and include:

- 20 or more matched seeds;
- noise ratios 0, 0.03, and 0.10;
- sample sizes 100, 300, and 1000;
- centralized PySR/GP;
- a faithful federated symbolic-regression baseline;
- a non-federated counterexample-guided SR baseline;
- bootstrap confidence intervals;
- paired tests with multiple-comparison correction;
- certificate leakage analysis.

The three retained failure cases should become a separate core-surrogate
replacement study rather than being silently tuned away.
