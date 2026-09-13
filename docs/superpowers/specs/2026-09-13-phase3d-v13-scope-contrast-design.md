# FedFalsify Phase-3D / v13 Scope-Contrast Fixture Proof — Design Specification

Date: 2026-09-13
Status: Design freeze candidate for human review
Branch: `research/phase3d-v13-scope-contrast-design`

## 1. Purpose

Phase-3C falsified v12/SCSV-NCSC for the intended heterogeneous structural-recovery claim. The dominant failure was architectural: source-linked localized terms are often locally rank-collinear with their shared source term inside role clients, while pooled shared-core recertification can absorb localized heterogeneity into false ordinary global terms.

Phase-3D is therefore a **zero-new-scientific-seed architectural admissibility study**. It must prove, on deterministic/noiseless fixtures, that a replacement architecture can simultaneously recover:

- a globally shared source term,
- an additional client-subset coefficient shift of that same source,
- the correct client scope,
- and null cases without inventing localized structure.

Phase-3D MUST NOT access Phase-3C development seeds `29301–29310`, the engineering seed `29300`, or final-confirmation seeds `11001–11999`.

## 2. Proposed Method

Working name: **FedFalsify v13 / SCSV-SCC** — Set-Conditional Structural Verification with Scope-Contrast Certification.

Model class:

\[
y = \sum_j \beta_j \phi_j(x) + \sum_m \delta_m I(c\in R_m)\phi_m(x) + \epsilon.
\]

For a source-linked localized effect, the architecture must retain both the shared source and the localized scope-shift term, e.g.

\[
\beta x_3^2 + \delta I(c\in R)x_3^2.
\]

The method MUST NOT require the scope-shift term to increase rank inside a single role client. Instead, identifiability is evaluated over a role-vs-outside scope contrast, where the scope regressor is zero outside the role and equals the source basis inside it.

## 3. Evidence Flow

The v13 proof architecture is:

1. Discovery candidate bank.
2. Source-protected provisional shared family.
3. Scope-contrast role discovery.
4. Freeze role identities.
5. Joint Selector model containing shared terms plus frozen scope-contrast terms.
6. Joint term-deletion structural tests.
7. Independent Probe confirmation.
8. Final shared + localized structure.

The failed serial dependency `SCR -> local NCEE` is not reused.

## 4. Statistical / Structural Rules

Phase-3D is a deterministic structural-admissibility proof, not a new performance study. The following v12 principles remain frozen unless explicitly overridden in this spec:

- Discovery / Selector / Probe separation remains.
- BH remains exploratory for role discovery where multiple candidate scopes are compared.
- Holm remains the final multiplicity control for Probe-confirmed structural decisions.
- Outside-scope safety remains mandatory.
- Deterministic rank policy remains mandatory.
- Shared non-intercept capacity remains 5.
- Localized capacity remains 2.
- Total final structural capacity remains 10.
- No threshold tuning is permitted using Phase-3C outcomes.

The scope-contrast structural test must compare a reduced model containing the shared source with a full model adding exactly one scope-contrast source-shift regressor. The relevant rank expansion is checked on the aggregated role+outside scope, not inside a single role client.

## 5. Deterministic / Noiseless Fixtures

No scientific RNG seeds are used. Inputs are fixed numeric grids chosen deterministically and stored in source/config. Responses are noiseless ground-truth functions.

Eight fixtures are required:

1. `quadratic_scope_shift`
   - shared: `x3^2`, `sin(x2)`, `x1`
   - localized: scope-linked shift of `x3^2`

2. `linear_scope_shift`
   - shared ordinary terms including `x1`
   - localized: scope-linked shift of `x1`

3. `trig_scope_shift`
   - shared ordinary terms including `cos(x2)`
   - localized: scope-linked shift of `cos(x2)`

4. `interaction_scope_shift`
   - shared ordinary terms including `x1*x2`
   - localized: scope-linked shift of `x1*x2`

5. `weak_source_scope_shift`
   - weak shared source plus stronger localized shift of the same source

6. `dual_scope_shift`
   - two distinct localized source-linked shifts on non-overlapping client scopes

7. `null_no_localized`
   - shared structure only, no localized mechanism

8. `anchor_contamination_null`
   - distribution/support heterogeneity but no localized coefficient shift

The primary must-pass fixture is the quadratic source-linked case:

\[
y = 0.86x_3^2 + 0.72\sin(x_2) + 0.56x_1 + 0.70I(c\in R)x_3^2.
\]

The method must recover both shared `x3^2` and localized `I(c\in R)x3^2` with exact scope `R`.

## 6. Model Registry

Phase-3D runs exactly four models on every fixture/fold unit:

