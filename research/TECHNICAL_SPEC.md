# FedFalsify MVI Technical Specification

## Research question

Can heterogeneous institutions recover a hidden mathematical mechanism without
sharing observation rows, gradients, or neural-network weights, by exchanging
structured falsification certificates?

## Current prototype

The minimum viable invention uses a finite symbolic grammar. The server owns a
candidate equation and clients own private `(X, y)` data. A discovery round has
two stages:

1. **Federated fit:** each client returns an aggregated normal-equation summary
   for the current active terms. The server fits global coefficients.
2. **Federated falsification:** each client evaluates the fitted hypothesis and
   returns a certificate containing local loss, residual behavior, a worst
   failure region, and residual evidence for inactive symbolic terms.

The server adds at most one term per round. The selected repair maximizes a
consensus score combining residual correlation, cross-client sign agreement,
client support, and symbolic complexity.

## Hidden mechanism in experiment 1

```text
y = 2*x1 + sin(x2) + 0.5*x3^2 + Gaussian noise
```

Four clients observe different, overlapping ranges. The success criterion is
recovery of the true active terms and coefficients within a declared tolerance.

## Certificate boundary

The prototype does not transmit raw observation rows. It does transmit
aggregated normal equations and residual statistics. These summaries are not a
formal privacy guarantee. Differential privacy, secure aggregation, membership
inference evaluation, and certificate minimization are reserved for later
research phases.

## Falsifiable claims for version 0.1

- Counterexample-guided repair recovers the known mechanism more reliably than
  unguided/random term addition under the benchmark settings.
- Cross-client consensus rejects terms supported by only one spurious local
  correlation.
- The final mechanism can be audited as a compact symbolic expression.

These claims must be tested over multiple seeds, noise levels, client counts,
and domain partitions before publication.

## Next research milestones

1. Add unguided, local-only, and centralized symbolic discovery baselines.
2. Add spurious-correlation and exception-mechanism benchmarks.
3. Replace quantile failure regions with privacy-budgeted predicates.
4. Add a repair ledger and explicit hypothesis constraints.
5. Extend the finite basis grammar to expression trees.
6. Prove finite-space elimination/retention properties.
7. Integrate a message-based federated runtime after the simulation is stable.
