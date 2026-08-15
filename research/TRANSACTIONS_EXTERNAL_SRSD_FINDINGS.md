# SRSD-Feynman external validation findings

Status: **final unit-invariant external artifact complete; not final paper confirmation**

## Evidence identity

- final workflow run: `30862392893`;
- artifact: `external-srsd-v4`;
- artifact ID: `8874930076`;
- artifact digest: `sha256:5ff59b002458a9cd439c105757bebf579d836a361b4aac80f43e3956a7af4c8b`;
- source merge commit: `b62bd3627e59e3165f9c4aa3d64259d4c2e39fdc`;
- rows: `35`;
- equations: `5`;
- official train/test splits retained;
- clients: four quartile domains of the first physical input;
- nuisance stress: three deterministic irrelevant variables per equation.

The final implementation uses training-client-only scaling for inputs, targets,
and every nonconstant finite-catalog basis column. Term names and structural
identity are unchanged by basis scaling.

## Repair audit

Three predecessor attempts remain recorded rather than erased:

1. run `30860646170` failed because two official equation files had fewer
   predictors than the provisional schema assumed;
2. run `30861162857` was invalidated after audit because absolute scale floors
   made tiny nonconstant physical targets appear approximately zero;
3. run `30861771502` fixed target scaling and truth aliases, but finite basis
   columns still depended on physical units, which unfairly affected ridge and
   score comparisons.

V4 repairs only these measurement issues. The five problems, official splits,
client partitions, nuisance variables, methods, seeds, and PySR budget were not
changed.

## Truth-supported finite catalog

| Method | Strict exact recovery | Semantic recovery `1e-6` | Dummy-free | Mean test NMSE |
|---|---:|---:|---:|---:|
| Centralized forward | **5/5** | **5/5** | 5/5 | approximately `1.56e-24` |
| Score-only federated | **5/5** | **5/5** | 5/5 | approximately `1.56e-24` |
| Full FedFalsify | 4/5 | 4/5 | **5/5** | `0.01735` |

The first four supported equations were recovered exactly by all three finite
methods:

- `x0*x1`;
- `m*z` with gravity absorbed into the scalar coefficient;
- `r*F*sin(theta)`;
- `-mu*B*cos(theta)`.

For `II.27.18`, centralized-forward and score-only federated search selected the
named `E^2` mechanism exactly. Full FedFalsify selected the linear surrogate

```text
0.9538 * z(E)
```

and obtained test NMSE `0.08676`. This is a retained certificate/stopping
failure, not a catalog or unit-normalization failure.

The exact score-only/centralized recovery with full FedFalsify failure is
consistent with the Beijing result: the current certificate path can be more
conservative than aggregate score search even when the correct catalog term is
available.

## Deliberate catalog misspecification

The named ground-truth term and algebraically identical aliases were removed
without changing any setting.

| Method | Semantic recovery `1e-4` | Mean test NMSE | Dummy-free |
|---|---:|---:|---:|
| Centralized forward | 0/5 | `0.5546` | 5/5 |
| Full FedFalsify | 0/5 | `0.5627` | 5/5 |
| Score-only federated | 0/5 | `0.5532` | 4/5 |

The misspecification condition therefore establishes an explicit finite-catalog
boundary: no finite method reconstructed any of the five physical mechanisms
once the required composite term was unavailable.

Score-only search selected one nuisance-dependent term on the misspecified
`II.15.4` problem. This negative outcome is retained and prevents a universal
nuisance-rejection claim.

## Official PySR adaptive search

| Problem | Semantic recovery `1e-4` | Test NMSE |
|---|---:|---:|
| `I.12.1` | yes | `1.86e-15` |
| `I.14.3` | yes | `2.56e-17` |
| `I.18.12` | no | `0.001289` |
| `II.15.4` | no | `0.89199` |
| `II.27.18` | yes | `1.58e-16` |

Official PySR achieved semantic recovery on `3/5` equations and selected no
appended nuisance variable. It recovered the squared-energy equation on which
full FedFalsify failed, reinforcing the need for adaptive algebraic search.

At the frozen budget, the nested sine-product and magnetic cosine-product
problems remained failures for PySR. This is a five-problem controlled external
suite, not a general ranking of symbolic-regression systems.

## Cross-study interpretation

The synthetic and external evidence now supports a narrower, more credible
conclusion:

- when the named true mechanism is available, finite-catalog aggregate search
  can be extremely reliable and nuisance-resistant;
- full FedFalsify's certificate/stopping logic can reject or fail to reach a
  useful shared term that score-only search discovers;
- finite catalogs fail completely under deliberate mechanism misspecification;
- official adaptive search covers some mechanisms outside the finite method's
  reliable path, but also fails on difficult trigonometric interactions at the
  frozen budget.

## Permitted claim

> On five official SRSD-Feynman equations partitioned into four domain clients,
> score-only federated finite-catalog search and centralized-forward selection
> recovered all five named mechanisms when the truth term was available. Full
> FedFalsify recovered four, failing on `E^2`, while official PySR recovered
> three equations adaptively. Removing the named mechanism caused all finite
> methods to fail semantically.

## Prohibited claims

- universal superiority over official symbolic-regression systems;
- catalog-free scientific discovery by the current FedFalsify method;
- perfect nuisance rejection under misspecification;
- formal privacy from aggregate messages alone;
- Transactions submission readiness.

## Research decision

Together with the negative Beijing result, this study closes the two-dataset
external execution gate but opens a mandatory algorithmic gate: the final method
must combine validation-aware/sample-split certificate logic with an adaptive or
score-only fallback that prevents premature stopping and catalog-lock failures.
The archived external artifacts must not be retrospectively replaced by that
future development study.
