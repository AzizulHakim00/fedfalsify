# Transactions stability-superset v3 forensic analysis

Status: **POST-HOC DIAGNOSTIC ANALYSIS OF FROZEN NO-GO EVIDENCE**

Primary decision: **NO-GO**

Primary evidence workflow: `31037754111`

Recovery workflow: `31251266048` (evidence recovery only; not an independent replication)

Recovery artifact: `9020382424`

Artifact digest: `sha256:4eaa72761c9ede08ae9d0e8cf671006f6bca41120d2f305b6d953968c17bfcc6`

Recovery row digest: `sha256:9c8f401d2e52fe7230e4f90650b5f858530edba890f07b302420c51e44ca27f4`

Evidence seeds: `15101--15105` (spent)

This document is a forensic decomposition performed **after** the frozen v3 gate was evaluated. It is diagnostic, not confirmatory. It may motivate a new preregistered v4 study, but none of the analyses below can retroactively change the v3 decision or be used to retune v3.

## 1. Evidence integrity and provenance

The recovered artifact contains exactly 3,150 rows from 450 matched conditions and seven methods. Every method has 450 rows. The only evidence seeds are `15101--15105`; engineering smoke seed `15001` is absent. The artifact contains `rows.csv`, `summary.json`, `decision.json`, `manifest.json`, `RECOVERY_NOTE.md`, and `COMPLETE`.

The recovery commit `c4ce15b25e7e32f65af48e3dac076805a8df811d` differs from the primary trigger commit `f1f3e782a59f8b5c5f9cde99ef683879726802b5` only in `.github/workflows/stability_superset_v3_evidence.yml`. No algorithm, benchmark, report, or test source changed. The recovery manifest explicitly marks the execution as `evidence-recovery` and states that it is not additional statistical evidence.

The recovery artifact upload succeeded. Its later Git push failed only because the branch advanced while the 29-minute recovery matrix was running, causing a non-fast-forward rejection. This does not affect the sealed artifact or scientific decision.

## 2. Overall method results

| Method | Exact recovery | Term precision | Term recall | Test NMSE | Spurious accepted | Exception metric* |
|---|---:|---:|---:|---:|---:|---:|
| Centralized forward | **0.9444** | **0.9809** | **0.9967** | **0.000106** | 0.0333 | 1.0000 |
| Legacy certificate | **0.7133** | 0.8743 | 0.8706 | 0.004578 | **0.0000** | **1.0000** |
| Cross-fit v1 governed | 0.7089 | 0.8960 | 0.9067 | 0.002680 | 0.0222 | 0.9889 |
| Cross-fit v2 structural | 0.6489 | 0.8903 | 0.8544 | 0.016926 | **0.0000** | 0.9533 |
| **Stability-superset v3** | **0.5244** | 0.9170 | 0.7756 | 0.048532 | **0.0000** | 0.8444 |
| V3 strict intersection | 0.5000 | 0.9119 | 0.7083 | 0.099754 | **0.0000** | 0.8444 |
| Score-only federated | 0.1156 | 0.5858 | 0.9867 | 0.000286 | 0.3044 | 1.0000 |

`*` The summary exception metric counts correct absence on non-exception scenarios as success. The conditional exception-scenario recovery rate is analyzed separately below.

V3 recovered the exact structure in 236/450 conditions, compared with 321/450 for legacy and 292/450 for v2. Mean v3 test NMSE was approximately **10.6x** legacy. Therefore the failure is not merely a strict-expression scoring artifact; the frozen v3 output also had substantially worse predictive error on average.

## 3. Benchmark localization

| Benchmark | Legacy exact | V2 exact | V3 exact | V3 intersection | Centralized |
|---|---:|---:|---:|---:|---:|
| base | 0.533 | 0.433 | **0.156** | 0.144 | 0.900 |
| interaction | 0.844 | 0.767 | **0.533** | 0.456 | 0.956 |
| nested_sine | 0.956 | 0.956 | **0.900** | 0.867 | 0.967 |
| poly3 | 0.233 | 0.089 | **0.033** | 0.033 | 0.967 |
| trig_product | 1.000 | 1.000 | **1.000** | 1.000 | 0.933 |

The v3 failure is highly structured rather than universal. `trig_product` is solved perfectly and `nested_sine` remains strong. The dominant failures are `poly3`, `base`, and restricted exceptions, with a substantial drop on `interaction`.

### Noise and sample-size localization

| Noise ratio | Legacy exact | V2 exact | V3 exact |
|---|---:|---:|---:|
| 0.03 | 0.940 | 0.807 | **0.660** |
| 0.10 | 0.693 | 0.653 | **0.513** |
| 0.20 | 0.507 | 0.487 | **0.400** |

