# SCSV-Cert v6 post-independent forensic analysis

Status: **POST-SEAL FORENSICS ONLY; NO NEW EVIDENCE, NO THRESHOLD TUNING**.

This document analyzes the already-sealed independent artifact from workflow `31314059069` after the preregistered decision was fixed as **INDEPENDENT-VALIDATION NO-GO**. It does not alter the frozen SCSV-Cert v6 algorithm, the independent benchmark, seeds `20101--20105`, or Gates A--R.

## 1. Decision boundary

The independent study passed 17/18 frozen gates. Gate N failed because Panel-S exception recovery was:

- 4 clients: `24/30 = 0.8000`;
- 8 clients: `27/30 = 0.9000`;
- 16 clients: `28/30 = 0.9333`.

The frozen requirement was at least `0.90` at **every** tested client count, so the scientific decision remains NO-GO. The result may not be rescued by subgroup performance.

## 2. The failure is not candidate discovery

Across all `90` Panel-S exception conditions, the declared exception term

`I(x3>1)*x3^2`

was present in the full-v6 candidate bank in **90/90 conditions**. It was selected into the operational structure in `79/90 = 87.78%` conditions.

Therefore every Panel-S exception miss occurred **after successful candidate exposure**.

Across all independent exception conditions from Panels G, S and S32 (`n=200`), the exception term was in the candidate bank in **200/200** conditions and was selected in `187/200 = 93.5%`. There were `13` exception-selection misses in total.

This sharply separates the current failure from v4/v5 candidate-completeness failures: the v6 score proposer and high-recall bank exposed the restricted mechanism, but the set selector sometimes omitted it.

## 3. Exact localization of Gate-N failures

The six 4-client Panel-S exception misses were:

| Family | Profile | Seeds missed | Exception selected | Bank contained exception |
|---|---|---|---:|---:|
| `cubic_cross` | imbalanced | `20101--20105` | `0/5` | `5/5` |
| `multi_quadratic` | balanced | `20104` | `0/1` | `1/1` |

All other 4-client family/profile cells recovered the exception in `5/5` seeds.

The failed `cubic_cross` imbalanced client-size rotations were:

- `20101`: `150;71;72;104`;
- `20102`: `104;150;71;72`;
- `20103`: `72;104;150;71`;
- `20104`: `71;72;104;150`;
- `20105`: `150;71;72;104`.

Because the failure occurred for every rotation, including cases where the eligible final client was small, medium, or the largest client, the mechanism cannot be explained by eligible-client sample count alone.

## 4. Selector-path anatomy

For every one of the six Gate-N misses, the exception term was available to the selector but absent from the selected structure.

The selected structures were:

- `cubic_cross`, imbalanced, `20101`: `1;x3^2;x1^3;x1*x2`;
- `cubic_cross`, imbalanced, `20102`: `1;x3^2;x1^3;x1*x2`;
- `cubic_cross`, imbalanced, `20103`: `1;cos(x3);x1^3;x1*x2`;
- `cubic_cross`, imbalanced, `20104`: `1;x1;x3^2;sin(x1);x1*x2`;
- `cubic_cross`, imbalanced, `20105`: `1;x3^2;x1^3;x1*x2`;
- `multi_quadratic`, balanced, `20104`: `1;x3;x1^2;x2^2;x3^2`.

The selector was not hitting the maximum structural-size ceiling in the dominant failure pattern: the truth structure would still fit inside the frozen six-term cap. Thus the primary failure is **ranking/selection**, not capacity.

Among all `11` Panel-S exception-selection misses across 4/8/16 clients:

- `x3` appeared as a selected surrogate in `6/11`;
- `cos(x3)` appeared in `1/11`;
- `x3^2` was retained in `10/11`;
- the exception term was in the bank in `11/11` but selected in `0/11`;
- `7/11` of the wrong operational structures were nevertheless probe-certified, because the probe is audit-only and cannot reintroduce an omitted term.

The mean test NMSE of these exception-selection misses was approximately `0.01114`, compared with approximately `0.000598` when the exception term was selected in Panel S.

## 5. Shared-base core/restricted aliasing

All `13` exception-selection misses across the entire independent artifact occurred in truth families that contain the global core term `x3^2` together with the restricted exception term `I(x3>1)*x3^2`:

