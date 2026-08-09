# FCRRA post-diagnostic forensic analysis

Status: **FINAL POST-HOC FORENSIC ANALYSIS; FCRRA remains NO-GO**.

This document analyzes only already-spent evidence from the sealed SCSV-Cert v6 independent study and the sealed FCRRA spent-seed diagnostic. It does not reopen any frozen gate, does not convert v6 to independent GO, and does not authorize external SRSD execution.

## 1. Evidence identity

- Independent evidence run: `31314059069`.
- Independent evidence commit: `25fd323c54bfa49dfcd55f36f39d9f1305195eb8`.
- Independent seeds: `20101--20105` (spent).
- FCRRA run: `31327514970`.
- FCRRA authorization/source SHA: `80466ba54bcc1dccc0697615b8aa3b6c9ee56a8e`.
- FCRRA sealed evidence commit: `c63219f649dec90e6a0f4e459f525945016207e7`.
- FCRRA rows: `590`.
- FCRRA attempts: `13`.
- FCRRA accepts: `0`.
- Rescued exception misses: `0/13`.
- Exact-recovery harms: `0`.
- Maximum outside-role prediction difference: approximately `5.33e-15`.

The frozen FCRRA decision is therefore unchanged: **FCRRA-MECHANISM-SIGNAL-NO-GO**.

## 2. What FCRRA successfully isolated

FCRRA fixed the principal defect of RCSA: it did not globally refit the already-selected shared coefficients after proposing an exception. The shared selector-fit coefficients were frozen, and only one residual exception coefficient was estimated from role-eligible discovery sufficient statistics.

This achieved the intended invariance. Outside the exception role, the gated term is zero and predictions remained numerically identical to the frozen shared model. The outside-role identity gate passed.

Therefore the FCRRA failure is not caused by leakage into outside-role predictions.

## 3. Structural identifiability problem

The independent benchmark exception is

`e(x) = I(x3 > 1) * x3^2`

with catalog metadata

- kind: `exception`;
- source term: `x3^2`;
- symbolic complexity: `4`.

The independent exception generator makes the final client the role-eligible client and samples all of that client's `x3` values from `[1.05, 2.5]`. All other clients remain below the gate.

Consequently, within the eligible client,

`I(x3 > 1) * x3^2 = x3^2`

for every observation.

The exception basis and its source basis are therefore exactly collinear inside the eligible role. Local eligible data alone cannot identify a shared `x3^2` coefficient separately from an eligible-role deviation on `x3^2`.

Cross-client contrast is required: the non-eligible clients identify the shared source coefficient, while the eligible client identifies the deviation from that shared coefficient.

## 4. Evidence that the pooled shared slope absorbed the local deviation

Among the 13 frozen-v6 exception-selection misses:

- `12/13` frozen selector structures already contained the source term `x3^2`;
- one `cubic_cross`, four-client imbalanced condition (`seed 20103`) omitted `x3^2` and used `cos(x3)` as a surrogate;
- the FCRRA residual coefficient estimates ranged only from approximately `0.0532` to `0.5118`, while the generating exception coefficient is `0.75`.

Representative pooled discovery source coefficients were substantially above the generating shared source coefficient. For example, in several `cubic_cross` failures the frozen discovery `x3^2` coefficient was around `0.91`, even though the shared generating coefficient is `0.50`. In `nested_mixed` and `multi_quadratic`, pooled discovery source coefficients were approximately `1.20`, while the shared generating coefficient is `0.80`.

This is consistent with partial absorption of the role-specific `+0.75` deviation into the pooled shared slope before FCRRA computes an eligible residual.

## 5. Complexity penalty was secondary, not primary

FCRRA evaluated the augmented eligible-role candidate through the generic SCSV information profile. Because the exception expression has symbolic complexity `4`, the role-local selector pays the full structural complexity again even though the exception expression was already present in the high-recall candidate bank.

A post-hoc arithmetic check replaced that `+4` structural-complexity increment with a one-extra-parameter penalty while leaving the FCRRA coefficients unchanged. Only `1/13` attempted cases would have passed.

