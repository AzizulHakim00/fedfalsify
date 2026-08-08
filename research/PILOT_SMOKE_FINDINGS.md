# Pilot Smoke Findings — Diagnostic, Not Confirmatory

## Purpose

This note records the first local diagnostic run after freezing the v0.3 pilot
pipeline. It is intentionally retained even though the proposed method is not
the best method in every setting. These values must not be copied into a paper
as confirmatory results.

## Diagnostic matrix

- Five controlled mechanisms
- Three scenarios: complementary, spurious and exception
- One seed: 2026
- Noise ratio: 0.03 of pooled noiseless target standard deviation
- 150 samples per client
- Five methods
- Total: 75 method-runs

## Mean diagnostic results

| Method | Exact recovery | Term precision | Term recall | Global-test NMSE | Nuisance accepted |
|---|---:|---:|---:|---:|---:|
| Centralized forward | 1.000 | 1.000 | 1.000 | approximately 0.0000 | 0.000 |
| Local-only forward | 0.483 | 0.817 | 0.746 | approximately 0.2604 | 0.067 |
| Score-only federation | 0.333 | 0.738 | 1.000 | approximately 0.0000 | 0.133 |
| Random repair | 0.000 | 0.160 | 0.283 | approximately 0.9051 | 1.000 |
| FedFalsify | 0.400 | 0.758 | 0.900 | approximately 0.0011 | 0.067 |

## Interpretation

1. The centralized finite-basis reference is currently strongest. This is
   expected because it sees pooled rows and uses the same frozen grammar.
2. FedFalsify is substantially better than random repair and has higher exact
   recovery than score-only federation in this small diagnostic.
3. FedFalsify has lower nuisance acceptance than score-only federation, which
   is consistent with the cross-client support hypothesis.
4. Local-only methods are unstable under shifted client domains and extrapolate
   poorly to the separately generated global test domain.
5. The current FedFalsify exception path can select correlated surrogate terms
   instead of the correct gated mechanism at low sample size. This failure is
   not hidden or excluded.

## Required next algorithmic test

The next method revision should target **conditional exception
identifiability**, not add unrelated features. A promising direction is a new
certificate that reports cross-client coefficient heterogeneity for active
terms and tests whether a domain gate explains that heterogeneity. This must be
implemented as a preregistered ablation and compared against the unchanged v0.3
method.

## Claim boundary

These figures are a one-seed engineering diagnostic. The frozen 1,125-run pilot
and later 20-seed confirmatory study are still required. No superiority,
privacy, causal, clinical or scientific-law claim follows from this note.
