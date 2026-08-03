# Transactions external validation protocol

Status: **frozen before complete external results are inspected**

## 1. Purpose

This protocol governs the first two external studies. Results are retained whether
positive, neutral, or negative. Dataset or station subsets may not be removed
because a method performs poorly.

## 2. Study E1 — UCI Beijing multi-site air quality

### Source and client definition

- source: UCI dataset 501, DOI `10.24432/C5RK5G`;
- license: CC BY 4.0;
- client: one nationally controlled monitoring station;
- expected clients: all 12 stations;
- target: contemporaneous `PM2.5`;
- claim type: associational prediction, never causal pollution discovery.

### Frozen split and preprocessing

- chronological split within every station: 60% train, 20% validation, 20% test;
- rows with missing target are dropped before splitting;
- numeric imputation uses the station training-period median only;
- missingness indicators, cyclic wind, hour, and month encodings are retained;
- station identity is never a predictor;
- symbolic fitting uses a deterministic chronological systematic sample capped at
  2,000 training rows per station;
- validation and test periods are not used for scaling or term selection;
- full chronological test periods are used for final station metrics;
- feature and target standardization is fitted from aggregate training sums and
  sums of squares only.

### Frozen feature set

`PM10`, `SO2`, `NO2`, `CO`, `O3`, temperature, pressure, dew point, rain,
wind speed, cyclic hour, and cyclic month.

The finite catalog contains all selected linear terms, declared squared physical
terms, and six preregistered interactions. No station-specific term is allowed.

### Methods

- full FedFalsify;
- centralized forward finite-catalog model;
- score-only federated finite-catalog model;
- pooled linear ridge on all selected linear terms;
- local-only finite-catalog model;
- official PySR pooled-data baseline;
- leave-one-station-out FedFalsify and centralized-forward sensitivity.

### Primary endpoints

1. mean station-level test NMSE;
2. median station-level test NMSE;
3. worst-station test NMSE;
4. station-cluster bootstrap interval for mean NMSE;
5. station non-degradation rate relative to local-only models.

MAE, RMSE, expression complexity, runtime, communication, and leave-one-station-out
error are secondary endpoints. Each station is the inferential unit; hourly rows
are not treated as independent replications.

## 3. Study E2 — SRSD-Feynman ground-truth suite

### Source

Official `yoshitomo-matsubara/srsd-feynman_easy` files hosted on Hugging Face,
associated with the SRSD benchmark and licensed CC BY 4.0.

### Frozen problems

- `feynman-i.12.1`;
- `feynman-i.14.3`;
- `feynman-i.18.12`;
- `feynman-ii.15.4`;
- `feynman-ii.27.18`.

These cover product, triple interaction, sine interaction, cosine interaction,
and squared interaction forms.

### Frozen client construction

- official train/validation/test files are preserved;
- four clients are defined by quartiles of the first physical input on the
  official training split;
- three deterministic independent nuisance variables are appended to every
  split using fixed external-study seeds;
- no result-dependent client boundary or variable removal is permitted.

### Conditions

1. `truth-supported`: the finite catalog includes one named composite term that
   represents the physical ground-truth structure;
2. `catalog-misspecified`: the same term is removed without changing any other
   setting;
3. `adaptive-search`: official PySR searches from shared primitive operators.

Training-only scaling is allowed, but the named true term must reconstruct the
original physical coordinates before evaluating the physical equation.

### Methods and endpoints

- FedFalsify;
- centralized forward finite-catalog search;
- score-only federated search;
- official PySR.

Primary endpoints:

- strict exact recovery for truth-supported finite-catalog methods;
- official-test semantic recovery at NMSE `1e-6` and `1e-4`;
- official-test NMSE;
- nuisance-variable rejection;
- degradation under catalog misspecification.

## 4. Governance

- external seeds begin at `12001`;
- frozen Study A seeds `9001--9020` and final confirmation seeds `11001+` are not
  used for external method tuning;
- failed downloads, model failures, non-finite predictions, and unsupported
  equations remain visible failures;
- raw dataset files are identified by SHA-256 hashes;
- every aggregate artifact records source commit, environment, row counts, and
  scientific boundaries;
- these studies are external validation, not final confirmation;
- no manuscript claim is upgraded until both complete artifacts are inspected.
