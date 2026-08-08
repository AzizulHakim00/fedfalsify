# FedFalsify Technical Specification — Version 0.5

## Research question

Can distributed institutions refine an interpretable symbolic hypothesis by
exchanging aggregate falsification certificates, while distinguishing:

1. terms supported across heterogeneous clients;
2. shortcuts supported at only one client;
3. restricted-domain terms that other clients cannot observe; and
4. correlated core surrogates that should be replaced after discovery?

This is a falsifiable research question, not a proven novelty, privacy,
causality, or scientific-truth claim.

## Aggregate protocol

For active terms, clients send aggregate normal-equation summaries. For grammar
terms, they send:

- conditional residual evidence;
- local coefficient adjustment;
- standard error and z-score;
- effective residualized term energy;
- observed support and estimability; and
- an aggregate high-error region.

Raw `(X, y)` rows are not included. Repeated aggregate queries may leak
information and require a separate privacy analysis.

## Discovery stages

### Core repair

A normal core term is eligible only when enough observing clients support it and
the evidence signs are sufficiently consistent.

### Restricted-domain exception

A gated term is eligible when its validity region is observed, residual support
is present, and the source-term coefficient exhibits a sufficiently strong
uncertainty-normalized contrast between clients inside and outside the gate.

### Core-surrogate replacement

After v0.4 discovery, v0.5 considers one-for-one and two-for-one structural
swaps. A swap is accepted only when:

- a robust objective combining pooled and worst-client error improves;
- at least a declared fraction of clients improves;
- most clients do not materially worsen;
- the incoming term receives cross-client coefficient support;
- the incoming coefficient remains significant after federated refitting; and
- reported symbolic complexity does not increase.

Accepted swaps are recorded in a replacement ledger.

## Controlled benchmarks

The research pipeline includes five frozen finite-grammar mechanisms under
complementary-domain, single-client-spurious, and restricted-exception
scenarios. The mechanisms are synthetic test functions, not new natural laws.

## Current development evidence

- v0.4 coefficient heterogeneity: exact recovery increased from 58% to 94% in
  the fixed 100-run ablation development matrix; exception recovery increased
  from 60% to 100%.
- v0.5 core replacement: exact recovery increased from 92% to 96% in a fixed
  200-run disjoint-seed development matrix; exception recovery remained 100%.

The v0.5 exact-recovery Wilson intervals overlap. No statistical-superiority
claim is permitted from this development study.

## Claims that are not permitted yet

- first federated symbolic discovery or first replacement method;
- privacy preserving without a threat model and formal guarantee;
- causal mechanism from observational fit alone;
- clinical discovery or scientific law from synthetic benchmarks;
- superiority over published symbolic-regression methods;
- universal solution to correlated-surrogate selection.

## Required confirmatory work

1. published centralized symbolic-regression baselines;
2. faithful federated symbolic-regression comparison;
3. counterexample-guided SR comparison outside federation;
4. new confirmatory seeds, noise levels, client counts, and sample sizes;
5. paired statistics, confidence intervals, and corrected tests;
6. communication and certificate-leakage analysis;
7. privacy-budgeted or secure variants;
8. expression-tree search rather than a finite basis catalog;
9. formal false-term rejection and true-term retention analysis;
10. replication of restricted exceptions across multiple observing clients.