- `cubic_cross`;
- `multi_quadratic`;
- `nested_mixed`.

No exception-selection miss occurred in the independent families lacking the global `x3^2` core term.

This is mechanistically important. On the declared eligible client, where `x3>1` by construction, the exception feature equals `x3^2`. The global and restricted terms are therefore locally collinear on the eligible domain and are distinguishable only through their behavior on the outside-domain clients.

The failure is consequently best described as **shared-base core/restricted aliasing under a globally weighted selector**, not as missing observability.

## 6. Role mismatch in the frozen v6 architecture

The frozen discovery and probe stages understand term role, but the set selector does not.

The selector profile ranks candidate structures using

`log(weighted global MSE) + complexity * log(N) / N`,

where weighted MSE is pooled over all selector-client SSE divided by total selector support. This is appropriate for globally observable core structure, but a declared exception is active on only its eligible domain. Its local benefit is diluted by the outside-domain support during set ranking.

By contrast, the later probe code explicitly identifies eligible clients for an exception term and tests conditional necessity on those clients while requiring non-degradation outside the eligible domain.

However, the probe is non-destructive in v6. Once the role-blind selector omits an exception term, the role-aware probe never evaluates or restores it.

The architectural mismatch is therefore:

**role-aware discovery -> role-blind set selection -> role-aware but non-destructive probe**.

This explains why the candidate bank can be complete while a restricted mechanism is still lost.

## 7. Evidence against alternative explanations

The sealed rows argue against several simpler explanations:

1. **Candidate-bank failure:** false for the exception term; bank presence was 200/200 across all independent exception conditions.
2. **Final-size cap:** not binding in the dominant Gate-N failures.
3. **Eligible-client size alone:** cubic-cross imbalanced failed under every deterministic size rotation.
4. **Generic scaling collapse:** exact recovery increased from 4 to 8 to 16 clients and S32 achieved 1.0 exact/exception recovery.
5. **Score proposer as the cause:** the score proposer is necessary for high-recall exposure; removing it sharply damaged complete-truth bank coverage. The remaining defect is downstream of that exposure.

## 8. Successor mechanism hypothesis

A scientifically justified successor should preserve the successful v6 components and change only the role-mismatched selection stage.

Working hypothesis: **Role-Conditional Set Augmentation (RCSA)**.

Proposed architecture:

1. build the frozen high-recall bank exactly as v6;
2. select the core structure with the existing global set-information criterion, using core terms only;
3. for each declared exception term already present in the bank, identify eligible selector clients from observed support only;
4. compare `core` versus `core + exception` using an information criterion computed on eligible selector support, not pooled global support;
5. require non-degradation on outside-domain selector clients;
6. admit the exception only when the role-local information criterion improves and outside-domain non-degradation holds;
7. send the resulting structure to the existing independent role-aware probe;
8. keep the probe audit-only for the first exploratory diagnostic so that any gain can be attributed to role-conditioned selection rather than a second adaptive search.

This is not a recommendation to relax a numerical threshold. It is a correction of the **population over which the already-used information criterion is evaluated**, matching the declared observability semantics of the term.

## 9. Governance for the next experiment

The next experiment must be a **spent-seed exploratory mechanism diagnostic**, not fresh v7 evidence.

Permitted data:

- already-spent independent seeds `20101--20105` only;
- engineering smoke may use a separate engineering-only seed.

Prohibited:

- changing v6 thresholds using the sealed outcomes;
- rerunning Gate N as if it were new evidence;
- launching Layer-B SRSD as confirmatory evidence;
- overwriting historical SRSD/Beijing/v1--v6 artifacts;
- claiming independent validation success.

Only if a preregistered spent-seed RCSA diagnostic shows the expected mechanism signal without harming non-exception structure should a separately versioned successor protocol be frozen with genuinely fresh seeds.

## 10. Scientific conclusion

The independent NO-GO is narrow but real. SCSV-Cert v6 strongly generalizes for global structure and scales well to larger federations, but its global set selector can discard a locally valid restricted mechanism even when discovery has already exposed it. The dominant mechanism is shared-base aliasing between `x3^2` and `I(x3>1)*x3^2`, amplified by a selector objective that pools support across eligible and ineligible clients.

The next research target is therefore not broader candidate generation and not threshold relaxation. It is **role-conditioned model selection for restricted mechanisms**.
