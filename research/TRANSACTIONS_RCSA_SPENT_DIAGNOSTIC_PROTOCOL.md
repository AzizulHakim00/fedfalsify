# Role-Conditional Set Augmentation (RCSA) spent-seed diagnostic protocol

Status: **FROZEN BEFORE ANY RCSA DIAGNOSTIC RUN**.

This is a post-independent, spent-seed mechanism diagnostic motivated by the sealed SCSV-Cert v6 independent NO-GO. It is **not v7 evidence**, does not reopen Gate N, and cannot authorize an external-confirmatory claim by itself.

## 1. Scientific question

The sealed independent artifact showed that the declared exception term was present in the full-v6 candidate bank in every independent exception condition, but the globally weighted set selector sometimes omitted it. Does a strictly role-conditioned augmentation of the already-frozen v6 selector structure rescue those omissions without changing v6 core selection?

## 2. Causal isolation rule

The diagnostic must call the frozen `scsv_cert_method` unchanged and treat its operational selector structure as an immutable anchor.

RCSA may **only** consider adding a declared exception term when all of the following hold:

1. the term is already present in the frozen v6 candidate bank;
2. the term is absent from the frozen v6 selector structure;
3. adding it does not exceed the inherited maximum structure size of six terms including intercept.

RCSA may not delete, replace, reorder, or retune any term already selected by v6.

If no exception term satisfies these conditions, the RCSA diagnostic output must be exactly the frozen v6 operational structure.

## 3. Role-local selector test

For a missing banked exception term `e`, let `S` be the frozen v6 selector structure and `S+e` the augmented structure.

Both candidates are fit using the same discovery/fit sufficient-statistic packets used by SCSV.

### Eligible selector clients

Eligibility is determined from **selector packets only**. A selector client is eligible for `e` when its observed support for the term is at least

`max(3, ceil(0.10 * selector_support))`.

Probe support is not consulted during this decision.

If no selector client is eligible, the augmentation is rejected.

### Role-local information criterion

On the eligible selector clients only, compute the same information criterion family already used by SCSV:

`J = log(MSE) + complexity * log(N) / N`.

The augmentation passes the role-local selector test iff

`J(S+e) < J(S)`.

No additional numerical margin or tuned threshold is allowed.

### Outside-domain non-degradation

On selector clients outside the eligible set, the augmented structure must not increase total selector SSE beyond numerical tolerance `1e-10` relative to the frozen v6 anchor.

The exception is admitted iff both the role-local information criterion improves and outside-domain non-degradation holds.

## 4. Probe semantics

After the selector-only augmentation decision, the resulting structure is sent to the existing SCSV independent probe diagnostics unchanged.

The probe remains **audit-only** in this diagnostic. It may report necessity/swap/eligibility failures, but it does not delete the newly admitted exception or replace the frozen v6 anchor.

This preserves causal attribution to the role-conditioned selector augmentation.

## 5. Scope of exception handling

The current independent benchmark contains exactly one declared restricted exception term, `I(x3>1)*x3^2`. This diagnostic is intentionally scoped to that one-term mechanism question. A general multi-exception successor algorithm must be designed separately only if the diagnostic signal is positive.

## 6. Seeds and evidence boundary

Engineering-only smoke seed:

- `21001`

Repository search before protocol freeze found no prior occurrence of `21001`.

Scientific diagnostic data:

- only already-spent independent seeds `20101`, `20102`, `20103`, `20104`, `20105`;
- the frozen 590-condition independent matrix geometry is reused;
- the sealed v6 rows at `results/scsv_v6_independent/rows.csv` are the historical comparator and must not be altered.

No new validation seed may be consumed in this diagnostic.

## 7. Diagnostic matrix

Run exactly one RCSA diagnostic output for each of the already-defined 590 independent conditions:

- Panel G: 300 conditions;
- Panel S: 270 conditions;
- Panel S32: 20 conditions.

Total new diagnostic rows: **590**.

The historical frozen `scsv-v6-full` row for each matched condition is read from the sealed independent artifact rather than rerun as new evidence.

## 8. Frozen diagnostic endpoints

For every condition report:

- frozen v6 anchor structure;
- exception present in bank;
- exception already in anchor;
- RCSA attempted;
- eligible selector client IDs and support;
- anchor role-local information score;
- augmented role-local information score;
- outside selector SSE before/after;
- augmentation accepted;
- diagnostic final structure;
- exact recovery;
- term precision/recall;
- test NMSE;
- exception recovery;
- probe certification and term diagnostics;
- additional diagnostic communication/runtime, labeled as unoptimized wrapper overhead.

## 9. Frozen mechanism-signal criteria

This diagnostic is considered **RCSA-MECHANISM-SIGNAL PASS** only if all criteria pass:

A. The exception term remains present in the candidate bank in exactly the same conditions as frozen v6.

B. All non-exception conditions produce an operational term set exactly identical to frozen v6.

C. Every exception condition where frozen v6 already selected the exception remains structurally unchanged.

D. Panel-S 4-client exception recovery increases from frozen v6 `0.8000` to at least `0.9000`.

E. Panel-S 8-client exception recovery is at least the frozen v6 value `0.9000`.

F. Panel-S 16-client exception recovery is at least the frozen v6 value `0.9333`.

G. Panel-S32 exception recovery remains `1.0000`.

H. Across all 590 conditions, RCSA exact recovery is at least frozen v6 exact recovery minus `0.01`.

I. RCSA creates **zero exact-recovery harms** among conditions that were exact under frozen v6.

J. Spurious acceptance does not exceed the frozen v6 condition-matched value in any non-exception condition; by construction these structures should be identical.

K. Among the 13 already-observed independent exception-selection misses, at least half are rescued (`>=7/13`) without changing any previously selected core term.

One failed criterion yields **RCSA-MECHANISM-SIGNAL NO-GO**. No post-result threshold adjustment or subgroup rescue is permitted.

## 10. Engineering smoke boundary

Before running any spent-seed diagnostic condition, seed `21001` only must verify:

- the wrapper calls the frozen `scsv_cert_method` rather than copying/modifying it;
- no selected v6 term can be deleted or replaced;
- selector eligibility uses selector packets only;
- role-local IC uses exactly the existing SCSV information-score form;
- outside non-degradation uses selector packets only;
- probe packets cannot influence the augmentation decision;
- a no-exception condition returns the exact v6 structure;
- an already-selected exception remains unchanged;
- an omitted banked exception can be evaluated without exceeding the six-term cap;
- smoke output contains only `21001`;
- RCSA mechanism-signal criteria are not evaluated in smoke mode.

Only engineering bugs may be repaired after this freeze. The diagnostic decision rule and criteria A--K may not change after any `20101--20105` diagnostic result is consumed.

## 11. Promotion boundary

A PASS would mean only that the sealed NO-GO mechanism has a plausible role-conditioned repair on already-spent data. It would authorize design of a separately versioned, generalized successor protocol with genuinely fresh seeds.

A PASS would **not** convert SCSV-Cert v6 to independent GO and would **not** authorize retrospective SRSD confirmation.

A NO-GO would retire this RCSA formulation and retain the v6 independent failure as the current boundary.
