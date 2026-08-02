# FedFalsify Technical Specification — Version 0.2

## Research question

Can distributed institutions refine an interpretable mathematical hypothesis by
exchanging aggregate falsification certificates, while distinguishing:

1. terms supported across heterogeneous clients;
2. shortcuts supported at only one client; and
3. restricted-domain terms that other clients cannot observe?

This is the present falsifiable question. It is not yet a statement of proven
novelty, privacy, causality, or scientific truth.

## Current protocol

For active terms, every client sends an aggregate normal-equation summary. For
inactive terms, it sends:

- residual correlation;
- residual inner product;
- local residual slope;
- term energy;
- number of local observations where the term is active; and
- an aggregate high-error region.

Raw `(X, y)` rows are not included in the protocol message.

## Repair categories

### Core repair

A normal symbolic term is eligible only when:

- at least two clients can evaluate it;
- a declared fraction of observing clients supports it; and
- the signs of the residual relationships are sufficiently consistent.

This rule is intended to reject a local shortcut that is observable everywhere
but predictive at only one institution.

### Restricted-domain exception

A gated term can be provisionally retained when every client observing its
validity region supports it. Clients with zero observations in the region are
not counted as agreement and are not treated as contradictions. The result must
report the term as an exception, not as part of the invariant core.

A one-client exception is weak evidence. It requires replication in future work.

## Controlled benchmarks

### Benchmark A — complementary domains

```text
y = 2*x1 + sin(x2) + 0.5*x3^2 + noise
```

Expected result: recover `x1`, `sin(x2)`, and `x3^2`.

### Benchmark B — local spurious correlation

```text
y = 3*x1 + 0.8*x2^2 + noise
```

At client 1 only, `x3` is generated as a noisy proxy for the outcome. Expected
result: recover `x1` and `x2^2`; reject `x3`.

### Benchmark C — invariant core and exception

```text
y = 2*x1 + sin(x2) + I(x3 > 1)*0.75*x3^2 + noise
```

Clients 1–3 do not observe `x3 > 1`; client 4 does. Expected result:

- invariant core: `2*x1 + sin(x2)`;
- provisional exception: `I(x3 > 1)*0.75*x3^2`.

## Current success criteria

- exact expected term recovery in the finite grammar;
- coefficient error within prespecified tolerances;
- rejection of the declared one-client shortcut;
- correct core/exception classification;
- final mean squared error close to the injected noise variance;
- certificates serialize without raw rows.

## Claims that are not permitted yet

- "first federated counterexample method";
- "first counterexample-guided symbolic regression";
- "privacy preserving" without a formal threat model and guarantee;
- "causal mechanism" from observational fit alone;
- "scientific discovery" based only on a synthetic benchmark;
- superiority without multi-seed comparisons and established baselines.

## Required next experiments

1. centralized symbolic-regression baseline;
2. local-only symbolic-regression baselines;
3. federated GP/SR comparison;
4. scalar-fitness federation without structured certificates;
5. counterexample-guided SR comparison outside the federated setting;
6. multiple seeds, client counts, noise levels, and domain partitions;
7. certificate leakage attacks and privacy-budgeted variants;
8. replication requirements for exceptions;
9. expression-tree search rather than a hand-enumerated basis;
10. formal conditions for false-term rejection and true-term retention.