Therefore simply weakening or redefining the complexity penalty is not an adequate repair. The coefficient-identification problem remains primary.

## 6. Nested cross-client contrast diagnostic

A separate post-hoc calculation on the same spent conditions tested a different statistical question.

For a frozen v6 structure `S`, define a globally identified nested discovery model

`M1 = S + e`.

Fit `M1` from discovery sufficient statistics across all clients. Because `e=0` outside the eligible role, the non-eligible clients identify the shared source behavior while the eligible client provides information about the gated deviation.

Then define a **fixed-reduced conditional comparator** by setting only the fitted exception coefficient in `M1` to zero while leaving every fitted shared coefficient from `M1` unchanged.

This comparator asks whether the exception coefficient itself is necessary conditional on the same shared fit. It does not permit a reduced model to re-absorb the local deviation into a different shared coefficient vector.

Using a one-additional-parameter BIC-style held-out criterion,

`Delta = log(SSE_full / SSE_fixed_reduced) + log(N_role) / N_role`,

with no tuned numerical margin:

- all `13/13` frozen exception misses had `Delta < 0` on the selector split;
- all `13/13` also had `Delta < 0` on the disjoint probe split;
- the fitted nested exception coefficient was positive in all 13 exploratory cases and typically much closer to the generating deviation than the FCRRA residual coefficient;
- aggregate outside-role selector and probe SSE did not worsen in these 13 post-hoc cases.

These calculations are **exploratory spent-seed forensics only**. They cannot be used as confirmatory evidence and cannot override the v6 or FCRRA decisions.

## 7. Why the fixed-reduced test is scientifically different

RCSA compared two separately refitted models and then scored the eligible role. The reduced model could absorb part of the role effect into the shared coefficients.

FCRRA froze the pooled shared coefficients before estimating a local residual. By that point, part of the role effect had already been absorbed by the pooled source coefficient.

The fixed-reduced nested contrast instead:

1. identifies the shared and gated coefficients jointly from cross-client discovery information;
2. freezes that joint shared fit;
3. removes only the gated coefficient for the held-out necessity comparison;
4. evaluates selector and probe evidence without refitting the reduced comparator.

This is a conditional coefficient-deviation question rather than another greedy term-selection question.

## 8. Parent-source semantic boundary

A role-specific deviation is only semantically meaningful when the declared source term is part of the frozen shared structure.

Therefore a successor diagnostic should not force an orphan gated deviation when `catalog.get(exception).source_term` is absent from the frozen shared selector structure. The one `cubic_cross` seed-20103 case should remain untouched by a conservative role-deviation mechanism rather than being counted as evidence for a source coefficient that the shared selector did not retain.

This leaves 12 parent-identifiable exception misses available to test a role-contrast mechanism while preserving the original structural boundary.

## 9. Prior-art boundary

The global-plus-local parameterization itself must not be presented as a novel invention. Personalized federated learning and federated mixed-effects modeling already study shared models with client- or group-specific deviations.

Any eventual novelty claim must instead be scoped to the combination of:

- finite symbolic structural discovery;
- declared source/exception relationships;
- cross-client identifiability of a gated coefficient deviation;
- selector/probe-separated conditional necessity certification;
- privacy-compatible sufficient-statistic messages;
- explicit falsification and NO-GO governance.

Relevant prior-art anchors include federated generalized mixed-effects modeling (Li et al., 2021, arXiv:2109.14046) and personalized federated model-adaptation work such as pFedGate (Chen et al., ICML 2023).

## 10. Correct successor action

Do not tune FCRRA, relax its gates, or reuse it under another name.

The justified next exploratory mechanism is a separately named **Role-Contrast Conditional Deviation (RCCD)** diagnostic using only already-spent seeds `20101--20105` plus a new engineering-only smoke seed. RCCD must preserve the frozen v6 structure and candidate bank, require the exception source term to be present in the shared anchor, fit a nested shared-plus-deviation model on discovery packets, and certify the single deviation parameter on disjoint selector and probe packets using a one-degree-of-freedom conditional necessity test.

Even a successful RCCD spent-seed signal would not be v7 evidence. A fresh successor protocol and genuinely untouched seeds would still be required.