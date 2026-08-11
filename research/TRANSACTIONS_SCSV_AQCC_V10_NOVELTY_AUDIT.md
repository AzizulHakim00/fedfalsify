# FedFalsify v10 novelty audit

## Candidate successor

**FedFalsify v10: Set-Conditional Structural Verification with Anchor Quarantine and Client Consensus (SCSV-AQCC)**

Status: **paper-first successor hypothesis only**. This document does not authorize fresh evidence.

## Triggering evidence

The sealed v9 sharded-recovery result is permanently `DEVELOPMENT-NO-GO`. Its spent-data postmortem found two separable mechanisms:

1. all 44 null/diffuse-null false-positive deviations were already present in the frozen v6 anchor, so v9's mandatory anchor monotonicity made those false positives irreparable;
2. all 36 missed true deviations occurred at noise ratio 0.30, dominated by selector/probe directional contradiction despite zero role/source/pair/evidence-integrity violations.

V10 therefore targets inherited exception contamination and split-direction instability. It must not retune v9 on spent seeds `26101--26105` or `27101--27105`.

## Prior-art boundary

The following ideas are established prior art and are **not** claimed as v10 novelty.

### Stability through repeated/subsampled selection

Meinshausen and Buehlmann, *Stability Selection*, JRSS-B 72(4), 2010, introduced repeated subsampling around a base selector and false-discovery control. Therefore generic resampling, selection-frequency filtering, or 'stability selection' is not a novelty claim.

### Aggregation across multiple data splits

Meinshausen, Meier and Buehlmann, *P-values for high-dimensional regression*, 2009/2010, explicitly addressed the instability of a single random split and aggregated inference over multiple splits. Therefore generic multi-split evidence aggregation is not a novelty claim.

### Shared structure with group-specific parameters

Fong and Motani, *Multi-Level Symbolic Regression: Function Structure Learning for Multi-Level Data*, AISTATS/PMLR 238, 2024, learns shared symbolic structure while allowing group-specific parameter values. Therefore generic shared/global structure plus group-level deviations or parameters is not a novelty claim.

### Federated shared/local personalization

Personalized federated learning already contains shared-representation/local-component constructions, e.g. Collins et al., *Exploiting Shared Representations for Personalized Federated Learning*. Therefore generic shared/global versus client-local decomposition is not a novelty claim.

## Narrow candidate novelty

The potentially defensible contribution is the **specific structural certificate composition**, not any component alone:

> In federated symbolic structural recovery, exception-like terms already selected by a shared anchor are quarantined rather than inherited irrevocably; each quarantined exception and each newly proposed exception must be re-certified against a source-linked, role-aware fixed full/reduced pair, while high-noise held-out evidence is judged through client-level contradiction persistence after selector/probe sufficient statistics are combined within client.

This claim is intentionally narrower than 'robust symbolic regression', 'stability selection', 'personalized federated learning', or 'multi-level symbolic regression'.

## Mechanistic distinction from v9

V9 protects every anchor term. V10 protects only ordinary shared/core anchor terms. Anchor terms whose catalog metadata marks them as `kind='exception'` are quarantined and must pass the same role-aware certificate as newly proposed deviations.

V9 vetoes a candidate when either held-out view is directionally contradicted. V10 does not aggregate over arbitrary new random splits. It keeps the same frozen selector/probe packets, first combines their full/reduced SSE contribution **within each role client**, and then requires both:

1. pooled complexity-penalized evidence across the fixed held-out packets; and
2. positive median client-level raw improvement.

Thus a single noisy split cannot veto a candidate when the combined held-out evidence for the role clients is directionally persistent, while a candidate supported only by one anomalous client cannot pass the client-median condition when multiple role clients exist.

## Claim restrictions

Even if v10 later passes development, do not claim:

- novelty of stability selection, resampling, repeated splitting, or evidence aggregation;
- novelty of shared/global plus local structure;
- generic false-discovery control from the v10 procedure unless separately proven;
- causal identification;
- formal differential privacy;
- catalog-free symbolic discovery;
- superiority over all symbolic-regression methods.

A future manuscript may claim the narrow certificate only if fresh development and independent validation both pass preregistered gates and a final literature review does not reveal a closer prior method.
