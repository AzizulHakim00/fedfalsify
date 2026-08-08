# Certificate-Guided Adaptive Tree: Low-Budget Calibration Findings

## Status

This was a fresh-seed development calibration, not a final comparison.

- workflow run: `30856167708`;
- artifact ID: `8872545576`;
- artifact digest: `sha256:845350558bfb7339170c8b7d83a854de115fae19e033b7f6643d87f97b25959d`;
- source commit: `03b25e07b53db7fda17d44c06b4b3626d00a647e`;
- seed: `10011`;
- 12 conditions per method;
- benchmarks: `base`, `poly3`;
- scenarios: complementary, spurious, exception;
- noise ratios: `0.03`, `0.10`;
- budget: population `16`, generations `3`, max genes `3`, max expression complexity `7`.

## Aggregate result

| Method | Exact recovery | Semantic recovery 1e-2 | Term recall | Strong extrapolation NMSE | Spurious accepted | Runtime (s) | Communication bytes |
|---|---:|---:|---:|---:|---:|---:|---:|
| Certificate-guided federated tree | 0% | 0% | **34.72%** | **0.1121** | **0%** | 1.084 | 561,547 |
| Centralized tree GP | 0% | 0% | 15.28% | 3.0801 | 33.33% | 0.300 | 0 |
| Federated tree-GP-style | 0% | 0% | 15.28% | 3.0801 | 33.33% | 0.389 | 300,192 |
| Residual-counterexample GP | 0% | 0% | 15.28% | 6.1631 | 16.67% | 0.317 | 0 |

The certificate-guided method reduced strong-extrapolation error relative to every controlled tree comparator. The paired bootstrap interval for comparator-minus-reference strong-extrapolation NMSE was above zero for all three comparisons. It also rejected every `x4` nuisance structure in this calibration.

However, no method achieved semantic recovery at `1e-2`, and no method achieved strict recovery. Therefore this calibration does not establish a successful adaptive symbolic-discovery method.

## Protocol defect identified

The calibration used `max_genes=3`. Exception conditions contain an invariant core plus a restricted exception, and the strict recognized-term endpoint can require four distinct terms. Although a composite tree can sometimes encode multiple terms in one gene, the strict support metric recognizes at most one canonical term per gene. The exception strict-recovery endpoint was therefore structurally disadvantaged.

This defect does not invalidate the measured prediction and extrapolation values, but it makes strict exception recovery unsuitable as a primary conclusion from this run.

## Search behavior

The certificate-guided method selected compact, support-consistent structures and assigned zero final certificate penalty to every retained gene. Examples included:

- `add(sin(x2),x1)` with `x1` for the base mechanism;
- `square(add(x1,x1))` with `x1^3` for `poly3`;
- no selected `x4` nuisance term.

The structures captured important components but missed terms such as `x3^2` or the gated exception under the reduced budget. This explains improved extrapolation without semantic success.

## Decision

The adaptive direction remains promising but is **NO-GO as a paper contribution** based on this run.

A corrected calibration must use:

- `max_genes=4`;
- population `48`;
- generations `12`;
- the same grammar and budget for all methods;
- a fresh seed;
- strict and semantic metrics reported separately;
- explicit exception-support diagnostics.

No threshold or penalty should be tuned from the frozen Study A seeds.
