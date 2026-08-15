# FedFalsify Transactions External Validation Plan

## 1. Purpose

The frozen custom synthetic study is necessary but insufficient for a Q1 Transactions claim. External validation must test three distinct questions:

1. Does the method recover equations outside the five custom benchmark families?
2. Does cross-client falsification remain useful when clients arise naturally rather than by arbitrary random splitting?
3. Does the method produce stable, simple, and predictive expressions on real scientific or engineering data where the exact true equation is unknown?

This plan uses four complementary study families. The final manuscript should include at least three; all four are preferred if computationally feasible.

## 2. Dataset family A — established symbolic-regression benchmarks

### Source

- SRBench: https://github.com/cavalab/srbench
- SRSD scientific-discovery datasets: https://github.com/omron-sinicx/srsd-benchmark

SRBench is a living open benchmark containing modern symbolic-regression methods, standard machine-learning baselines, and hundreds of PMLB datasets. SRSD provides physics-informed sampling ranges and equations with known ground truth, including dummy-variable variants designed to test variable selection.

### Scientific role

- external ground-truth equation recovery;
- comparison against established SR methods;
- structural and semantic fairness;
- dummy-variable and catalog-misspecification stress;
- compatibility with community benchmarking practice.

### Client construction

Clients must be created by domain restrictions, not IID random splitting. For each equation, define clients using physically or mathematically meaningful input-domain regions, for example:

- quantiles or signed regions of one controlling variable;
- operational regimes documented by the benchmark;
- disjoint interpolation subdomains;
- deliberately complementary coverage regions;
- spurious local correlations introduced only in training clients.

At least one client-design protocol must be fixed before viewing method results. A second protocol may be used as a sensitivity analysis.

### Primary metrics

- strict exact recovery;
- canonical structural recovery;
- normalized edit distance;
- all-domain semantic recovery;
- interpolation and extrapolation NMSE;
- expression complexity;
- dummy-variable rejection;
- runtime and search budget.

### Inclusion rule

Select equations spanning polynomial, trigonometric, rational, interaction, and mixed forms. Exclude equations that require unsupported discontinuities unless every compared method receives the same operator support or the condition is explicitly marked unsupported.

## 3. Dataset family B — UCI Beijing Multi-Site Air Quality

### Source

Official UCI dataset:

https://archive.ics.uci.edu/dataset/501/beijing

The dataset contains hourly pollutant and meteorological data from 12 nationally controlled air-quality monitoring sites. Each site is a natural client, and meteorological observations are matched to nearby weather stations.

### Scientific role

- real multi-client environmental data;
- naturally heterogeneous geographic stations;
- cross-station generalization;
- expression stability without known true equations;
- shortcut rejection under station-specific correlations.

### Proposed prediction tasks

Primary task:

```text
PM2.5_t = f(PM10_t, SO2_t, NO2_t, CO_t, O3_t,
            temperature_t, pressure_t, dew_point_t,
            wind_speed_t, wind_direction_t,
            hour, month)
```

Secondary task:

```text
PM2.5_(t+1) = f(current pollutants, current meteorology,
                lagged PM2.5, hour, month)
```

The contemporaneous task is better suited to interpretable association discovery. The one-hour forecasting task provides a predictive robustness check. Claims must remain associational, not causal.

### Client definition

- one monitoring station per client;
- all 12 stations retained unless a station fails preregistered minimum-quality criteria;
- station identity never supplied as a predictor to the primary discovery model;
- leave-one-station-out evaluation used for cross-client generalization.

### Preprocessing

- chronological train/validation/test split within every station;
- no interpolation across the train/test boundary;
- missing-value handling fitted on training periods only;
- wind direction encoded using sine and cosine components;
- periodic time variables encoded cyclically;
- pollutant units retained and documented;
- optional log transform of strongly skewed concentrations determined on development data only;
- identical preprocessing across all methods.

### Primary metrics

- held-out station-wise MAE, RMSE, and normalized MSE;
- worst-station error;
- leave-one-station-out error;
- expression complexity;
- bootstrap term-selection frequency;
- sign stability;
- station-level non-degradation rate;
- communication bytes;
- comparison with pooled and local-only symbolic models.

### Leakage controls

- no random row split;
- no future observations in training transformations;
- lagged targets constructed before partitioning and validated chronologically;
- meteorological station matching accepted as dataset metadata, but station identity not used to memorize outcomes;
- duplicate timestamps and impossible pollutant values audited before modeling.

## 4. Dataset family C — NASA Li-ion Battery Aging

### Source

Official NASA Open Data Portal:

https://data.nasa.gov/dataset/li-ion-battery-aging-datasets

The dataset contains repeated charge, discharge, and impedance operations from multiple 18650 Li-ion batteries under different temperatures, current loads, depth-of-discharge conditions, and rest patterns. Experiments continue toward a 30% capacity-fade end-of-life criterion.

### Scientific role

- real run-to-failure engineering data;
- one battery cell as a natural client;
- heterogeneous operating conditions;
- interpretable degradation relationships;
- cross-battery expression stability.

### Proposed tasks

Primary task at discharge-cycle level:

