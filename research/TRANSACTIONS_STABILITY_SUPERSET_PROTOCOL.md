# Transactions stability-selected candidate-superset protocol

Status: **frozen before implementation outcomes are inspected**

## 1. Scientific motivation

Cross-fit redesign v2 showed that the independent structural probe was safe when
activated, but candidate generation frequently omitted the true cubic term before
probing. The next redesign therefore changes candidate generation, not validation
or probe thresholds.

This is a new development study. It does not retune v2 and does not use spent
seeds `13001--13005` or `14001--14005`.

## 2. Immutable components

The following v2 components remain unchanged:

- disjoint coefficient-fit, certificate, selector, and structural-probe roles;
- validation non-degradation and complexity gates;
- independent probe coefficient freezing;
- 1% rival probe-SSE margin;
- 60% client win and sign-agreement requirements;
- prohibition on score-only structural fallback;
- finite maximum final structure of six terms.

Completed confirmation, PySR, Beijing, SRSD, cross-fit v1, and surrogate v2
artifacts are immutable. Final-confirmation seeds `11001+` remain untouched.

## 3. New candidate-generation mechanism

Development seeds: `15001--15005`.

Each client's discovery portion is divided into five deterministic folds. For
each fold direction, coefficients are fitted on four folds and residual evidence
is computed on the held-out fold.

For every inactive term the server records, without using selector or probe
outcomes:

- number of folds where the term is the best supported repair;
- number of folds where it is among the top three supported repairs;
- median absolute residual correlation across observable client-folds;
- weighted sign agreement;
- coefficient-sign stability across folds;
- client coverage.

The stability-selected candidate superset contains a term only when at least one
frozen rule holds:

1. best repair in at least two of five folds; or
2. top-three repair in at least three folds, with sign agreement at least 0.60
   and observable support at at least half of clients.

At most eight inactive terms may enter the superset. Ties are resolved by fold
selection count, median absolute residual correlation, lower complexity, then
lexicographic term name. Selector or probe outcomes cannot alter the superset.

## 4. Candidate structures

The server constructs a nested path from the stable superset using aggregate
fit-fold coefficient summaries. Candidate structures include:

- the five-fold strict intersection;
- majority structure: terms selected in at least three fold directions;
- stability path prefixes up to the six-term final budget;
- the union of fold-direction structures, clipped by frozen stability ranking.

Every non-intersection structure must pass the unchanged v2 selector and
structural-probe gates. The output is the admissible candidate with the lowest
selector information score. If none passes, the strict intersection is returned.

Score-only search remains a predictive comparator only.

## 5. Frozen development matrix

- benchmarks: `base`, `poly3`, `nested_sine`, `trig_product`, `interaction`;
- scenarios: complementary, spurious, restricted exception;
- noise ratios: `0.03`, `0.10`, `0.20`;
- samples per client: `120`, `300`;
- client counts: `4`;
- seeds: `15001--15005`;
- methods: legacy certificate, v1 governed, v2 structural, stability-superset v3,
  score-only predictive comparator, centralized upper bound, and paired v3
  intersection diagnostic.

All rows and failures are retained.

## 6. Primary endpoints

1. exact structural recovery;
2. high-noise `poly3` and `interaction` exact recovery;
3. test NMSE;
4. spurious acceptance;
5. exception recovery;
6. stable-superset recall of the true term;
7. stable-superset size and nuisance inclusion;
8. selector/probe activation, gains, and harms;
9. runtime and communication.

The key mechanism endpoint is **true-term candidate recall before selection**. A
method cannot claim improved discrimination if it merely increases final error
performance while the true term is absent from the candidate superset.

## 7. Frozen go/no-go gate

V3 advances only if every criterion holds:

- overall exact recovery is at least legacy minus 0.01;
- high-noise `poly3`/`interaction` exact recovery exceeds legacy and v2 by at
  least 0.05;
- true-term candidate recall on high-noise `poly3` is at least 0.85;
- spurious acceptance is no more than 0.01 above legacy;
- exception recovery is at least 0.97;
- continuation causes zero observed exact harms relative to the paired v3
  intersection;
- median stable-superset size is no greater than five inactive terms;
- runtime is below 15x and communication below 30x legacy.

Failure of any criterion is a NO-GO. Thresholds and ranking rules may not be
changed after result inspection.

## 8. Claim boundary

A positive development result would show only that multi-fold stability screening
improved finite-catalog candidate recall and structural discrimination in the
frozen synthetic matrix. It would not establish catalog-free discovery, causal
validity, formal privacy, external superiority, or Transactions readiness.

PR #1 remains draft and unmerged.