| Samples/client | Legacy exact | V2 exact | V3 exact |
|---|---:|---:|---:|
| 120 | 0.716 | 0.622 | **0.484** |
| 300 | 0.711 | 0.676 | **0.564** |

More samples help v3, but do not remove the structural deficit.

## 4. High-noise gate failure

For the preregistered high-noise subset (`noise_ratio = 0.20`, benchmarks `poly3` and `interaction`):

| Method | Exact recovery |
|---|---:|
| Legacy | **0.3333** |
| V2 structural | 0.2833 |
| **V3 stability-superset** | **0.1500** |
| V3 intersection | 0.0500 |
| Centralized | 0.9500 |

By benchmark, v3 exact recovery is `0/30` on high-noise `poly3` and `9/30` on high-noise `interaction`. The critical `x1^3` candidate-recall gate passed, but this did not make the **complete polynomial mechanism** recoverable.

This distinction is central: the v3 gate measured recall of one critical cubic term, while exact `poly3` also requires `x1` and `x1^2`. The forensic analysis shows that `x1^2` is the dominant missing component.

## 5. Candidate-generation mechanism audit

Across all 450 v3 conditions:

- mean target-term recall inside the stable superset: **0.7331**;
- conditions where the stable superset contains the complete truth: **204/450 = 0.4533**;
- median stable-superset size: **3**;
- mean nuisance terms in the stable superset: **1.0533**;
- high-noise `poly3` critical `x1^3` recall: **1.0000**.

Thus, a compact superset was achieved, but complete-mechanism coverage was too low.

### Target-term recall by stage

| True term | Target conditions | Stable-superset recall | Strict-intersection recall | Final-v3 recall |
|---|---:|---:|---:|---:|
| `I(x3>1)*x3^2` | 150 | **0.353** | 0.533 | 0.533 |
| `sin(x1)` | 90 | 1.000 | 0.867 | 0.989 |
| `sin(x1)*cos(x2)` | 90 | 1.000 | 1.000 | 1.000 |
| `sin(x1+x1^2)` | 90 | 0.556 | 0.989 | 0.989 |
| `sin(x2)` | 90 | **0.089** | 0.389 | 0.389 |
| `x1` | 180 | 1.000 | 0.844 | 0.944 |
| `x1*x2` | 90 | 0.822 | 1.000 | 1.000 |
| `x1^2` | 90 | **0.000** | 0.078 | 0.078 |
| `x1^3` | 90 | 1.000 | 0.189 | 0.467 |
| `x3^2` | 180 | 0.628 | 0.456 | 0.628 |

The strongest mechanistic finding is that `x1^2` was **never** admitted to the v3 stable superset, despite being a true term in all 90 `poly3` conditions. This alone prevents stable-superset completeness on every `poly3` condition.

For `x1^2`, the mean fold-selection count was about **2.6/5**, sign agreement about **0.797**, and client coverage **1.0**, yet its best-repair and top-three counts were both zero under the v3 admission statistic. This reveals a mismatch between **path persistence** and **inactive residual-rank evidence**: a term can repeatedly appear in fold-level discovered structures while the v3 superset rule still assigns it no admission path.

`sin(x2)` shows a similar, though weaker, pathology: it is often present in fold-level structures but enters the stable superset only 8.9% of the time.

## 6. Mutually interpretable failure decomposition

V3 has 214 exact-recovery failures. Using the frozen row-level evidence, the final failures decompose as follows:

| Failure class | Count | Fraction of v3 failures |
|---|---:|---:|
| Stable superset missing truth and final output still missing truth | **189** | **88.3%** |
| Stable superset complete, but downstream output loses a true term | 3 | 1.4% |
| Final output contains all truth but also nuisance term(s) | 22 | 10.3% |
| **Total exact failures** | **214** | **100%** |

In addition, 48 exact successes occurred even though the stable superset itself did not contain all truth, because the frozen strict-intersection path is allowed to retain terms outside the stable superset. This confirms that v3 is a hybrid candidate system; stable-superset completeness is mechanistically informative but not identical to final exact recovery.

The dominant failure class is therefore **upstream evidence admission / candidate completeness**, not destructive continuation.

## 7. Continuation audit

V3 continuation activated in **71/450** conditions. Relative to the paired v3 strict intersection:

- exact gains: **11**;
- exact harms: **0**;
- NMSE improvements: **67**;
- NMSE harms: **4**.

Matched exact outcomes show 11 v3-only exact successes and zero intersection-only exact successes. Therefore the continuation mechanism is directionally useful and empirically safe for exact recovery on these spent conditions. The main problem is that too many required terms never become eligible for a useful continuation.

This is consistent with the frozen zero-harm gate passing.

