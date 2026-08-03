# Transactions Implementation Status

This file tracks implementation state only. It does not declare the work ready for submission.

## Frozen evidence

- Study A run ID: `v06-primary-confirmatory`
- Verified method-runs: `2400`
- Frozen seeds: `9001--9020`
- Evidence commit: `02613c79f88210d37ad1705954207283c03894b3`
- Status: complete, hash-verified, and not eligible for retuning

## Phase 1: semantic-equivalence and failure analysis

Implemented:

- safe evaluation of archived equations;
- interpolation, client-support, mild-extrapolation, and strong-extrapolation domains;
- strict and relaxed semantic thresholds;
- threshold sensitivity at `1e-4`, `1e-3`, and `1e-2`;
- expression complexity;
- duplicate-row checks;
- 40-failure taxonomy for frozen FedFalsify outcomes;
- Unicode and ASCII exception-indicator parsing;
- result-manifest workflow for archived Phase 1 evidence.

Submission gate:

- all 2400 archived equations must parse;
- the final Phase 1 result files must be hash-sealed;
- strict and semantic conclusions must be reported separately.

## Phase 2: controlled ablations

Implemented runner variants:

- full FedFalsify;
- no coefficient-heterogeneity certificate;
- no client-validated replacement;
- no client non-degradation constraint;
- score-only federated search;
- centralized catalog-matched search;
- local-client consensus;
- no exception module.

Governance:

- frozen seeds `9001--9020` are rejected by code;
- development defaults begin at seed `10001`;
- failed runs remain in the analysis;
- raw and Holm-corrected summaries are written separately.

## Remaining mandatory Transactions work

1. Execute and archive Phase 1 full semantic results.
2. Execute full ablations on development and validation seeds.
3. Add equal-budget official PySR and at least one additional maintained SR system.
4. Add adaptive-catalog and catalog-misspecification experiments.
5. Add client, feature, noise, imbalance, overlap, and exception-prevalence stress studies.
6. Add at least two external scientific datasets; three are preferred.
7. Complete formal shortcut-rejection and invariant-retention results.
8. Freeze and execute a new independent confirmation on untouched seeds beginning at `11001`.
9. Prepare a hierarchical statistical analysis over seeds and benchmark families.
10. Write the paper only after the empirical and theoretical claim matrix is complete.

## Current submission decision

`NO-GO` for a Q1 Transactions submission at this stage.

The frozen result is a strong foundation, but official-baseline fairness, semantic analysis, ablations, external validation, scalability, and theory remain required.
