# Transactions cross-fitted redesign findings

Status: **complete development study; preregistered scientific gate failed**

## Evidence identity

- frozen protocol: `research/TRANSACTIONS_CROSSFIT_REDESIGN_PROTOCOL.md`;
- workflow run: `30892814499`;
- final artifact: `crossfit-redesign-v1-parallel-final`;
- artifact ID: `8885931902`;
- artifact digest: `sha256:fd824e995f7d10aaeaa83788ca3af86b463c167d55cd01ea0c67028c75f7fc83`;
- branch head used by the workflow: `17a4b8c02bff8517dd5b2bb6a2872d3e5530571c`;
- rows: `2,250` across `450` matched conditions;
- row CSV digest: `c947aec8317fe84d55ccebd6db760f95255bd0d983529c2e3a5a7e1ceb26ac95`;
- summary digest: `314640ff171cad85814f2863f3d0d16e7d846e5f2ceceabf6a19c38c7d27619e`.

Five preregistered benchmark strata were executed on independent clean GitHub
runners and aggregated only after each stratum passed row-count, identity,
finite-value, seed, and method checks. Existing confirmatory, Beijing, and SRSD
artifacts were not modified. Final-confirmation seeds were not used.

## Frozen matrix

- benchmarks: `base`, `poly3`, `nested_sine`, `trig_product`, `interaction`;
- scenarios: complementary, spurious, and restricted exception;
- noise ratios: `0.03`, `0.10`, and `0.20`;
- samples per client: `120` and `300`;
- clients: `4`;
- development seeds: `13001--13005`;
- methods: legacy certificate, cross-fit intersection, cross-fit governed,
  score-only federated, and centralized forward search.

The cross-fit method used disjoint local fit/certificate folds in both directions
plus a held-out validation partition. The governed method could replace the
intersection only through the preregistered validation, worst-client,
non-degradation, complexity, and cross-client term-support gates.

## Aggregate results

| Method | Exact recovery | Test NMSE | Term precision | Term recall | Spurious accepted | Exception recovered |
|---|---:|---:|---:|---:|---:|---:|
| Centralized forward | **0.8956** | **0.000120** | **0.9694** | **0.9987** | 0.0000 | **1.0000** |
| Cross-fit governed | 0.7267 | 0.003379 | 0.9074 | 0.9198 | 0.0067 | 0.9933 |
| Legacy certificate | 0.7156 | 0.005438 | 0.8920 | 0.8857 | **0.0000** | **1.0000** |
| Cross-fit intersection | 0.6311 | 0.026040 | 0.9139 | 0.8300 | **0.0000** | 0.9733 |
| Score-only federated | 0.1244 | 0.000288 | 0.5982 | 0.9956 | 0.3533 | **1.0000** |

The governed redesign reduced mean test NMSE by `37.86%` relative to legacy and
increased exact recovery by `1.11` percentage points. The exact-recovery gain was
not statistically compelling in an exploratory paired analysis: 15 governed-only
successes versus 10 legacy-only successes, exact two-sided McNemar `p = 0.4244`.
A condition-level bootstrap interval for the exact difference was
`[-0.0111, 0.0333]`.

The paired mean NMSE difference, governed minus legacy, was `-0.002059`; its
condition-level bootstrap 95% interval was `[-0.003582, -0.000623]`. This supports
a predictive-error improvement within this development matrix, not a final
confirmatory claim.

Spurious acceptance increased from `0/450` to `3/450`. The absolute difference
was `0.00667`, within the frozen `+0.01` development tolerance, but it is a real
failure count and is not rounded away.

The redesign was substantially more expensive: mean runtime was approximately
`10.8x` legacy and aggregate communication was approximately `21.8x` legacy.
These are matched software-development measurements, not production-system
benchmarks.

## Governed continuation audit

Fallback activated in `116/450` conditions (`25.78%`). Relative to the plain
cross-fit intersection:

