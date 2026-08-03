# Transactions official-PySR validation protocol

Status: **frozen before execution**

Scientific role: validation study, not final confirmation.

## Objective

Test whether the advantage observed for finite-catalog FedFalsify persists when
compared with the official Julia-backed PySR implementation under deterministic
functional evaluation rather than exact string or named-term matching.

The study is intentionally restricted to conditions supported by the shared
operator grammar. The restricted indicator-gated exception scenario is not part
of the primary matched comparison because the official PySR grammar used here
does not include that operator.

## Methods

1. `fedfalsify-v05`
   - federated aggregate fitting;
   - certificate-guided finite-catalog discovery;
   - client-validated core replacement;
   - no raw observation pooling.
2. `official-pysr`
   - official PySR 1.5.x package;
   - pooled raw observations;
   - operators: addition, multiplication, sine, cosine and square;
   - deterministic serial execution with a fixed random seed.

The comparison is not a privacy comparison. FedFalsify transmits aggregate
messages, whereas PySR receives pooled data.

## Frozen validation matrix

- benchmarks: `base`, `poly3`, `nested_sine`, `trig_product`, `interaction`;
- scenarios: `complementary`, `spurious`;
- noise ratios: `0.03`, `0.10`;
- samples per client: `300`;
- clients: `4`;
- validation seeds: `10501--10505`;
- semantic evaluation samples: `4,000` per domain.

This gives:

```text
5 benchmarks × 2 scenarios × 2 noise levels × 5 seeds = 100 conditions
```

Each condition is evaluated under two PySR budgets and paired with the same
FedFalsify result, producing 200 matched method pairs and 400 archived rows.

## Frozen PySR budgets

### Compact regime

- iterations: `5`;
- populations: `2`;
- population size: `20`;
- maximum expression size: `18`.

### Quality regime

- iterations: `20`;
- populations: `4`;
- population size: `30`;
- maximum expression size: `18`.

The compact regime is a low-compute sensitivity analysis. It is not labelled
as exactly wall-clock matched. Runtime is measured and reported rather than
assumed equal.

## Primary endpoint

The primary endpoint is paired all-domain semantic recovery at normalized MSE
threshold `1e-3` under the **quality** regime.

A run succeeds only when the reported equation has NMSE at or below `1e-3` on
all four deterministic domains:

1. global interpolation;
2. noiseless pooled client support;
3. mild extrapolation at scale `1.25`;
4. strong extrapolation at scale `1.50`.

Parser errors, unavailable packages, incomplete searches and non-finite
predictions remain failures.

## Secondary endpoints

- compact-regime all-domain semantic recovery at `1e-3`;
- all-domain semantic recovery at `1e-4` and `1e-2`;
- interpolation NMSE;
- client-support NMSE;
- mild- and strong-extrapolation NMSE;
- runtime;
- expression complexity;
- FedFalsify strict named-term recovery, reported descriptively only.

Strict structural recovery is not used as the primary cross-method endpoint
because PySR may return algebraically equivalent equations outside the named
finite catalog.

## Statistical analysis

For each regime:

- exact paired McNemar test for semantic recovery at `1e-3`;
- exact paired McNemar test at `1e-2`;
- paired percentile-bootstrap interval for PySR minus FedFalsify strong-
  extrapolation NMSE;
- paired percentile-bootstrap interval for PySR minus FedFalsify runtime;
- Wilson 95% intervals for method-level semantic success rates.

The two primary-regime-family McNemar values (`compact`, `quality`) receive a
Holm step-down correction. The quality-regime `1e-3` endpoint remains the
predeclared primary interpretation.

Benchmark-stratified rates are descriptive and cannot replace the pooled
primary endpoint.

## Seed governance

- frozen confirmatory seeds `9001--9020` are prohibited;
- development/calibration seeds `10001--10500` are prohibited;
- this validation study uses only `10501--10505`;
- seeds `11001+` remain untouched for independent final confirmation.

No result-dependent seed replacement is allowed. Infrastructure reruns must
reuse the same seed and configuration. A model or equation failure is retained
as a failure.

## Warm-up and runtime

Each parallel worker performs one unmeasured tiny PySR warm-up before the
validation conditions. Reported runtime is taken from the subsequent model-fit
calls. Installation and Julia compilation time are archived separately in CI
logs and are not included in model runtime.

## Claim rules

Permitted after successful completion:

- report paired semantic recovery differences under the two frozen budgets;
- report benchmark-specific strengths and weaknesses;
- state that PySR uses pooled data while FedFalsify keeps observations local;
- state explicitly when PySR is stronger, including the polynomial benchmark.

Not permitted from this study alone:

- universal state-of-the-art superiority;
- superiority on exception grammars;
- privacy guarantees;
- causal discovery claims;
- final Transactions readiness.

## Immutability rule

After the first complete validation artifact is produced, the matrix, seeds,
operator grammar, thresholds and primary endpoint are frozen. Any later method
change requires new development seeds and a separately named validation study;
the original artifact remains archived without selective replacement.
