# Transactions Development Ablation Findings

## Status

This is fresh-seed **development evidence**, not final confirmation.

- workflow run: `30854002562`;
- artifact ID: `8872030104`;
- artifact digest: `sha256:c0e339f9e2a1e306657c1c48c96bd0a3f5fe37de46ed2dfc375c4d522d0b5ff0`;
- artifact source commit: `e5c95ba34f4b389a83454688f797732a402d1304`;
- rows: `1200`;
- seeds: `10001--10005`;
- frozen seed overlap: none;
- conditions: 5 benchmarks × 3 scenarios × 2 noise ratios × 5 seeds;
- variants: 8;
- samples per client: 300;
- clients: 4;
- bootstrap resamples: 4000.

The results may guide design and targeted validation. They must not be used as final Transactions confirmation.

## Aggregate results

| Variant | Exact recovery | Test NMSE | Spurious accepted | Exception recovery | Runtime (s) | Communication bytes |
|---|---:|---:|---:|---:|---:|---:|
| Centralized catalog | **97.33%** | **1.24e-05** | 0.00% | 100.00% | **0.0145** | 0 |
| **FedFalsify full** | **94.67%** | 1.57e-04 | **0.00%** | **100.00%** | 0.2374 | 315,872 |
| No non-degradation gate | 94.67% | 1.57e-04 | 0.00% | 100.00% | 0.2373 | 315,872 |
| No coefficient heterogeneity | 86.67% | 5.69e-03 | 0.00% | 86.67% | 2.7339 | 5,326,196 |
| No replacement | 86.00% | 1.02e-03 | 0.00% | 100.00% | 0.1413 | 127,042 |
| No exception module | 63.33% | 1.04e-01 | 0.00% | 66.67% | 0.2147 | 292,435 |
| Local consensus | 53.33% | 9.90e-02 | 0.00% | 66.67% | 0.0246 | 2,154 |
| Score-only federated | 24.00% | 4.88e-05 | 28.67% | 100.00% | 1.1243 | 2,243,957 |

## Paired comparisons against full FedFalsify

| Comparator | Full-only exact successes | Comparator-only | Holm-adjusted McNemar p | Paired NMSE difference, comparator − full, 95% bootstrap CI |
|---|---:|---:|---:|---:|
| Centralized catalog | 4 | 8 | 0.7754 | −1.44e-04 [−2.82e-04, −3.01e-05] |
| No non-degradation | 0 | 0 | 1.0000 | 0.0 [0.0, 0.0] |
| No heterogeneity | 20 | 8 | 0.1071 | 5.53e-03 [2.51e-03, 8.87e-03] |
| No replacement | 13 | 0 | 9.77e-04 | 8.68e-04 [4.40e-04, 1.35e-03] |
| No exception module | 47 | 0 | 7.11e-14 | 1.03e-01 [6.68e-02, 1.43e-01] |
| Local consensus | 62 | 0 | 2.60e-18 | 9.88e-02 [6.50e-02, 1.35e-01] |
| Score-only federated | 106 | 0 | 1.73e-31 | −1.08e-04 [−2.45e-04, 4.40e-06] |

## Finding A — privileged centralized catalog is a strong upper bound

The centralized catalog model obtains 97.33% exact recovery versus 94.67% for FedFalsify. The binary exact-recovery difference is not statistically significant in this development matrix, but centralized catalog fitting has lower NMSE and much lower runtime.

This is expected to be a difficult comparator because it pools raw rows and receives the same privileged finite catalog. It exposes an important claim boundary:

> FedFalsify should not be framed as improving accuracy over an unconstrained pooled-data oracle-like catalog method.

The defensible contribution is data-local symbolic discovery with shortcut rejection and supported exceptions, while approaching the privileged pooled upper bound. Real-data studies must quantify the performance price of data locality rather than hiding it.

## Finding B — predictive fit alone is insufficient

The score-only federated model obtains extremely low mean NMSE (`4.88e-05`), slightly below full FedFalsify, yet exact recovery is only 24% and spurious-term acceptance is 28.67%.

By scenario:

- complementary exact recovery: 28%, spurious acceptance: 36%;
- spurious exact recovery: 24%, spurious acceptance: 22%;
- exception exact recovery: 20%, spurious acceptance: 28%.