## 8. Restricted-exception failure

On the 150 actual `exception` conditions, conditional recovery of `I(x3>1)*x3^2` is:

| Method | Exception-term recovery |
|---|---:|
| Legacy | **1.0000** |
| Cross-fit v1 | 0.9667 |
| Cross-fit v2 | 0.8600 |
| **V3** | **0.5333** |
| V3 intersection | 0.5333 |
| Centralized | 1.0000 |

The v3 stable superset contains the exception term in only **53/150 = 35.3%** of exception conditions.

The reason is structurally visible in the diagnostics. The gated exception is intentionally observable on only one of the four clients, so its measured client coverage is typically **0.25**. V3's second stable-admission rule requires client coverage at least `0.50`, making that path unavailable to a scientifically legitimate restricted exception. The exception can enter only through the alternative `best repair in >=2 folds` rule.

This is not evidence that the numeric `0.50` threshold should simply be lowered. It shows that **global client coverage is the wrong denominator for a role-restricted term**. A future method should measure repeatability among eligible/observable gated clients and retain an independent gate-vs-outside heterogeneity certificate.

## 9. Nuisance competition

Twenty-two failures contain every true term but still fail exact recovery because extra terms remain. Across all v3 failures, the most frequent extra terms are:

- `sin(x1)`: 56 occurrences;
- `cos(x3)`: 20;
- `x1`: 8;
- `x2`: 5;
- `cos(x1)`: 2;
- `x3`: 2.

The preregistered spurious variables `x4`/`x4^2` were controlled perfectly by v3, so this is not generic spurious-feature collapse. It is **within-grammar surrogate/nuisance competition**. A future redesign should therefore include a conservative term-removal audit after forward structural admission.

## 10. Matched descriptive comparisons

These are post-hoc descriptive checks, not preregistered confirmatory tests.

- V3 vs legacy: `1` v3-only exact success, `86` legacy-only exact successes, `363` ties; exact-rate difference `-0.1889`.
- V3 vs v2: `0` v3-only exact successes, `56` v2-only exact successes, `394` ties; difference `-0.1244`.
- V3 vs paired intersection: `11` v3-only exact successes, `0` intersection-only exact successes, `439` ties; difference `+0.0244`.

The first two comparisons reject the interpretation that v3 merely missed its gate by sampling noise. The third supports preserving the independent continuation/probe concept while redesigning candidate admission.

## 11. Scientific diagnosis

The retained evidence supports four distinct conclusions.

**A. Candidate recall must be mechanism-complete, not single-term-only.** Passing the `x1^3` recall gate did not solve `poly3` because `x1^2` was systematically excluded.

**B. Residual-rank stability and discovery-path stability are not equivalent.** Some true terms repeatedly occur in fold-level structures without satisfying v3's best/top-three inactive-score rule.

**C. Core and restricted-exception terms require different observability semantics.** Global client coverage is appropriate for invariant core evidence but can be structurally incompatible with a valid gated exception.

**D. Forward-only structural admission is insufficient.** A smaller secondary class of failures comes from nuisance terms that survive in an otherwise truth-complete final structure.

These conclusions motivate an architectural redesign. They do **not** justify changing v3 thresholds after inspection.

## 12. Required v4 design principles

Any v4 development study should be frozen on fresh seeds and should implement the following mechanism-level changes rather than retuning v3:

1. **Dual evidence channels:** combine residual-rank stability with fold-level path-selection persistence.
2. **Role-conditioned observability:** core terms use cross-client breadth; restricted exceptions use repeatability among eligible gated clients plus the existing gate-vs-outside coefficient contrast.
3. **Termwise continuation:** independently validate/probe each proposed added term instead of relying mainly on whole-structure strict intersection.
4. **Bidirectional audit:** after forward admission, test whether each retained non-intercept term is actually needed; delete nuisance terms only under an independent non-degradation rule.
5. **Full-mechanism candidate endpoints:** report complete-target coverage in addition to critical-term recall.
6. **Fresh development seeds only:** no v3 seed may be treated as fresh evidence.

## 13. Claim boundary

Permitted:

> In the frozen v3 matrix, stability screening recovered the critical cubic term but failed to preserve complete mechanisms, especially the quadratic polynomial component and restricted exception. Independent continuation was safe when activated, suggesting that the next redesign should focus on role-conditioned, termwise evidence admission rather than looser validation thresholds.

Not permitted:

- claiming v3 superiority;
- lowering v3 thresholds and rerunning the spent matrix as if fresh;
- treating recovery run `31251266048` as an independent replication;
- claiming a new v4 mechanism is novel before a dedicated prior-art search;
- using final-confirmation seeds `11001+` before a future frozen development gate passes.
