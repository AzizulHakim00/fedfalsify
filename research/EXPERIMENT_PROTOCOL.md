# FedFalsify v0.3 Preregistered Pilot Protocol

## Status and freeze rule

This document fixes the pilot questions, method budget, outcomes and exclusion
rules before interpreting the pilot results. Changes after result inspection
must be recorded in a dated amendment rather than silently replacing this file.

## Primary scientific question

Can structured aggregate falsification certificates distinguish globally
supported symbolic terms, client-local shortcut terms and restricted-domain
exceptions more reliably than controlled baselines using the same finite grammar
and term budget?

## Research questions

- **RQ1 — Recovery:** Can the methods recover the exact known symbolic structure
  when clients observe complementary domains?
- **RQ2 — Shortcut rejection:** Does a nuisance variable predictive at only one
  client enter the reported invariant mechanism?
- **RQ3 — Exception separation:** Is a gated exception recovered without being
  presented as an invariant core term?
- **RQ4 — Robustness:** How do noise and random seed affect recovery?
- **RQ5 — Cost:** What runtime and approximate message volume are required?

## Primary outcome

Exact structural recovery rate. The intercept is ignored. A term is active when
its absolute fitted coefficient is at least `1e-3`. Exact recovery requires the
active term set to equal the known generating term set.

## Secondary outcomes

1. Term precision and recall.
2. Relative coefficient error over the union of true and predicted terms.
3. Noise-free global-test NMSE on a separately generated domain.
4. Nuisance acceptance rate for `x4` or `x4^2`.
5. Exception recovery for `I(x3>1)*x3^2`.
6. Discovery rounds, wall-clock runtime and approximate serialized bytes.

## Benchmarks

The pilot uses five mechanisms representable by the frozen finite grammar:

1. `2*x1 + sin(x2) + 0.5*x3^2`
2. `x1 + x1^2 + x1^3`
3. `sin(x1) + sin(x1 + x1^2)`
4. `2*sin(x1)*cos(x2)`
5. `x1*x2 + 0.5*x3^2`

These are controlled mechanisms, not claims of new natural laws.

## Scenarios

- **Complementary:** clients observe shifted, overlapping input ranges.
- **Spurious:** `x4` is strongly correlated with the target only at client 1
  and independent elsewhere.
- **Exception:** the target additionally contains
  `0.75*I(x3>1)*x3^2`; clients 1–3 do not observe the validity region and the
  final client does.

## Methods and fairness constraints

All methods use the same finite grammar and maximum active-term budget.

1. **Centralized forward search:** pooled raw data; information-criterion stop.
2. **Local-only forward search:** one independent search per client.
3. **Score-only federation:** greedy proposed-term evaluation using aggregate
   fit summaries and candidate MSE, without term-level certificates.
4. **Random repair:** random terms under the same budget.
5. **FedFalsify:** cross-client structured residual certificates with
   observability and exception metadata.

The centralized method is an information-rich reference, not a privacy-preserving
competitor. The current baselines are finite-basis controls, not substitutes for
future PySR, GP, Bayesian federated SR or published counterexample-guided SR
reproductions.

## Pilot matrix

- Benchmarks: 5
- Scenarios: 3
- Noise ratios: `0`, `0.03`, `0.10` relative to pooled noiseless target SD
- Seeds: `2026`–`2030`
- Clients: 4
- Samples/client: 300
- Maximum terms including intercept: 6
- Methods: 5

Full pilot size: 1,125 method-runs.

## Separate test domain

Every method is evaluated on a newly generated global domain with 4,000 samples.
The test target is noise-free, so NMSE measures structural extrapolation rather
than memorization of training noise.

## Exclusion and failure rules

A run is not silently removed. Numerical failure, non-finite output or timeout
must remain in the result ledger with a failure status. Hyperparameters are not
changed for a particular benchmark after examining its result. Any protocol
change requires a dated amendment and rerunning every method in the affected
matrix.

## Statistical plan for the later full study

The pilot is diagnostic. The confirmatory study will use at least 20 matched
seeds, paired method comparisons, bootstrap confidence intervals for recovery
rates, Wilcoxon signed-rank tests for continuous errors, and Holm correction for
multiple pairwise comparisons.

## Claim boundary

Passing this pilot would support only a controlled finite-grammar statement. It
would not establish privacy, causality, clinical validity, universal symbolic
regression superiority or discovery of a scientific law.
