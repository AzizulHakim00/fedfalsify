# FedFalsify v0.5 Development Findings

## Scope

This note records the fixed disjoint-seed comparison defined in
`V0_5_DEVELOPMENT_PROTOCOL.md`. The matrix contains 200 method-runs and was
executed in GitHub Actions without per-benchmark retuning.

## Aggregate results

| Method | Exact recovery | 95% Wilson interval | Term precision | Term recall | Global NMSE | Exception recovery |
|---|---:|---:|---:|---:|---:|---:|
| v0.4 | 0.920 | [0.850, 0.959] | 0.982 | 0.985 | 0.00022 | 1.000 |
| v0.5 core replacement | **0.960** | **[0.902, 0.984]** | **0.994** | **0.993** | **0.00014** | **1.000** |

The exact-recovery increase is four percentage points. The confidence intervals
overlap, so this development matrix alone does not justify a strong statistical
superiority claim. Both methods used the same generated dataset in every
setting; a later confirmatory analysis must therefore use paired outcomes rather
than treating the recovery proportions as independent.

## Interpretation

Version 0.5 improved exact recovery from 92/100 to 96/100 runs while preserving
100% restricted-exception recovery. The improvement is consistent with the
intended role of the post-search stage: correcting or removing a small number of
correlated core surrogates after exception discovery has completed.

The average accepted replacement count was low (`0.03` per v0.5 run). This is
expected for a conservative repair stage: most v0.4 candidates were already
correct, and replacement should be rare rather than compulsory.

## Retained v0.5 failures

Four of 100 v0.5 runs were not exact:

1. `base`, seed 3035, 300 samples/client:
   `x2` remained as an extra surrogate beside the correct terms.
2. `poly3`, seed 3033, 120 samples/client:
   the linear `x1` term was missing.
3. `poly3`, seed 3036, 120 samples/client:
   `sin(x1)` and `cos(x1)` remained as surrogates and `x1^2` was missing.
4. `poly3`, seed 3037, 120 samples/client:
   the linear `x1` term was missing.

These failures are retained. They show that one- and two-term swap proposals do
not solve every low-sample identifiability problem, especially when the true
polynomial components are strongly collinear over restricted client domains.

## Costs and limitations

The v0.5 stage evaluates multiple structural swaps. It therefore increases
aggregate-query volume and computation compared with v0.4. The CSV ledger stores
runtime and serialized message estimates, but a dedicated communication and
privacy-leakage analysis is still required.

The current method also assumes a finite catalog containing the true term. It is
not yet expression-tree symbolic regression.

## Permitted development statement

> In a fixed 200-run finite-grammar development matrix with disjoint seeds, the
> federated core-replacement stage increased exact recovery from 92% to 96%
> while retaining 100% exception recovery.

## Statements not supported

- statistically significant superiority over v0.4;
- superiority over PySR, genetic programming, federated symbolic regression, or
  counterexample-guided symbolic regression;
- privacy preservation;
- causal or scientific-law discovery;
- universal resolution of correlated-surrogate failures.

## Next confirmatory study

Use new seeds and include:

- at least 20 matched seeds across noise and sample-size conditions;
- centralized PySR or another established expression-tree SR implementation;
- a faithful federated symbolic-regression baseline;
- a non-federated counterexample-guided SR baseline;
- paired exact-recovery testing such as McNemar's exact test;
- bootstrap confidence intervals for continuous paired differences;
- multiple-comparison correction;
- runtime, communication, and certificate-leakage analysis.

No v0.5 threshold should be changed using the four failures above before the
confirmatory comparison is frozen.
