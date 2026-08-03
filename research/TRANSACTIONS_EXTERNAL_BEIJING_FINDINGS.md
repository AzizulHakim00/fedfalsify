# Beijing 12-station external validation findings

Status: **complete external validation; negative for the current full FedFalsify configuration**

## Evidence identity

- workflow run: `30860646170`;
- artifact: `external-beijing-v1`;
- artifact ID: `8874265597`;
- artifact digest: `sha256:8d00c6d856d3888cfcc549a22c94f1d9e8962425360296eb010ca72cdb71992b`;
- source merge commit: `fe25d5df66d0350327cdff8015f3c30797adc6ef`;
- official raw rows: `420,768`;
- natural clients: all `12` monitoring stations;
- artifact rows: `84` station-test results and `24` leave-one-station-out results.

All methods used the same deterministic training sample of at most 2,000
chronological training rows per station. Test metrics used each station's complete
chronological test period. Imputation and standardization were fitted from
training information only.

## Primary station-level result

Lower NMSE is better.

| Method | Mean station NMSE | Median | Worst station | Station non-degradation versus local |
|---|---:|---:|---:|---:|
| Pooled histogram gradient boosting | **0.07143** | **0.07013** | **0.08641** | **12/12** |
| Centralized forward finite catalog | 0.08718 | 0.08653 | 0.10233 | 7/12 |
| Score-only federated finite catalog | 0.08718 | 0.08653 | 0.10233 | 7/12 |
| Pooled linear ridge | 0.09484 | 0.09797 | 0.10595 | 6/12 |
| Local-only forward | 0.09996 | 0.09129 | 0.14380 | reference |
| Full FedFalsify | 0.11910 | 0.11767 | 0.14789 | 1/12 |
| Official PySR | 0.11911 | 0.11767 | 0.14790 | 1/12 |

Station-cluster bootstrap intervals for mean NMSE were:

- gradient boosting: `[0.06579, 0.07693]`;
- centralized forward: `[0.08195, 0.09242]`;
- local-only forward: `[0.08788, 0.11325]`;
- full FedFalsify: `[0.11211, 0.12683]`.

The intervals and station-level non-degradation counts show that the current full
FedFalsify configuration did not transfer successfully to this real multi-site
task.

## Discovered expressions

Full FedFalsify stopped after the single standardized predictor

```text
0.8412 * PM10
```

with the stop reason `target federated MSE reached`.

Official PySR independently returned essentially the same one-term expression:

```text
0.8411471 * PM10
```

The score-only federated and centralized-forward procedures selected the same
six-term finite-catalog model:

```text
-0.01833
+ 0.6253 * PM10
+ 0.2425 * CO
- 0.1280 * PM10 * wind_speed
+ 0.3764 * dew_point
+ 0.2940 * month_cos
```

This model reduced mean station NMSE from approximately `0.1191` to `0.0872`.
The exact equality between the centralized and score-only federated outputs shows
that aggregate score communication was sufficient for this catalog and sample,
whereas the full certificate/stopping configuration was overly conservative.

## Leave-one-station-out sensitivity

| Method | Mean held-station NMSE | Worst held station |
|---|---:|---:|
| Centralized forward | **0.08743** | **0.10293** |
| Full FedFalsify | 0.11916 | 0.14823 |

Excluding each target station from model fitting did not materially change the
ranking. The failure is therefore not explained by a single station dominating
the pooled training sample.

## Scientific interpretation

This is a retained negative result for the current headline algorithm. It reveals
three limitations:

1. the current target-MSE stopping criterion can terminate before useful shared
   covariates and interactions enter the model;
2. a certificate intended to reject shortcuts can also suppress real but
   heterogeneous environmental associations;
3. the synthetic benchmark advantage does not automatically transfer to
   observational multi-site prediction.

The non-symbolic gradient-boosting model is the strongest predictive context
baseline but is not an interpretable symbolic contribution. The finite-catalog
centralized and score-only federated models provide the strongest interpretable
results in this study.

## Permitted claim

> On the frozen Beijing 12-station study, the current full FedFalsify
> configuration was overly conservative and underperformed centralized-forward,
> score-only federated, local-only, linear, and gradient-boosting alternatives.
> A score-only federated finite-catalog search matched the centralized symbolic
> expression without pooling observation rows.

## Prohibited claims

- superiority of full FedFalsify on real air-quality data;
- causal effects of pollutants or weather variables;
- formal privacy from aggregate communication alone;
- general superiority of score-only search without additional external studies;
- Transactions readiness.

## Required algorithmic response

This result motivates a fresh development study—not retrospective retuning of
this artifact—covering:

- sample-split or cross-fitted certificate evaluation;
- validation-aware stopping rather than a training target-MSE stop;
- explicit non-degradation against local and score-only candidate paths;
- calibration across client heterogeneity and observational covariate shift.

The archived Beijing artifact remains immutable and will serve as the negative
external baseline for those developments.
