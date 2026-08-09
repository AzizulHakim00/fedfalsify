# Frozen-Core Role Residual Augmentation (FCRRA) spent-seed diagnostic protocol

Status: **FROZEN BEFORE ANY FCRRA DIAGNOSTIC RUN**.

This protocol follows the sealed RCSA spent-seed NO-GO. It is a post-hoc mechanism diagnostic only. It is not SCSV-Cert v7 evidence, cannot reopen the independent v6 decision, and cannot authorize external confirmation.

## 1. Scientific question

The RCSA diagnostic showed that globally refitting the frozen v6 core together with a missing restricted exception term produced zero rescue: all 13 attempted additions failed role-local selector information score even though outside-domain selector SSE improved. Does freezing the shared v6 coefficients and estimating only the restricted-term coefficient from eligible-domain residuals recover the missing exception mechanism without altering any shared prediction outside that role?

## 2. Immutable anchor

Every condition must first call the frozen `scsv_cert_method` unchanged with the same settings used in the independent study.

The returned v6 selector structure is the immutable shared structural anchor. FCRRA may not:

- delete or replace any v6-selected term;
- change the candidate bank;
- rerank shared terms;
- change any v6 threshold;
- change the maximum structure size;
- refit or modify the anchor shared coefficients during the FCRRA admission test.

FCRRA may only evaluate a declared exception term that is already present in the v6 candidate bank, absent from the v6 selector structure, and can be added without exceeding six terms including intercept.

## 3. Frozen-core residual coefficient

Let the frozen v6 anchor candidate be

`f_S(x) = sum_j beta_j phi_j(x)`.

For a missing declared exception term `e(x)`, define anchor residuals on eligible discovery clients only:

`r = y - f_S(x)`.

The restricted coefficient is estimated without modifying any `beta_j`:

`gamma = sum(e * r) / (sum(e^2) + 1e-10)`

where both sums are additive over role-eligible discovery clients only.

The augmented candidate is

`f_FCRRA(x) = f_S(x) + gamma e(x)`.

No intercept or shared coefficient is refit during the admission decision.

## 4. Role eligibility

Eligibility is computed independently for discovery and selector packets using the same declared support floor family already used by SCSV exception diagnostics:

`max(3, ceil(0.10 * local_support))`.

A client contributes to the residual coefficient only if its discovery support for `e` meets the discovery floor.

A client contributes to the role-local selector decision only if its selector support for `e` meets the selector floor.

Probe support is prohibited from coefficient estimation and admission.

If no eligible discovery client or no eligible selector client exists, the augmentation is rejected.

## 5. Selector-only admission

On eligible selector clients, compare the frozen anchor against the frozen-core augmented candidate using the existing SCSV information-score family:

`J = log(MSE) + complexity * log(N) / N`.

The augmentation passes iff

`J(FCRRA) < J(anchor)`.

No additional margin, multiplier, threshold, or tuned constant is allowed.

Because the exception basis is zero outside its declared role and the shared coefficients remain fixed, outside-domain predictions must be numerically identical to the frozen anchor. The implementation must assert absolute prediction/SSE differences outside the eligible role are at most `1e-10`.

## 6. Probe semantics

Only after selector admission, run the existing independent SCSV probe diagnostics on the augmented structural set. The probe is audit-only in this spent-seed diagnostic and cannot delete the exception or alter the shared anchor.

Report exception necessity, eligible probe clients, and outside-domain non-degradation, but do not use probe outcomes to tune the selector rule.

## 7. Diagnostic scope

The current independent benchmark has one declared restricted term:

`I(x3>1)*x3^2`.

This diagnostic is limited to that one exception mechanism. It does not establish a general multi-role or multi-exception algorithm.

## 8. Seeds and evidence firewall

Engineering smoke only:

- `22001`

Repository search before protocol freeze found no prior occurrence of `22001`.

Scientific diagnostic data:

- only already-spent independent seeds `20101`, `20102`, `20103`, `20104`, `20105`;
- exact same 590 independent conditions;
- frozen v6 historical rows from `results/scsv_v6_independent/rows.csv` are read-only comparators;
- sealed RCSA rows are read-only mechanistic comparators.

No fresh successor-validation seed may be consumed.

## 9. Diagnostic matrix

Exactly one FCRRA output per existing independent condition:

- Panel G: 300;
- Panel S: 270;
- Panel S32: 20;
- total: **590 rows**.

Non-exception conditions must be structurally and predictively identical to frozen v6.

## 10. Required endpoints

For each condition record:

- frozen v6 anchor structure;
- frozen anchor coefficients;
- exception present in bank;
- exception already selected;
- FCRRA attempted;
- eligible discovery clients/support;
- eligible selector clients/support;
- residual numerator `sum(e*r)`;
- residual denominator `sum(e^2)`;
- estimated `gamma`;
- anchor role-local information score;
- FCRRA role-local information score;
- outside-domain SSE/prediction maximum difference;
- augmentation accepted;
- final structure and coefficients;
- exact recovery;
- term precision/recall;
- test NMSE;
- exception recovery;
- probe certification and exception diagnostics;
- incremental communication/runtime, explicitly labelled diagnostic overhead.

## 11. Frozen mechanism-signal criteria

FCRRA is **FCRRA-MECHANISM-SIGNAL PASS** only if all criteria pass:

A. Candidate-bank exception identity matches frozen v6 for every condition.

B. Every non-exception condition remains exactly structurally identical to frozen v6.

C. Every exception condition where v6 already selected the exception remains unchanged.

D. Outside-domain predictions/SSE remain identical to the anchor within `1e-10` for every attempted augmentation.

E. Panel-S 4-client exception recovery is at least `0.90`.

F. Panel-S 8-client exception recovery is at least `0.90`.

G. Panel-S 16-client exception recovery is at least `0.9333`.

H. Panel-S32 exception recovery remains `1.0000`.

I. Overall exact recovery across all 590 conditions is at least frozen v6 exact recovery minus `0.01`.

J. Zero exact-recovery harms among conditions exact under frozen v6.

K. Zero non-exception spurious worsening versus frozen v6.

L. At least `7/13` previously observed missing-exception conditions are rescued.

M. At least one of the five `cubic_cross` 4-client imbalanced misses is rescued; a mechanism that rescues only easier non-Gate-N cases is insufficient.

Any failed criterion yields **FCRRA-MECHANISM-SIGNAL NO-GO**. No threshold adjustment, coefficient shrinkage selection, subgroup rescue, or repeated testing is permitted after seeing the spent-seed outcome.

## 12. Engineering smoke requirements

Before executing any `20101--20105` FCRRA diagnostic condition, seed `22001` only must verify:

- the wrapper calls frozen `scsv_cert_method`;
- shared anchor structure is never deleted/replaced;
- shared anchor coefficients are bitwise/numerically unchanged during FCRRA admission;
- `gamma` uses eligible discovery residual sufficient statistics only;
- selector decision uses eligible selector packets only;
- probe packets do not affect estimation or admission;
- outside-role predictions are identical within `1e-10`;
- no-exception condition returns frozen v6 exactly;
- already-selected exception remains unchanged;
- an omitted banked exception can be evaluated within the size cap;
- smoke output contains only seed `22001`;
- mechanism criteria A--M are not evaluated in smoke mode.

Only engineering bugs may be repaired after this freeze. The scientific FCRRA rule and criteria A--M become immutable once any spent-seed FCRRA scientific result is computed.

## 13. Promotion boundary

A PASS would support only the mechanistic proposition that residual-only role-local coefficient estimation is a promising repair for the retained v6 low-client exception failure. It would authorize design of a separately named successor algorithm and a new preregistered validation protocol using genuinely fresh seeds.

It would not convert SCSV-Cert v6 to independent GO, would not erase RCSA NO-GO, and would not authorize retrospective SRSD execution.

A NO-GO retires this frozen-core residual augmentation formulation and retains the current v6 independent boundary.
