# Role-Contrast Conditional Deviation (RCCD) spent-seed diagnostic protocol

Status: **FROZEN AFTER FCRRA FORENSICS AND BEFORE ANY FORMAL RCCD RUN**.

RCCD is a post-independent, post-FCRRA mechanism diagnostic. It is **not v7 evidence**, does not reopen the SCSV-Cert v6 independent NO-GO, and cannot authorize external SRSD confirmation by itself.

## 1. Scientific question

The sealed FCRRA analysis established that the restricted exception

`I(x3 > 1) * x3^2`

is exactly collinear with its source term `x3^2` inside the eligible client. FCRRA froze a pooled shared source coefficient before estimating an eligible residual, allowing the pooled coefficient to absorb part of the local deviation.

RCCD asks a narrower question:

> When a declared, banked exception has a source term already present in the frozen v6 shared structure, can the shared source coefficient and its role-specific deviation be jointly identified from cross-client discovery statistics and then independently certified as one additional deviation parameter on selector and probe data?

## 2. Causal isolation boundary

RCCD must call the frozen `scsv_cert_method` unchanged and treat its **selected term set** as the shared structural anchor.

RCCD may not delete or replace any term already selected by v6.

RCCD may consider exactly one declared exception term only when all conditions hold:

1. the exception is already in the frozen v6 high-recall candidate bank;
2. the exception is absent from the frozen v6 selector structure;
3. `catalog.get(exception).source_term` is non-null;
4. that source term is already present in the frozen v6 selector structure;
5. adding the exception does not exceed six terms including the intercept.

If any condition fails, RCCD must return the frozen v6 structure unchanged.

The current independent grammar contains one exception term, `I(x3>1)*x3^2`, whose source term is `x3^2`.

## 3. Discovery-stage nested identification

Let `S` be the frozen v6 selector structure and `e` the eligible banked exception.

Using the same discovery sufficient-statistic packets as SCSV, fit the nested model

`M_full = S + e`

across **all clients**.

This global discovery fit is required for identifiability. Outside-role clients, where `e=0`, identify the shared source coefficient. The eligible client contributes information about the source-plus-deviation coefficient.

No truth labels, test rows, selector rows, or probe rows may enter this fit.

## 4. Fixed-reduced conditional comparator

After fitting `M_full`, construct

`M_zero`

by copying every fitted coefficient from `M_full` and setting **only the exception coefficient to zero**.

Do not refit `M_zero`.

This fixed-reduced comparator is essential. It asks whether the exception coefficient itself contributes held-out evidence conditional on the same fitted shared coefficient vector. A separately refitted reduced model is prohibited because it can re-absorb the role deviation into the shared source coefficient.

## 5. Role eligibility

Role eligibility is determined independently on each held-out split from observed support of the exception term using the inherited floor

`max(3, ceil(0.10 * local_support))`.

For the selector decision, only selector support may determine selector eligibility.

For probe certification, only probe support may determine probe eligibility.

Discovery eligibility is recorded for diagnostics but may not substitute for held-out eligibility.

## 6. One-degree-of-freedom conditional information test

The symbolic exception expression has already been discovered into the candidate bank. RCCD therefore tests whether **one additional coefficient deviation** is supported, not whether the full symbolic expression should be rediscovered.

For a held-out split with eligible support `N_role`, compute eligible-role SSE for `M_full` and `M_zero` and define

`Delta = log(SSE_full / SSE_zero) + log(N_role) / N_role`.

The split passes iff

`Delta < 0`.

This is a one-additional-parameter BIC-style criterion. No extra margin, p-value threshold, effect-size threshold, or tuned constant is allowed.

If no eligible client exists on a split, that split fails.

## 7. Selector and probe separation

RCCD acceptance requires **both**:

1. selector `Delta < 0`;
2. independent probe `Delta < 0`.

The full candidate and its coefficients are fit from discovery packets only. Selector and probe packets are used only to evaluate the frozen full-versus-fixed-reduced contrast. No refit occurs after seeing selector or probe evidence for purposes of the decision.

## 8. Outside-role safety

Because fitting `M_full` jointly may alter shared coefficients relative to the original v6 anchor, RCCD must separately verify outside-role predictive safety.

On both selector and probe splits:

- compare aggregate SSE over clients not eligible for the exception;
- `M_full` must have aggregate outside-role SSE no larger than the original frozen-v6 discovery anchor, up to numerical tolerance `1e-10`.

This is an aggregate client-role safety condition. Per-client outside nondegradation is recorded descriptively but is not a frozen acceptance gate.

## 9. Acceptance and operational structure

RCCD accepts the exception iff all are true:

- bank/source/size prerequisites pass;
- selector conditional test passes;
- probe conditional test passes;
- selector outside-role aggregate safety passes;
- probe outside-role aggregate safety passes.

If accepted, the operational structure is exactly `S + e`.

If rejected or ineligible, the operational structure is exactly `S`.

No core term can be removed or replaced.

For post-decision test evaluation, coefficients may be refit on the complete training client data only after the structure is fixed. The independent synthetic test generator remains untouched and is never used for selection or certification.

