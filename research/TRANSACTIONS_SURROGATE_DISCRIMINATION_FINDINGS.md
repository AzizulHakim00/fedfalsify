# Transactions surrogate-discrimination v2 findings

Status: **complete development study; preregistered gate failed**

## Evidence identity

- protocol: `research/TRANSACTIONS_SURROGATE_DISCRIMINATION_PROTOCOL.md`;
- workflow run: `31020422813`;
- final artifact: `surrogate-discrimination-v2-final`;
- artifact ID: `8936544092`;
- artifact digest: `sha256:4763a6825be0a71ae8bd1819e9334519a3dbb274dedcd3c40360d8c424bc98d5`;
- workflow head: `326128a5c9676b42ef3bf5847125ff333a2f996f`;
- rows: 2,700 across 450 matched conditions;
- development seeds: `14001--14005`.

All five benchmark strata completed independently and passed identity, row-count,
finite-value, method, and seed checks before aggregation. Existing confirmation,
external validation, and final-confirmation evidence was untouched.

## Aggregate results

| Method | Exact recovery | Test NMSE | Term precision | Term recall | Spurious accepted | Exception recovered |
|---|---:|---:|---:|---:|---:|---:|
| Centralized forward | **0.9556** | **0.000077** | **0.9901** | **1.0000** | 0.0067 | **1.0000** |
| Cross-fit v1 governed | 0.7222 | 0.003826 | 0.9112 | 0.9239 | 0.0156 | 0.9822 |
| Legacy certificate | **0.7133** | **0.005582** | 0.8911 | 0.8822 | **0.0000** | **1.0000** |
| Cross-fit v2 structural | 0.6800 | 0.010285 | 0.9060 | 0.8739 | **0.0000** | 0.9778 |
| Cross-fit v2 intersection | 0.6289 | 0.020900 | 0.9143 | 0.8319 | **0.0000** | 0.9778 |
| Score-only federated | 0.1244 | 0.000283 | 0.5931 | 0.9893 | 0.2467 | **1.0000** |

V2 structural continuation improved the paired intersection substantially, but the
intersection/directional candidate family remained weaker than legacy overall.
V2 exact recovery was 3.33 percentage points below legacy, violating the frozen
2-point non-inferiority margin. V2 test NMSE was also higher than legacy, although
it was approximately 50.8% lower than the v2 intersection.

## Continuation audit

The independent structural probe activated in 65/450 conditions (`14.44%`).
Relative to the paired v2 intersection:

- exact gains: `23`;
- exact harms: `0`;
- test-NMSE improvements: `65`;
- test-NMSE harms: `0`.

Selected sources:

| Source | Activations |
|---|---:|
| Direction B | 24 |
| Direction A | 22 |
| Cross-fit union | 19 |

Raw score-only search was never allowed to supply a structural output. V2 accepted
no spurious variable in the frozen matrix. These results show that the probe gate
was conservative and safe when an admissible candidate existed.

Benchmark-level activation audit:

| Benchmark | Activations | Exact gains | Exact harms | NMSE improvements |
|---|---:|---:|---:|---:|
| Base | 19 | 8 | 0 | 19 |
| Interaction | 9 | 5 | 0 | 9 |
| Nested sine | 5 | 5 | 0 | 5 |
| Poly3 | 32 | 5 | 0 | 32 |
| Trig product | 0 | 0 | 0 | 0 |

The probe therefore discriminated some omitted truths successfully, but in the
main polynomial failure stratum only 5 of 32 activations restored exact structure.

## Benchmark boundaries

V2 structural minus legacy exact recovery:

| Benchmark | Difference |
|---|---:|
| Base | +0.0222 |
| Nested sine | +0.0444 |
| Trig product | 0.0000 |
| Interaction | -0.0222 |
| Poly3 | **-0.2111** |

On the preregistered high-noise `poly3` + `interaction` subset:

- legacy exact recovery: `0.3333`;
- v1 governed: `0.3667`;
- v2 structural: `0.3333`;
- centralized forward: `0.9833`.

The required v2 gain over both legacy and v1 was at least `0.05`. The observed
gain over legacy was `0.00`; relative to v1 it was `-0.0333`.

## Scientific interpretation

The independent probe gate was not the main bottleneck. It produced no observed
structural harms and rejected score-only shortcuts. The failure occurred earlier:
the intersection and two directional certificate searches often did not place the
true cubic term into any candidate set. Once the true term is absent from all
candidate sets, an outcome-independent probe cannot recover it.

This result separates two problems:

1. **candidate validation** — improved by the probe gate;
2. **candidate generation under correlated high-noise terms** — still unresolved.

The next redesign must not loosen validation/probe thresholds. It must generate a
small, stable candidate superset before structural discrimination. Scientifically
reasonable directions include stability-selected residual screening across more
than two folds, grouped rival sets, and hierarchy-aware inclusion of polynomial
families. Such a redesign requires a new frozen protocol and fresh development
seeds.

## Frozen decision

| Criterion | Result |
|---|---|
| Overall exact no more than 0.02 below legacy | **Fail** |
| High-noise gain over legacy at least 0.05 | **Fail** |
| High-noise gain over v1 at least 0.05 | **Fail** |
| Spurious acceptance controlled | Pass |
| Exception recovery at least 0.97 | Pass |
| No score-only structural source | Pass |
| Zero exact harms on continuation | Pass |
| Runtime below 15x legacy | Pass (`1.98x`) |
| Communication below 30x legacy | Pass (`2.18x`) |

**Decision: NO-GO for external redesign evaluation and NO-GO for final
confirmation.**

Seeds `14001--14005` are spent. Threshold changes, selected reruns, or presentation
of v2 as a successful structural solution are prohibited. Final-confirmation
seeds `11001+` remain untouched.