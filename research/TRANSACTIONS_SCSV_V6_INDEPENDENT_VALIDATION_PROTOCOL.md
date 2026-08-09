# SCSV-Cert v6 independent scalability and generalization protocol

Status: **FROZEN AFTER THE SEALED V6 DEVELOPMENT GO AND BEFORE ANY INDEPENDENT-VALIDATION SEED**.

The SCSV-Cert v6 algorithm, high-recall bank, selector objective, structural family, probe certificate, thresholds, maximum bank size, maximum final size, score proposer, role conditioning and path-persistence rules are inherited unchanged from `TRANSACTIONS_SCSV_CERT_V6_PROTOCOL.md`. This stage may add only benchmark/data-generation adapters, study harnesses, audit code and reporting logic. It may not change the v6 mechanism.

## 1. Scientific question

Does the frozen SCSV-Cert v6 mechanism retain its structural advantage when it is tested on (i) truth mechanisms that are new combinations of the already-frozen grammar and were not among the five v6 development families, and (ii) substantially larger and imbalanced federations, without tuning on the new outcomes?

This is an **independent synthetic validation stage**, not another development stage. Passing permits execution of a separately preserved external SRSD validation with the same frozen v6 mechanism. Failure is retained and blocks a synthetic-generalization claim.

## 2. Algorithm firewall

The following are immutable:

- `scsv_cert_method` operational rule;
- role-conditioned discovery;
- path persistence;
- discovery-only score proposer;
- bundle rescue disabled;
- maximum bank size `10`;
- maximum operational structure size `6` including intercept;
- one-shot fit/selector/probe sufficient-statistic packets;
- selector score `log(MSE) + complexity * log(N) / N`;
- deterministic selector tie breaks;
- probe audit is non-destructive;
- exception eligible-client semantics;
- numerical ridge and all inherited thresholds.

No independent-validation result may be used to modify these rules.

## 3. Independent truth families

All truth terms are already supported by the frozen `BenchmarkTermCatalog`, but their combinations are new relative to the five v6 development benchmark families. The exact five independent families are:

1. `cubic_cross`
   - `0.8*x1^3 + 1.2*x1*x2 + 0.5*x4`
2. `fourier_quadratic`
   - `1.0*cos(x1) + 0.9*sin(x3) + 0.7*x4^2`
3. `nested_mixed`
   - `1.0*sin(x1+x1^2) + 0.6*x2 + 0.8*x3^2`
4. `multi_quadratic`
   - `0.6*x1^2 + 0.5*x2^2 + 0.8*x3^2 + 0.4*x4^2`
5. `trig_cross`
   - `1.2*sin(x1)*cos(x2) + 0.7*cos(x3) + 0.5*x4`

For the `exception` scenario, the already-declared restricted term `0.75*I(x3>1)*x3^2` is appended exactly as in the frozen development generator.

These families test new structural combinations and truth roles without changing the operator vocabulary. New operators are intentionally excluded so that failure can be attributed to generalization of the frozen mechanism rather than simultaneous grammar expansion.

## 4. Client-generation semantics

The same domain-shift geometry used by the preregistered benchmark generator is retained:

- client-specific phase shifts for `x1`, `x2` and `x3`;
- `x4` standard normal;
- `spurious`: the first client receives the same local shortcut construction on `x4`;
- `exception`: only the final client is inside the declared `x3 > 1` gated region, while all other clients remain outside.

For `balanced` conditions every client receives the same requested number of rows.

For `imbalanced` conditions, client row counts are a deterministic geometric profile from `0.50x` to `1.50x` the nominal rows/client, rounded to integers and clipped at a minimum of `50`. The profile is monotone in client index and then deterministically rotated by `seed % num_clients` so the largest client is not always associated with the same domain phase. No target value is used to define client size.

Noise is generated from the pooled noiseless target scale exactly as in the frozen benchmark generator.

## 5. Independent validation matrix

### Panel G — unseen-combination generalization

- 5 independent truth families;
- 3 scenarios: `complementary`, `spurious`, `exception`;
- noise ratios: `0.10`, `0.20`;
- samples/client: `100`, `250`;
- clients: `4`;
- profile: `balanced`;
- 5 independent seeds.

Total: `5 * 3 * 2 * 2 * 5 = 300` matched conditions.

### Panel S — federation scalability and imbalance

Representative families: `cubic_cross`, `multi_quadratic`, `trig_cross`.

- 3 scenarios;
- noise ratio: `0.20`;
- nominal samples/client: `100`;
- client counts: `4`, `8`, `16`;
- profiles: `balanced`, `imbalanced`;
- 5 independent seeds.

Total: `3 * 3 * 3 * 2 * 5 = 270` matched conditions.

### Panel S32 — targeted 32-client stress

Family: `multi_quadratic`.

- scenarios: `complementary`, `exception`;
- noise ratio: `0.20`;
- nominal samples/client: `100`;
- clients: `32`;
- profiles: `balanced`, `imbalanced`;
- 5 independent seeds.

Total: `1 * 2 * 1 * 1 * 2 * 5 = 20` matched conditions.

Overall: **590 matched conditions**.

## 6. Frozen methods

Exactly six methods are retained for every condition:

1. `legacy-certificate`;
2. `hr-v5-full`;
3. `scsv-v6-full` — primary frozen method;
4. `scsv-v6-no-score-proposer` — inherited mechanism ablation;
5. `centralized-forward` — finite-catalog reference;
6. `score-only-federated` — high-recall predictive comparator.