## 10. Evidence and seed boundary

Engineering-only smoke seed:

- `23001`

The initial protocol draft proposed `22001`, but implementation inspection before any RCCD execution showed that `22001` had already been used as the FCRRA engineering smoke seed. The RCCD engineering seed was therefore corrected to `23001` before any RCCD smoke or formal diagnostic run. No scientific RCCD result was consumed before this correction.

Formal RCCD diagnostic data:

- only already-spent independent seeds `20101`, `20102`, `20103`, `20104`, `20105`;
- exactly the frozen 590 independent conditions;
- historical comparator rows from `results/scsv_v6_independent/rows.csv`;
- no fresh successor/v7 seed may be consumed.

The engineering seed must never appear in the formal spent diagnostic.

## 11. Formal diagnostic matrix

One RCCD output is produced for each frozen independent condition:

- Panel G: 300;
- Panel S: 270;
- Panel S32: 20.

Total RCCD rows: **590**.

No method grid or extra benchmark search is allowed.

## 12. Required row-level diagnostics

Every RCCD row must record at least:

- frozen v6 anchor structure;
- frozen candidate bank terms;
- exception term and declared source term;
- exception in bank;
- exception in anchor;
- source in anchor;
- RCCD attempted;
- discovery full structure and coefficients;
- fitted exception coefficient;
- selector eligible clients/support;
- selector `SSE_full`, `SSE_zero`, and `Delta`;
- probe eligible clients/support;
- probe `SSE_full`, `SSE_zero`, and `Delta`;
- selector outside-role anchor/full SSE;
- probe outside-role anchor/full SSE;
- selector/probe acceptance flags;
- final structure;
- exact recovery;
- term precision/recall;
- exception recovery;
- test NMSE;
- unoptimized diagnostic runtime and communication overhead.

## 13. Frozen mechanism-signal criteria

RCCD receives **RCCD-MECHANISM-SIGNAL PASS** only if every criterion passes.

A. The rerun frozen-v6 anchor and bank match the sealed historical v6 condition-matched reference.

B. Every non-exception condition remains structurally identical to frozen v6.

C. Every exception condition where frozen v6 already selected the exception remains structurally identical to frozen v6.

D. RCCD attempts only missing banked exceptions whose declared source term is already in the frozen shared anchor; no orphan deviation is admitted.

E. Every RCCD-accepted deviation passes the frozen selector one-parameter conditional criterion.

F. Every RCCD-accepted deviation passes the independent probe one-parameter conditional criterion.

G. Every RCCD-accepted deviation satisfies aggregate outside-role nondegradation on both selector and probe.

H. Panel-S four-client exception recovery is at least `0.90` (frozen v6: `0.80`).

I. Panel-S eight-client exception recovery is at least `0.90` (frozen v6: `0.90`).

J. Panel-S sixteen-client exception recovery is at least `0.9333` (frozen v6: `0.9333`).

K. Panel-S32 exception recovery remains `1.00`.

L. Across all 590 conditions, RCCD exact recovery is at least frozen v6 exact recovery minus `0.01`.

M. RCCD creates zero exact-recovery harms among conditions exact under frozen v6.

N. Non-exception spurious acceptance is not worse than the condition-matched frozen-v6 value; by construction non-exception structures should be identical.

O. At least `7/13` previously observed frozen-v6 exception-selection misses are rescued.

P. At least one of the five hard `cubic_cross`, Panel-S, four-client, imbalanced exception misses is rescued without deleting a frozen core term.

Any failed criterion yields **RCCD-MECHANISM-SIGNAL-NO-GO**.

No criterion may be relaxed after formal RCCD rows are generated.

## 14. Engineering smoke requirements

Before formal spent execution, seed `23001` only must verify:

- the wrapper calls frozen `scsv_cert_method`;
- non-exception structures are unchanged;
- already-selected exceptions are unchanged;
- source-term absence prevents an orphan deviation;
- full and fixed-reduced candidates share exactly the same fitted shared coefficients;
- the fixed-reduced candidate differs only by setting the exception coefficient to zero;
- selector and probe eligibility are computed independently;
- selector `Delta` never reads probe packets;
- probe `Delta` never refits coefficients;
- the information penalty is exactly one extra parameter;
- outside-role safety is evaluated against the frozen v6 discovery anchor;
- no core term is deleted or replaced;
- smoke output uses only `23001`;
- A--P mechanism-signal criteria are not evaluated in smoke mode.

Only engineering defects may be repaired after this freeze. Scientific rules, criteria, and the spent matrix may not change after formal RCCD output is consumed.

## 15. Promotion boundary

A spent-seed RCCD PASS would establish only a **mechanism signal** for a source-linked role-deviation certificate.

It would authorize drafting a separately versioned successor protocol with genuinely fresh seeds. It would not:

- convert SCSV-Cert v6 to independent GO;
- make RCCD confirmatory evidence;
- authorize retrospective SRSD confirmation;
- justify a novelty claim before broader prior-art analysis.

A NO-GO retires this RCCD formulation and retains the existing independent failure boundary.