1. `v11-frozen`
2. `v12-frozen`
3. `scope-contrast-only`
4. `v13-full`

Purpose:

- `v11-frozen`: strong predecessor comparator.
- `v12-frozen`: reproduces the known failure geometry.
- `scope-contrast-only`: isolates whether role-vs-outside contrast fixes localized identifiability.
- `v13-full`: tests scope contrast plus heterogeneity-aware joint shared/local recertification.

## 7. Work Unit and Resume Semantics

The atomic persistence unit is:

`fixture × model × outer_fold`

Phase-3D initially uses `OUTER_FOLDS = (0,)` because deterministic fixture proof does not require artificial cross-validation. The runner interface must nevertheless support additional outer folds later without changing checkpoint semantics.

Each work unit is complete only after all required result and diagnostic payloads for that unit are generated and atomically persisted.

If Colab disconnects during a unit:

- already completed verified units are skipped,
- the incomplete unit is rerun,
- later untouched units remain pending,
- no completed unit is recomputed unless its hash/integrity check fails.

## 8. Google Drive Layout

Root:

`/content/drive/MyDrive/FedFalsify_Q1/PHASE3D_V13_SCOPE_CONTRAST_FIXTURES/`

Required layout:

- `config/frozen_config.json`
- `config/source_provenance.json`
- `config/environment.json`
- `units/<fixture>/<model>/fold_<NNN>.json`
- `checkpoint_index.csv`
- `phase3d_results.csv`
- `phase3d_results.pkl`
- `phase3d_results.joblib`
- `phase3d_diagnostics.csv`
- `phase3d_scope_diagnostics.csv`
- `phase3d_summary.csv`
- `phase3d_integrity.json`
- `phase3d_manifest_sha256.txt`
- `FedFalsify_PHASE3D_V13_FIXTURES.zip`

Every unit write must use temp-file + flush/fsync where practical + atomic `os.replace()`.

## 9. Reproducibility Requirements

The notebook/runner records:

- base repository commit,
- v13 implementation commit,
- Python version,
- numpy/scipy/pandas/joblib/pytest versions,
- exact fixture definitions and coefficients,
- exact role client identities,
- model registry,
- outer-fold registry,
- configuration SHA256,
- source/protocol SHA256 values,
- unit-level SHA256 hashes,
- final manifest SHA256 hashes.

Final state must be saved as human-readable CSV/JSON plus PKL/joblib plus a governed ZIP archive.

## 10. Shell / Live Output Requirements

The one-cell Colab wrapper must print organized banners and live progress. For each unit it prints:

- global unit index / total,
- fixture,
- model,
- fold,
- `RUN`, `SKIP`, or `RERUN-CORRUPT`,
- elapsed time,
- immediate save confirmation,
- checkpoint count.

Final output must print summary, integrity verdict, ZIP path, and ZIP SHA256.

## 11. Test-Driven Implementation Requirements

Before implementation, tests must be written for:

- deterministic fixture construction,
- no scientific-seed access,
- scope-contrast rank expansion with shared source retained,
- correct quadratic exact recovery,
- null rejection of localized false positives,
- dual-scope support,
- unit-level atomic persistence,
- resume skip of complete units,
- rerun of incomplete/corrupt unit only,
- CSV/PKL/joblib state equivalence,
- manifest verification,
- one-cell wrapper generation and fail-closed source/config checks.

## 12. Phase-3D Pass Criteria

Phase-3D is an architectural admissibility gate. It passes only if:

- shared + localized source-linked terms are simultaneously recoverable,
- exact client scope is recovered in quadratic, linear, trig, interaction, weak-source, and dual fixtures,
- null fixtures accept zero localized mechanisms,
- valid source-linked scope contrasts are not rejected merely because of within-role local collinearity,
- outputs are deterministic across reruns,
- resume integrity is clean,
- no scientific development/final seed is accessed,
- all repository tests and Phase-3D focused tests pass.

Failure of any must-pass structural fixture is a Phase-3D NO-GO; no fresh scientific seed block is allocated.

## 13. Non-Goals

Phase-3D does not:

- claim statistical superiority,
- tune thresholds using Phase-3C outcomes,
- run new development seeds,
- run final-confirmation seeds,
- benchmark external SR libraries,
- perform real-data validation,
- replace final development/final-confirmation studies.

## 14. Implementation Deliverables After Spec Approval

After human approval of this written spec:

- implementation plan,
- new v13 scope-contrast modules,
- deterministic fixture module,
- TDD test suite,
- resume-safe Phase-3D runner,
- one-cell Colab builder,
- checked-in generated `.ipynb`,
- downloadable `.ipynb` and `.py` copies for the user,
- CI evidence before any claim of readiness.