This is direct development evidence for the paper's core motivation: predictive accuracy can coexist with structurally incorrect and nuisance-contaminated equations. Cross-client falsification is necessary for structural reliability in the controlled setting.

## Finding C — client-validated replacement is essential

Removing replacement lowers exact recovery from 94.67% to 86.00%, with 13 full-only successes and no no-replacement-only successes. The Holm-adjusted McNemar value is `9.77e-04`, and paired NMSE worsens.

The effect is concentrated in difficult settings:

- high-noise `poly3`: full 46.67% versus no replacement 0%;
- high-noise base: full 100% versus no replacement 66.67%;
- high-noise interaction: full 100% versus no replacement 93.33%.

Replacement therefore has a defensible mechanistic role: correcting correlated or surrogate structures that remain after the discovery stage.

## Finding D — exception handling is indispensable

Removing the exception module reduces aggregate exact recovery to 63.33%. All 50 exception-scenario conditions fail strict recovery, exception recovery falls to zero within those conditions, and mean exception-scenario NMSE rises to approximately `0.3105`.

The full method records 47 exact successes that the no-exception model does not, with no reverse successes. This is the largest clean component effect after the score-only comparison.

The local-consensus method also fails all exception conditions, showing that simple majority support cannot recover a deliberately restricted effect.

## Finding E — coefficient heterogeneity is scenario-specific

The complete no-heterogeneity ablation removes coefficient evidence from both discovery and replacement.

Results reveal a trade-off:

- complementary exact recovery: 100%;
- spurious exact recovery: 100%;
- exception exact recovery: 60%;
- exception recovery overall: 86.67%;
- communication grows to approximately 5.33 MB per run;
- runtime grows to 2.73 seconds per run.

The aggregate exact-recovery McNemar result is not significant after Holm correction (`p=0.107`), but NMSE is significantly worse and exception performance degrades sharply. Coefficient heterogeneity therefore should be claimed as an exception-disambiguation and efficiency mechanism, not as a universal accuracy booster.

A targeted validation study must vary exception coefficient contrast, gate prevalence, and number of observing clients.

## Finding F — current non-degradation gate is empirically inactive

The no-nondegradation variant is identical to the full method on every recorded outcome:

- zero discordant exact-recovery pairs;
- zero NMSE difference;
- identical communication;
- effectively identical runtime.

This means the current benchmark never presents a candidate replacement that passes all other checks while violating the non-degradation gate.

The paper must not claim an empirical benefit from this component based on the current matrix. There are two scientifically acceptable paths:

1. design a preregistered adversarial replacement stress test where client harm is possible and test whether the gate activates; or
2. remove the gate from the headline contribution and retain it as a conservative safety rule.

Leaving it as a claimed essential component would be unsupported.

## Benchmark-level failure structure

Full FedFalsify remains perfect in all development benchmark/noise combinations except high-noise `poly3`, where exact recovery is 46.67%. The centralized catalog model achieves 100% on both `poly3` noise levels. This confirms that the high-noise polynomial surrogate failure is caused by the federated certificate/search pathway rather than by catalog incompleteness.

The next development target must therefore distinguish polynomial terms from trigonometric surrogates without using the frozen Study A seeds. Candidate approaches must be tested as explicit new variants, not silently inserted into v0.5.

## Required next experiments

1. Targeted exception heterogeneity matrix varying coefficient contrast and gate prevalence.
2. Adversarial replacement matrix to determine whether the non-degradation gate is useful.
3. Polynomial-surrogate discrimination variants on seeds `10006+`.
4. Validation of the best unchanged/simplified design on seeds `10501--10520`.
5. Official PySR and a second maintained SR method on the same supported conditions.
6. Independent final confirmation on untouched seeds beginning at `11001`.

## Claim boundary

Permitted from this development ablation:

> Replacement, falsification, and restricted-exception handling have measurable and distinct roles, while the current non-degradation gate is inactive and the pooled catalog model remains a strong upper bound.

Not permitted:

- every FedFalsify component is necessary;
- FedFalsify beats pooled centralized catalog fitting;
- development ablations are final confirmation;
- coefficient heterogeneity universally improves exact recovery;
- low prediction error implies correct symbolic discovery.
