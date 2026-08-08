# FedFalsify v0.4 Development Protocol

## Status

This is an **exploratory algorithm-development protocol**, not a preregistered
confirmatory experiment. The coefficient-heterogeneity mechanism was tuned on a
small three-seed `base` exception smoke benchmark. The larger 100-run matrix
below was then run without benchmark-specific retuning.

## Failure motivating v0.4

Version 0.3 could identify a restricted exception in high-support settings, but
at low sample sizes it sometimes selected globally correlated surrogates such as
`x3`, `sin(x3)`, or `cos(x3)` instead of the intended gated term
`I(x3>1)*x3^2`.

Residual correlation alone cannot distinguish these cases reliably because all
surrogate functions can correlate with the omitted gated effect inside the one
client that observes the exceptional domain.

## v0.4 hypothesis

For an exception term with a declared source term, clients release a local
**conditional coefficient adjustment** after residualizing the source term
against the current candidate equation.

For the current gated exception,

```text
exception term: I(x3 > 1) * x3^2
source term:    x3^2
```

the server compares source-term adjustments between:

- clients that observe the gate; and
- clients that do not observe the gate.

A large, uncertainty-normalized contrast supports a domain-specific exception
more directly than an undifferentiated global surrogate.

## Certificate contents

For each non-intercept grammar term, a client returns only aggregate values:

- local conditional coefficient adjustment;
- estimated standard error;
- z-score;
- residualized term energy;
- observed support;
- estimability flag.

These values are not raw rows, but they are also not a formal privacy guarantee.

## Repair rule

A gated exception is eligible only when:

1. its residual evidence passes the existing support and sign checks;
2. its source-term coefficient contrast is estimable inside and outside the gate;
3. the heterogeneity score exceeds the fixed threshold.

A sufficiently strong exception decision may be prioritized over a correlated
core-term surrogate. The final model uses coefficient significance pruning.
Search is allowed one temporary slack term so a surrogate can become
statistically negligible after the correct mechanism enters.

## Development matrix

- Benchmarks: `base`, `poly3`, `nested_sine`, `trig_product`, `interaction`
- Scenario: restricted-domain exception
- Methods:
  - `fedfalsify-no-heterogeneity` (v0.3 ablation)
  - `fedfalsify` (v0.4)
- Seeds: 2026, 2027, 2028, 2029, 2030
- Samples/client: 120 and 300
- Noise ratio: 0.03 of pooled noiseless target standard deviation
- Maximum reported terms: 6
- Runs: 5 × 1 × 2 × 5 × 2 = 100

## Primary outcome

Exception recovery rate for `I(x3>1)*x3^2`.

## Secondary outcomes

- exact symbolic recovery;
- term precision and recall;
- global-domain normalized MSE;
- coefficient error;
- nuisance-feature acceptance;
- communication estimate;
- runtime.

## Integrity rules

- No failed run is deleted.
- The development seeds must not be reused as the sole confirmatory evidence.
- v0.4 results cannot be described as proof of novelty, privacy, causality, or
  scientific truth.
- A confirmatory study must use new seeds, additional noise levels, published
  symbolic-regression baselines, and confidence intervals.
