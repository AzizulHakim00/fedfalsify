# Phase 3 Pre-Implementation Self-Review

**Date:** 2026-09-06  
**Reviewed specification:** `docs/superpowers/specs/2026-09-06-scsv-ncsc-phase3-final-candidate.md`  
**Related documents:** `research/PHASE3_NOVELTY_AUDIT.md`, `research/PHASE3_THEORY_SKETCH.md`  
**Decision:** READY FOR HUMAN SPEC REVIEW; NOT READY FOR IMPLEMENTATION UNTIL HUMAN APPROVAL

## 1. Corrections completed before this review

The final-candidate specification corrects the earlier Phase-3 drafts in the following material ways:

1. exact predecessor shared capacity is restored to `6` total shared terms including intercept, therefore at most `5` non-intercept terms;
2. final structural multiplicity control uses Holm/FWER rather than making a fragile post-filter FDR claim;
3. Discovery, Selector, and Probe have separate scientific roles;
4. shared candidates are nominated on Discovery and independently certified on Selector;
5. final localized p-values are computed only on untouched Probe;
6. localized tests use proper partial nested models that re-estimate nuisance shared coefficients instead of testing against transported fixed coefficients;
7. the shared term set, not a cross-split coefficient vector, is the structural reference for nested testing;
8. exact rank ambiguity causes abstention rather than tuned ridge regularization;
9. the inherited outside-role numerical tolerance is pinned to `1e-10` from the predecessor implementation;
10. the active-row guard is explicitly described as a new prospective engineering guard, not falsely labeled mathematically identical to the old fold rule;
11. Phase 3A refactor/parity is separated from Phase 3B scientific modification;
12. the novelty claim is narrowed after identifying existing federated SR, multitask shared/task-specific SR, noise-robust SR, Bayesian/UQ SR, and a 2025 selective-inference SR technical report.

## 2. Internal consistency review

### Data-use sequence

PASS.

- Discovery nominates candidates.
- Selector certifies shared structure.
- Discovery constructs localized roles conditional on shared structure.
- Selector performs non-final role/safety screening.
- Probe performs the final localized hypothesis test.

No Probe feedback is permitted into candidate, role, sign, shared-structure, or family construction.

### Structural test definition

PASS.

FULL and REDUCED are nested term-set models evaluated on the same client scope. Nuisance shared coefficients are re-estimated within each evaluation partition. FULL must increase effective rank by exactly one.

### Multiplicity

PASS.

- Selector shared family: Holm `0.05`.
- Discovery role construction: BH `0.10`, exploratory only.
- Probe localized family: Holm `0.05`.

Final accepted localized hypotheses must be a subset of Holm rejections, preserving the FWER event bound under deterministic post-Holm filtering.

### Shared capacity

PASS.

Frozen v6 semantics are correctly represented as maximum `6` total shared terms including intercept.

### Seed firewall

PASS.

- `29101--29105` spent;
- `29201--29205` spent;
- `29300` engineering only;
- `29301--29310` untouched fresh development;
- `11001+` untouched final confirmation.

No current document authorizes fresh development.

## 3. Scientific assumptions that remain explicit

These are not specification bugs; they are claim boundaries that must remain visible.

### Synthetic-noise calibration

The classical F tests are aligned with the frozen benchmark because the generator applies independent homoskedastic Gaussian noise with one condition-level noise standard deviation.

The same exact calibration must not be claimed automatically on real data.

### Shared-scope interpretation

SCR tests a common-coefficient ordinary term in the pooled joint model. This is evidence for a shared pooled structural component, not a theorem that every individual client has identical finite-sample effect estimates.

The development study must report false shared terms and shared precision/recall explicitly. If shared false positives remain material, the next forensic analysis should investigate cross-client heterogeneity rather than silently adding a breadth threshold after seeing fresh outcomes.

### Exploratory role BH

BH role membership is hypothesis construction, not final confirmation. No client-level inferential claim should be written from that stage alone.

### External heterogeneity

Heteroskedastic, dependent, or heavy-tailed external data may require robust covariance, permutation, or bootstrap inference. Such an extension is outside the frozen synthetic Phase-3 primary method and requires a separate external-validation protocol.

## 4. Novelty risks still open

The focused audit discovered a 2025 IEICE technical report titled *Selective Inference for Symbolic Regression using Genetic Programming*. The available index states that it is a non-peer-reviewed technical report and a polished version is expected elsewhere.

Before manuscript submission, the full report and any later publication must be obtained and compared in detail.

Until then, the manuscript must not claim:

- first inferential SR;
- first selective-inference SR;
- first federated SR;
- first shared/task-specific SR;
- first noise-robust SR;
- first uncertainty-aware SR.

The current novelty target is the specific combination of federated set-conditional scope decomposition, sequential independent structural certification, family-wise control, additive sufficient-statistic equivalence, and outside-role safety.

## 5. Gate review

The prospective Phase-3 gate is intentionally harder than the predecessor result and is frozen before fresh development.

No gate is guaranteed to pass. A NO-GO is a valid scientific outcome.

The gate must not be altered after `29301--29310` are used.

## 6. Placeholder / ambiguity scan

PASS.

The final-candidate specification contains no `TODO`, `TBD`, result-dependent threshold placeholder, unspecified seed namespace, or undefined final-confirmation authorization.

The implementation plan must define exact function/type interfaces and test commands; those belong in the plan, not this scientific specification.

## 7. Recommendation

Proceed to human review of the three-document package:

1. final-candidate specification;
2. novelty audit;
3. theory sketch.

If the human approves this package, the next step is **implementation planning only**. The implementation plan must begin with Phase 3A refactor/parity and must not write or execute a fresh-seed runner.

No scientific implementation or seed spending is authorized by this self-review.