Therefore the complete independent synthetic artifact contains **3,540 rows**.

## 7. Seed firewall

Engineering smoke only:

- `20001`

Independent validation seeds:

- `20101`, `20102`, `20103`, `20104`, `20105`

Repository search at protocol freeze found no prior occurrence of `20101`. The full block is reserved for this stage. Once any full independent-study path evaluates one independent seed, all five are considered spent. Prior v1-v6 development, exploratory, smoke, external and confirmation seeds are prohibited.

## 8. Primary and supporting endpoints

Primary endpoint: strict exact recovery of the nonconstant truth-term set.

Supporting endpoints:

- term precision and recall;
- test NMSE;
- spurious acceptance;
- exception recovery;
- candidate-bank target recall;
- complete-truth bank coverage;
- candidate-bank size and nuisance count;
- probe-certification fraction;
- necessity and swap diagnostic failures;
- candidate sets evaluated;
- runtime;
- communication bytes;
- communication bytes per client;
- exact recovery by panel, truth family, scenario, noise, sample size, client count and balance profile.

No subgroup may replace the global Panel G primary comparison.

## 9. Frozen independent-validation gates

All gates must pass.

### New-combination generalization

A. Panel G v6 exact recovery >= Panel G Legacy + `0.05`.

B. Panel G v6 exact recovery >= Panel G HR-VFS v5 + `0.10`.

C. Panel G v6 exact recovery >= Panel G centralized-forward - `0.05`.

D. Panel G mean term precision >= `0.95`.

E. Panel G mean term recall >= `0.95`.

F. Panel G mean test NMSE <= Panel G Legacy mean test NMSE.

G. Panel G spurious acceptance <= `max(0.05, Legacy + 0.01)`.

H. Panel G exception recovery >= `0.90`.

I. Panel G candidate-bank target recall >= `0.98`.

J. Panel G complete-truth bank coverage >= `0.95`.

### Scalability and imbalance

K. In Panel S, at each client count `4`, `8`, and `16`, v6 exact recovery >= Legacy exact recovery + `0.03` at the same client count.

L. Panel S v6 exact recovery at 16 clients >= its 4-client exact recovery - `0.03`.

M. Panel S imbalanced v6 exact recovery >= balanced v6 exact recovery - `0.05`.

N. Panel S exception recovery at every client count >= `0.90`.

O. Panel S median communication bytes per client at 16 clients <= `1.50x` the corresponding 4-client median.

P. Panel S median runtime at 16 clients <= `5.0x` the corresponding 4-client median.

Q. Panel S32 v6 exact recovery >= `0.85` and Panel S32 exception recovery >= `0.85`.

### Certificate sanity

R. Across all independent conditions, v6 probe-certification fraction >= `0.70`.

Any failed gate yields **INDEPENDENT-VALIDATION NO-GO**. No threshold relaxation or subgroup rescue is permitted on seeds `20101--20105`.

## 10. Frozen statistical analysis

Matched key:

`(panel, benchmark, scenario, noise, nominal_samples_per_client, client_count, balance_profile, seed)`.

Report:

- paired v6 versus Legacy/v5/centralized exact win-loss-tie counts;
- exact McNemar tests for paired binary exact recovery;
- bootstrap 95% confidence intervals for matched exact-recovery differences using condition-level resampling;
- family/scenario/noise/client-count/profile stratification;
- cluster summaries by seed and truth family;
- communication/client and runtime scaling ratios;
- term-level error taxonomy after all structures are frozen.

Multiplicity-adjusted secondary hypothesis tests are reported as secondary; they do not replace the preregistered gates.

## 11. Engineering smoke boundary

Before any `20101--20105` condition is executed, CI on `20001` only must verify:

- all five independent truth families use only frozen catalog terms;
- truth families are distinct from the five development truth sets;
- balanced and imbalanced generators are deterministic;
- imbalanced clients retain at least 50 observations;
- 4/8/16/32-client generation is valid;
- the v6 function object/source is inherited rather than copied or modified in the independent module;
- one representative v6 condition completes;
- smoke output contains only seed `20001`;
- the independent validation gate is not evaluated in smoke mode.

Only engineering bugs in adapters, generators, audit or workflow plumbing may be repaired after this protocol. The v6 scientific mechanism and gates may not change.

## 12. Evidence preservation

The independent workflow must:

1. check out an exact authorization SHA;
2. verify frozen protocol and implementation hashes;
3. run smoke/invariant tests before evidence;
4. execute exactly 3,540 rows;
5. audit row count, condition count, seeds, methods, finite values and duplicates;
6. record source SHA and per-file SHA-256 hashes;
7. upload the sealed artifact **before** attempting the repository evidence commit;
8. commit the sealed evidence without modifying historical v1-v6 or older external artifacts.

A technical preservation failure may be deterministically recovered on the same spent seeds only when clearly labeled recovery; it is not new evidence.

## 13. External-validation boundary

A synthetic independent GO does not establish real-world validity. It authorizes Layer B: rerun the archived SRSD-Feynman external suite through the frozen SCSV-Cert v6 adapter, preserving official train/test splits, natural domain clients, nuisance stress, truth-supported and deliberate catalog-misspecification conditions, and the historical PySR comparator. Old SRSD/Beijing findings remain immutable historical evidence and may not be overwritten.
