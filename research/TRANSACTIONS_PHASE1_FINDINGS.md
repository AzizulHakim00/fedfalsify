# Transactions Phase 1 Findings

## Status

Phase 1 is a post-hoc semantic-equivalence and failure analysis of the immutable Study A evidence. It does not rerun or retune the original search.

- Frozen input: `results/colab/v06-primary-confirmatory/final/v06_confirmatory.csv`
- Frozen rows: `2400`
- Frozen input SHA-256: `163620ab26c938aedd3fa44096c7145780d6ff9aa143ca8b863ea077ba9d3c45`
- Evaluation samples per semantic domain: `4000`
- Primary all-domain semantic threshold: NMSE `<= 1e-3`
- Relaxed sensitivity threshold: NMSE `<= 1e-2`
- Analysis workflow run: `30853146563`
- Archived artifact ID: `8871396938`
- Artifact digest: `sha256:cf2de872e2e2c92a0de49fcffc5e771dede35262ba6d8cd6ae76ae60116f6cbe`

The archived equations were evaluated on four deterministic domains:

1. global interpolation;
2. pooled client-support points with noiseless target values;
3. mild extrapolation at domain scale `1.25`;
4. strong extrapolation at domain scale `1.50`.

All `2400` equations parsed successfully after explicitly supporting both ASCII `I(x3>1)` and Unicode `𝟙[x₃>1]` exception notation.

## Main semantic results

| Method | Strict recovery | All-domain semantic recovery, 1e-3 | All-domain semantic recovery, 1e-2 | Interpolation semantic recovery, 1e-3 | Mean interpolation NMSE | Mean strong-extrapolation NMSE | Mean expression complexity |
|---|---:|---:|---:|---:|---:|---:|---:|
| **FedFalsify v0.5** | **93.33%** | **94.17%** | **96.50%** | **96.50%** | **0.000169** | **0.000952** | **26.63** |
| Centralized tree GP | 23.83% | 47.67% | 55.67% | 55.83% | 0.037415 | 0.479682 | 37.88 |
| Federated tree-GP-style | 23.83% | 47.67% | 55.67% | 55.83% | 0.037415 | 0.479682 | 37.88 |
| Residual-counterexample GP | 22.50% | 43.33% | 54.17% | 51.83% | 0.040276 | 0.952214 | 36.97 |

### Threshold sensitivity

| Method | All-domain recovery, 1e-4 | All-domain recovery, 1e-3 | All-domain recovery, 1e-2 |
|---|---:|---:|---:|
| **FedFalsify v0.5** | **90.83%** | **94.17%** | **96.50%** |
| Centralized tree GP | 43.17% | 47.67% | 55.67% |
| Federated tree-GP-style | 43.17% | 47.67% | 55.67% |
| Residual-counterexample GP | 39.17% | 43.33% | 54.17% |

## Interpretation

The original strict-recovery advantage is not explained away by representation bias. Semantic evaluation materially improves the controlled tree baselines because several syntactically different expressions approximate the target function. Nevertheless, FedFalsify retains a large all-domain semantic advantage at every declared threshold.

At the primary `1e-3` threshold:

- FedFalsify succeeds semantically in `565/600` conditions;
- centralized and federated tree GP each succeed in `286/600` conditions;
- residual-counterexample GP succeeds in `260/600` conditions.

FedFalsify also has lower mean expression complexity than the controlled tree methods. The average reduction is approximately 30% relative to centralized/federated tree GP and 28% relative to residual-counterexample GP.

This evidence supports a narrower and stronger claim:

> Under the frozen synthetic protocol, FedFalsify's advantage persists when equations are evaluated by deterministic interpolation and extrapolation behavior rather than only by canonical term identity.

It does not establish universal mechanistic identifiability or superiority over official external symbolic-regression systems.

## Strict-failure taxonomy

FedFalsify has `40` strict failures among `600` conditions.

| Failure category | Count |
|---|---:|
| Missing and extra terms | 34 |
| Strict mismatch but all-domain semantic success | 5 |
| Extra terms only | 1 |

### Concentration by benchmark

| Benchmark | Strict failures |
|---|---:|
| `poly3` | 34 |
| `nested_sine` | 4 |
| `base` | 2 |
| `interaction` | 0 |
| `trig_product` | 0 |

### Concentration by noise

| Noise ratio | Strict failures |
|---|---:|
| `0.10` | 36 |
| `0.03` | 4 |

### Concentration by scenario

| Scenario | Strict failures |
|---|---:|
| spurious | 14 |
| complementary | 13 |
| exception | 13 |

The scenario counts are nearly balanced. The dominant explanatory factors are therefore benchmark structure and noise, not a single scenario type.

## Principal failure boundary: high-noise polynomial surrogate ambiguity

Of the `34` `poly3` failures, `33` occur at noise ratio `0.10`. Each high-noise scenario has `11/20` strict failures, yielding only `45%` strict recovery for:

- `poly3` complementary, noise `0.10`;
- `poly3` spurious, noise `0.10`;
- `poly3` exception, noise `0.10`.

The recurrent substitutions are:

- missing `x1`, adding `sin(x1)`;
- missing `x1^2`, adding `cos(x1)`;
- missing both `x1` and `x1^2`, adding both `sin(x1)` and `cos(x1)`.

These are correlated local surrogates over the observed domain. They can have low interpolation error while extrapolating poorly. At the strict `1e-3` all-domain threshold, the high-noise `poly3` recovery remains `45%`. At the relaxed `1e-2` threshold it rises to approximately `60--70%`, depending on scenario, but the structural ambiguity remains genuine.

This must be presented as a central limitation, not hidden by aggregate averages.

## Five strict failures that are semantic successes

Five strict failures satisfy all four semantic domains at NMSE `<= 1e-3`:

- two `base` spurious cases with a very small extra linear `x2` coefficient;
- three `nested_sine` cases with a very small extra `x1` coefficient.

These cases show why strict and semantic metrics must be reported together. They are structurally over-specified but functionally accurate.

## Scientific consequences for Phase 2 and Phase 3

1. Do not alter or rerun seeds `9001--9020`.
2. Develop surrogate-discrimination improvements only on fresh seeds beginning at `10001`.
3. Add adaptive-domain or extrapolation-aware certificates as an ablation, not as a silent replacement of v0.5.
4. Compare fixed-catalog and catalog-misspecified settings.
5. Require equal-budget official PySR and another maintained symbolic-regression system.
6. Preserve strict structural recovery as a primary endpoint where ground truth is known.
7. Preserve all-domain semantic recovery as a co-primary endpoint.
8. Add hierarchical analysis over seeds and benchmark families before final claims.

## Claim boundary

Permitted:

> FedFalsify retained a substantial advantage under strict and all-domain semantic evaluation in the frozen controlled study, while its main failure mode was high-noise polynomial surrogate ambiguity.

Not permitted from Phase 1 alone:

- state-of-the-art symbolic regression;
- universal superiority;
- causal discovery;
- formal privacy;
- robustness to arbitrary expression grammars;
- Transactions readiness without official baselines, external datasets, ablations, scalability, and theory.
