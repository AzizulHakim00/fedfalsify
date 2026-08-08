# FedFalsify v0.5 Core-Surrogate Replacement Development Protocol

## Motivation

Version 0.4 recovered restricted-domain exceptions reliably but retained several
failures in which correlated core basis functions substituted for the injected
core mechanism. Version 0.5 tests a post-search structural replacement stage.

This is a development study, not a confirmatory paper experiment.

## Algorithmic hypothesis

A correlated active surrogate should be replaceable by an inactive core term
when a federated one-for-one or two-for-one swap satisfies all of the following:

1. improves a prespecified robust objective combining pooled and worst-client
   error;
2. improves at least half of participating clients;
3. does not materially worsen at least three quarters of clients;
4. receives statistically non-negligible coefficient support across clients;
5. remains significant after federated refitting; and
6. does not increase reported symbolic complexity.

Clients send aggregate normal-equation summaries and falsification certificates.
No raw observation row is transmitted. Repeated aggregate queries may leak
information and therefore do not constitute a privacy guarantee.

## Methods

- `fedfalsify-v04`: coefficient-heterogeneity exception discovery without the
  post-search core replacement stage.
- `fedfalsify-v05-core-replacement`: the same v0.4 candidate followed by the
  federated replacement and revalidation stage.

## Fixed matrix

- Mechanisms: all five frozen finite-grammar mechanisms.
- Scenario: restricted-domain exception.
- Samples/client: 120 and 300.
- Noise ratio: 0.03 relative to pooled noiseless target standard deviation.
- Clients: 4.
- Seeds: 3031--3040, disjoint from the v0.4 development seeds.
- Methods: 2.
- Total: 200 method-runs, 100 per method.

## Primary outcome

Exact structural recovery, ignoring the intercept and using the existing
absolute coefficient threshold of `1e-3`.

## Secondary outcomes

- term precision and recall;
- global-domain NMSE;
- exception recovery;
- accepted replacement count;
- replacement ledger;
- runtime and serialized communication volume in the CSV ledger.

## Freeze rule

The matrix was executed without benchmark-specific threshold changes. Results
are retained even when v0.5 fails. Any algorithm change after reading these
results must receive a new version number and new seeds.

## Claim boundary

This study can support only a controlled finite-grammar statement about the
post-search stage. It cannot establish superiority over published symbolic
regression, privacy, causality, clinical validity, or discovery of a scientific
law.
