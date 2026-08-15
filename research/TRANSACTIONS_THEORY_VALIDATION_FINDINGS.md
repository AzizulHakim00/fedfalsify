# Finite-Sample Certificate Theory Validation Findings

## Status

The analytic retention and shortcut-rejection bounds in
`TRANSACTIONS_FINITE_SAMPLE_THEORY.md` were validated by Monte Carlo simulation
under their stated fixed-design independent-Gaussian assumptions.

- workflow run: `30856547366`;
- artifact ID: `8872677736`;
- artifact digest: `sha256:334a1672d2fec849930a5325ecc18d16b3f9b8ff34ef17d8ab7afc243aa73c1c`;
- source commit: `5a4554cb10e167c50be26a7d0daf647ec789d6f5`;
- simulation cells: `100`;
- trials per cell: `20,000`;
- observable clients: `3, 4, 8, 16, 32`;
- standardized effects: `1.5, 2.0, 2.5, 3.0, 4.0`;
- active shortcut fractions: `0.0, 0.2, 0.4, 0.55`;
- z threshold: `1.96`;
- support threshold: `0.60`.

## Validation result

- invariant-retention lower-bound violations: `0`;
- shortcut-acceptance upper-bound violations: `0`;
- Monte Carlo tolerance used by the automated check: approximately `0.0283`;
- mean empirical invariant retention: `0.5347`;
- mean analytic invariant lower bound: `0.1276`;
- mean empirical shortcut acceptance: `0.3125`;
- mean analytic shortcut upper bound: `0.6581`.

The bounds are valid in the simulated model but intentionally conservative.
Monte Carlo agreement supports the implementation of the formulas; it does not
replace the analytic proofs.

## Retention transition

For standardized effect `4.0`, z threshold `1.96`, support threshold `0.60`,
and active-shortcut fraction `0.20`:

| Observable clients | Empirical invariant retention | Analytic lower bound | Empirical shortcut acceptance | Analytic upper bound |
|---:|---:|---:|---:|---:|
| 3 | 0.942 | 0.000 | 0.141 | 0.591 |
| 4 | 0.919 | 0.000 | 0.015 | 0.496 |
| 8 | 0.996 | 0.513 | 0.000 | 0.246 |
| 16 | 1.000 | 0.884 | 0.000 | 0.061 |
| 32 | 1.000 | 0.999 | 0.000 | 0.0037 |

The lower bound is uninformative for small client counts even when empirical
retention is high. Once the standardized effect is sufficiently above the z
threshold and the number of clients grows, the lower bound becomes sharp.

The shortcut bound also becomes substantially tighter with more clients when
the active-client fraction remains below the required support fraction.

## Weak-effect boundary

For standardized effects near or below the z threshold, empirical retention is
low and the theorem often returns a zero lower bound because the expected
positive-support probability does not exceed `rho=0.60`. This is a correct and
important limitation:

> Increasing the number of clients cannot guarantee retention when per-client
> evidence is too weak to lie on the acceptance side of the support threshold.

A practical system must therefore balance z threshold, client count, effect
size, and support fraction rather than treating more clients as a universal
solution.

## Shortcut locality boundary

Theorem 2 becomes informative only when

```text
q + (1-q) * 2[1-Phi(a)] < rho.
```

At active fraction `q=0.55` and support threshold `rho=0.60`, the gap is small,
so the Hoeffding bound remains conservative. At `q=0.20` or `q=0.40`, the bound
decays much faster with client count.

This mathematically distinguishes two cases:

- a genuinely local shortcut well below the support threshold;
- a broadly shared proxy whose support fraction approaches the threshold.

The latter is intrinsically harder and requires richer domains or additional
assumptions.

## Manuscript consequence

The theory can support a conditional statement of the form:

> Under independent Gaussian validation splits and minimum standardized-effect
> assumptions, same-sign invariant retention and client-local shortcut
> acceptance admit explicit finite-sample bounds controlled by client count,
> evidence threshold, and support fraction.

It cannot support:

- adaptive reuse of the same data without correction;
- globally shared proxy rejection;
- causal identification;
- one-client exception identification without prior gate assumptions;
- formal privacy.

## Required implementation follow-up

The current v0.5/v0.6 experiments do not use a dedicated independent validation
split for every generated candidate. A theory-aligned v0.7 implementation must
add deterministic sample splitting or cross-fitting before these probabilistic
bounds can be claimed for the algorithm itself.
