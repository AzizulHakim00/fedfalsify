# FedFalsify Technical Specification — Version 0.4

## Research question

Can distributed institutions refine an interpretable mathematical hypothesis by
exchanging aggregate falsification certificates, while distinguishing:

1. terms supported across heterogeneous clients;
2. shortcuts supported at only one client; and
3. restricted-domain terms whose effect changes inside a declared validity
   region?

This is a falsifiable research question. It is not a statement of proven
novelty, privacy, causality, or scientific truth.

## Protocol messages

For active terms, every client sends an aggregate normal-equation summary.
For every non-intercept grammar term, it sends aggregate conditional evidence:

- residualized term correlation;
- residual inner product;
- conditional local coefficient adjustment;
- estimated standard error and z-score;
- residualized term energy;
- number of local observations where the term is active; and
- an aggregate high-error region.

Raw `(X, y)` rows are not included. These statistics can still leak information
and are not a formal privacy mechanism.

## Conditional coefficient adjustment

For a candidate model with design matrix `Z` and a term vector `v`, the client
first residualizes the term against the active candidate:

```text
v_perp = v - Z (Z^T Z)^(-1) Z^T v
```

It then estimates the local omitted-term adjustment:

```text
delta = (v_perp^T residual) / (v_perp^T v_perp)
```

The certificate also includes an approximate standard error for `delta`. This
is an established regression operation; the project-specific hypothesis is how
these summaries are used during federated symbolic repair.

## Repair categories

### Core repair

A normal symbolic term is eligible only when:

- at least two clients can evaluate it;
- a declared fraction of observing clients supports it; and
- residual signs are sufficiently consistent.

This rule is intended to reject a local shortcut that is observable everywhere
but predictive at only one institution.

### Restricted-domain exception

Each gated exception declares a source term. For example:

```text
exception:   I(x3 > 1) * x3^2
source term: x3^2
```

The server partitions clients by whether they observe the gate. It compares the
source-term conditional coefficient adjustment inside and outside the gate.
A robust, uncertainty-normalized contrast produces a heterogeneity score.

The gated term is eligible only when:

- existing residual support and sign requirements pass;
- source-term adjustments are estimable on both sides of the gate; and
- the heterogeneity score exceeds the fixed threshold.

A sufficiently strong exception can be prioritized over a globally correlated
surrogate. The search may temporarily add one slack term, while final reporting
uses coefficient magnitude and approximate significance pruning.

## Controlled benchmarks

### Benchmark A — complementary domains

```text
y = 2*x1 + sin(x2) + 0.5*x3^2 + noise
```

### Benchmark B — local spurious correlation

```text
y = 3*x1 + 0.8*x2^2 + noise
```

At client 1 only, a nuisance variable is generated as a noisy outcome proxy.

### Benchmark C — invariant core and exception

```text
y = 2*x1 + sin(x2) + I(x3 > 1)*0.75*x3^2 + noise
```

Clients outside the gate cannot estimate the gated term, but can estimate the
ungated source-term coefficient adjustment.

### Extended v0.3/v0.4 benchmark family

Five finite-grammar mechanisms are evaluated under complementary, spurious, and
exception scenarios. A separate global input domain is used for extrapolation
metrics.

## v0.4 development evidence

A fixed 100-run development comparison used five mechanisms, five seeds, two
sample sizes, and the exception scenario.

- v0.3 ablation exception recovery: 0.600;
- v0.4 exception recovery: 1.000;
- v0.3 exact recovery: 0.580;
- v0.4 exact recovery: 0.940.

These are development results. Three remaining v0.4 core-surrogate failures are
recorded in `V0_4_DEVELOPMENT_FINDINGS.md`.

## Current success criteria

- exact expected term recovery in the finite grammar;
- coefficient error within declared tolerance;
- rejection of a declared one-client shortcut;
- correct core/exception classification;
- low global-domain normalized MSE;
- certificates serialize without raw rows;
- v0.4 improves exception recovery over the disabled-certificate ablation.

## Claims not permitted yet

- "first federated coefficient-heterogeneity method";
- "first federated counterexample method";
- "privacy preserving" without a threat model and formal guarantee;
- "causal mechanism" from observational fit alone;
- "scientific law" from synthetic recovery;
- superiority to symbolic regression generally;
- confirmatory statistical claims based only on development seeds.

## Required next experiments

1. disjoint-seed confirmatory study with confidence intervals;
2. published centralized symbolic-regression baseline;
3. faithful federated GP/SR comparison;
4. counterexample-guided SR comparison outside federation;
5. multiple client counts, noise levels, and sample sizes;
6. certificate leakage attacks and privacy-budgeted variants;
7. replication requirements for one-client exceptions;
8. expression-tree search rather than a hand-enumerated basis;
9. formal false-term rejection and true-term retention analysis;
10. targeted study of the remaining core-surrogate failure cases.