```text
capacity = f(cycle_index, ambient_temperature,
             discharge_current_summary,
             voltage_summary,
             temperature_summary,
             impedance_or_resistance_features)
```

Secondary task:

```text
capacity_fade_rate = f(current_capacity,
                       temperature, load, impedance features,
                       elapsed cycles)
```

The feature set must use only measurements available by the prediction time. Future end-of-life information must never enter predictors.

### Client definition

- one physical battery cell per client;
- batteries with too few usable discharge cycles excluded using a preregistered threshold;
- operating-profile groups retained for subgroup analysis, not used to hide poor cells.

### Evaluation

- chronological holdout within each battery;
- leave-one-battery-out generalization;
- early-life-to-late-life extrapolation;
- capacity MAE and normalized MSE;
- expression complexity and dimensional plausibility;
- coefficient and term stability across bootstrap cycles;
- worst-battery performance;
- local versus federated versus pooled comparisons.

### Scientific caution

A compact equation that predicts capacity does not prove an electrochemical law. The paper may claim interpretable predictive degradation relationships, not causal battery physics, unless independently validated.

## 5. Dataset family D — NASA CMAPSS jet-engine degradation

### Source

Official downloadable NASA dataset:

https://data.nasa.gov/dataset/cmapss-jet-engine-simulated-data

The dataset contains multiple multivariate run-to-failure trajectories. Each trajectory corresponds to a different engine with unknown initial wear and manufacturing variation. The public collection provides FD001–FD004 subsets with one or six operating conditions and one or two fault modes, plus true test-set remaining-useful-life values.

### Scientific role

- large heterogeneous fleet;
- one engine as a natural client;
- operating-condition shifts;
- fault-mode variation;
- client-count scalability.

### Proposed tasks

Primary interpretable health-index task:

```text
normalized_cycle_age or RUL = f(operating_settings,
                                selected sensor measurements)
```

A secondary task may discover a compact degradation score whose monotonic relation with RUL is evaluated.

### Client construction challenge

Treating every engine as an independent federated client creates many small clients and is scientifically useful for scalability. A grouped alternative may aggregate engines by operating condition for sensitivity analysis. The primary client definition must be fixed before results.

### Evaluation

- official train/test separation preserved;
- no use of true test RUL during model selection;
- FD001–FD004 reported separately;
- engine-level cluster bootstrap;
- held-out-engine and held-out-condition evaluation;
- RMSE, normalized MSE, worst-engine error;
- expression complexity and stability;
- performance by fault mode;
- communication and runtime scaling with client count.

### Availability boundary

Use the public `CMAPSS Jet Engine Simulated Data` resource containing `CMAPSSData.zip`. Do not rely on the separate C-MAPSS simulator-software page, which may report software availability restrictions.

## 6. External method suite

Every real-data study must compare:

- full FedFalsify;
- local-only symbolic regression;
- pooled centralized symbolic regression;
- centralized catalog-matched model;
- score-only federated model;
- official PySR where grammar and resource budget are compatible;
- at least one additional maintained symbolic-regression system;
- a strong non-symbolic predictive baseline for context.

The non-symbolic baseline is not expected to be interpretable. It establishes the price of symbolic simplicity.

## 7. Statistical design

### Unit of inference

- SRBench/SRSD: equation or benchmark family;
- Beijing: monitoring station and time block;
- Battery: physical cell;
- CMAPSS: engine trajectory.

Rows within a client are not independent experimental replications.

### Required inference

- paired comparisons at the client or benchmark level;
- cluster bootstrap by natural client;
- leave-one-client-out estimates;
- median and worst-client effects;
- multiplicity correction within declared comparison families;
- sensitivity analysis across semantic thresholds;
- hierarchical model or cluster-robust analysis across datasets.

### Seed policy

- development seeds: `10001--10030`;
- external preprocessing/bootstrap seeds: `12001--12050`;
- final external confirmation seeds fixed separately before execution.

No Study A seed may be reused for method tuning.

## 8. Go/no-go rules for each external dataset

A dataset enters the paper only when:

1. its source and license permit reproducible use;
2. the client definition is natural and declared before model comparison;
3. preprocessing is leakage-safe;
4. all methods receive the same usable observations and predictors;
5. failed runs are retained;
6. the result is not selected merely because FedFalsify performs well;
7. expression stability and client-wise outcomes are reported, not only pooled error;
8. limitations and unsupported grammar conditions are explicit.

A negative or neutral external result remains scientifically valuable and must not be silently dropped after execution.

## 9. Recommended final paper allocation

Main paper:

- selected SRBench/SRSD ground-truth suite;
- Beijing multi-station study;
- NASA battery study;
- one compact CMAPSS scalability table or figure.

Supplement:

- complete per-equation benchmark results;
- all 12 station results;
- all battery-cell results;
- FD001–FD004 breakdown;
- preprocessing manifests;
- failure logs;
- extra expressions and stability plots.

## 10. Current status

- dataset families selected;
- client definitions drafted;
- targets and leakage controls drafted;
- no external performance result has yet been generated;
- external evidence therefore cannot yet support a manuscript claim.

The next implementation task is to create immutable dataset manifests and loaders, beginning with UCI Beijing and the SRBench/SRSD ground-truth suite.
