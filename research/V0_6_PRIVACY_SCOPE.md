# FedFalsify v0.6 Privacy and Leakage Scope

## Current status

FedFalsify does not transmit raw observation rows, but that fact alone does not
establish privacy. The current protocol releases aggregate normal equations,
losses, residual summaries, term correlations, local coefficient adjustments,
standard errors, support counts, failure-region summaries, and repeated
replacement-query responses.

These releases can reveal information about client distributions or individual
records. Version 0.6 therefore makes no differential-privacy, cryptographic, or
membership-protection claim.

## Leave-one-out certificate sensitivity

`leave_one_out_sensitivity` creates the certificate for a fixed client and
candidate, removes one sampled record, recomputes the certificate, and measures
the L2 change in a deterministic numeric certificate vector.

Reported quantities:

- median leave-one-out L2 change;
- mean leave-one-out L2 change;
- maximum leave-one-out L2 change;
- number of sampled records.

This is a sensitivity and leakage proxy. It is not:

- a membership-inference attack;
- a reconstruction attack;
- a privacy accountant;
- a proof of bounded global sensitivity; or
- an epsilon/delta guarantee.

## Certificate-noise utility ablation

`NoisyCertificateClient` clips and perturbs falsification-certificate fields
with deterministic-seed Gaussian noise for reproducible experiments.

The noise multiplier is an experimental scale parameter. It is not epsilon.

Critical limitation:

> The wrapper currently leaves aggregate fit summaries unperturbed.

Consequently, a successful noisy-certificate run cannot be described as a
private federated run. It only shows whether the discovery decisions tolerate
noise in the certificate channel.

## Registered utility matrix

Before introducing a formal DP mechanism, run the following development matrix:

```text
mechanisms: base, poly3, interaction
scenarios: complementary, spurious, exception
samples/client: 120, 300
noise ratio: 0.03
certificate multipliers: 0, 0.10, 0.25, 0.50, 1.0
seeds: 7001--7010
```

Report:

- exact recovery;
- NMSE;
- shortcut acceptance;
- exception recovery;
- runtime;
- communication;
- leave-one-out sensitivity summaries.

Do not choose a preferred multiplier from this matrix and label it a privacy
budget.

## Requirements for a future formal DP version

A defensible DP extension must define:

1. the neighboring-dataset relation;
2. per-query clipping bounds;
3. sensitivity of each released statistic;
4. noise mechanism;
5. number and adaptivity of queries;
6. composition accountant;
7. final epsilon and delta;
8. whether client participation itself is protected;
9. treatment of fit summaries and replacement queries; and
10. utility under the same confirmatory matrix.

Repeated adaptive certificate and replacement queries are especially important:
even individually noisy releases can accumulate a large privacy loss.

## Safe language

Permitted:

> FedFalsify exchanges aggregate messages rather than raw observation rows, and
> we quantify leave-one-out certificate sensitivity and utility under controlled
> certificate perturbation.

Not permitted:

> FedFalsify is privacy preserving.

> The Gaussian multiplier provides differential privacy.

> Raw-data non-sharing guarantees patient confidentiality.