- exact recovery improved in `43` conditions;
- exact recovery was harmed in `0` conditions;
- test NMSE improved in all `116` activated conditions;
- test NMSE was harmed in `0` activated conditions.

| Selected continuation source | Activations | Exact gains over intersection |
|---|---:|---:|
| Direction B | 36 | 21 |
| Cross-fit union | 28 | 8 |
| Direction A | 26 | 14 |
| Score-only candidate | 26 | 0 |

This separates two scientifically different effects. Directional/union
continuation repaired unstable sample-split omissions and produced all 43 exact
structural gains. The score-only candidate produced predictive improvements but
`0/26` exact recoveries and introduced all three governed spurious selections.
Therefore score-only search is not an acceptable structural fallback in its
current form, even though it is a useful predictive candidate.

Fallback activation was `19.33%` on complementary scenarios, `19.33%` on
spurious scenarios, and `38.67%` on exception scenarios. The preregistered
fallback-selectivity safeguard therefore passed; fallback did not activate more
often merely because a local shortcut existed.

## Benchmark boundaries

| Benchmark | Legacy exact | Governed exact | Difference |
|---|---:|---:|---:|
| `base` | 0.4889 | 0.4778 | -0.0111 |
| `interaction` | 0.8333 | **0.8889** | +0.0556 |
| `nested_sine` | 0.9333 | **0.9889** | +0.0556 |
| `poly3` | **0.3222** | 0.2778 | -0.0444 |
| `trig_product` | 1.0000 | 1.0000 | 0.0000 |

The redesign improved interaction and nested-sine recovery, preserved perfect
trigonometric-product recovery, but did not solve the known polynomial-surrogate
failure. At noise ratio `0.20` across the preregistered `poly3` and `interaction`
subset, both legacy and governed exact recovery were `0.35`. The required gain
was `+0.05`; the observed gain was exactly `0.00`.

High-noise `poly3` failures continued to replace or approximate the cubic term
with correlated finite-catalog surrogates such as `sin(x1)` and `cos(x1)`.
Validation-aware continuation can identify a lower-error candidate, but ordinary
validation error does not reliably distinguish structural truth from a predictive
surrogate when both agree over the observed domain.

## Preregistered development decision

| Criterion | Result |
|---|---|
| Overall exact recovery no more than 0.02 below legacy | Pass |
| Mean test NMSE below legacy | Pass |
| Spurious acceptance no more than 0.01 above legacy | Pass |
| High-noise `poly3`/`interaction` exact gain at least 0.05 | **Fail** |
| Fallback not disproportionately activated on spurious scenarios | Pass |

**Overall decision: NO-GO for independent final confirmation of this redesign.**

Seeds `13001--13005` are now spent development seeds and may not be used to tune
another version. Untouched final-confirmation seeds `11001+` remain untouched.
The result does not invalidate sample splitting: it shows that sample separation
plus error-based governed continuation is insufficient for the polynomial
identifiability boundary.

## Scientific implications for a future redesign

A future protocol must be frozen on fresh development seeds before execution.
The evidence supports the following design constraints, not post-hoc parameter
changes:

1. keep disjoint fit/certificate partitions, because this aligns the implementation
   with the theorem's data-separation assumption;
2. retain directional/union continuation, which generated structural gains without
   observed exact harms in this matrix;
3. prohibit raw score-only fallback from being labeled a discovered structure;
   at most it may be retained as a predictive comparator;
4. add an explicit structural-surrogate discrimination test using domains or
   perturbations selected independently of validation error;
5. require stability of marginal term contribution across cross-fit directions,
   extrapolation probes, and client domains before replacing polynomial terms;
6. reduce the roughly `10.8x` runtime and `21.8x` communication increases before
   Transactions readiness.

No manuscript claim should state that the cross-fitted redesign solved the
external failure boundary. Its defensible result is narrower: it improved
predictive error and repaired some split-instability failures, while the central
high-noise polynomial identifiability problem remained unresolved.
