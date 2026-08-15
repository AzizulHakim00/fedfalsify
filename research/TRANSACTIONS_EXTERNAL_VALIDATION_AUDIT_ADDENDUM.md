# External validation measurement-audit addendum

This addendum is intentionally separate from the preregistered external protocol.
It records measurement defects found during execution and the exact admissibility
repairs. It does not redefine the five SRSD problems, client partitions, methods,
budgets, or seeds after observing method rankings.

## Beijing study

The Beijing study completed successfully in workflow `30860646170`. No dataset,
station, method, or endpoint repair was required after result inspection. The
artifact `external-beijing-v1` is the immutable admissible evidence.

## SRSD attempt history

### Schema attempt

Workflow `30860646170` failed before a complete SRSD matrix because provisional
problem dimensions did not match two official files. No complete five-problem
result was produced. The correction used the official file schemas and treated
fixed physical constants as fitted scalar coefficients.

### V2 target-scale audit

Workflow `30861162857` completed, but audit found that absolute numerical floors
in target standardization and NMSE could collapse tiny yet nonconstant physical
targets toward zero. The artifact is retained as diagnostic and is not used for
scientific claims.

Repair:

- two-pass training-client aggregate variance;
- no absolute magnitude floor for nonconstant inputs or targets;
- NMSE divided by observed target variance without a fixed `1e-12` floor.

### V3 structural and unit audit

Workflow `30861771502` fixed target scaling and enforced one identifiable named
truth representation. It then exposed a remaining fairness issue: finite basis
columns were evaluated in physical units spanning many orders of magnitude.
Ridge regularization and score thresholds were therefore unit-sensitive. The v3
artifact is retained as diagnostic and is not used for final claims.

### V4 final admissibility repair

Workflow `30862392893` added training-only centering and scaling for every
nonconstant finite-catalog basis column. This repair:

- preserves each term name and structural identity;
- uses training clients only;
- changes numerical conditioning, not the problem definition;
- leaves PySR inputs, problem list, official splits, quartile clients, nuisance
  variables, finite methods, PySR budget, and external seeds unchanged.

V4 passed pre-run unit tests and post-run evidence checks. Its artifact
`external-srsd-v4`, ID `8874930076`, digest
`sha256:5ff59b002458a9cd439c105757bebf579d836a361b4aac80f43e3956a7af4c8b`,
is the sole admissible SRSD evidence used in the PR findings.

## Governance consequence

The audit sequence is itself a research result: scientific symbolic-regression
comparisons are highly sensitive to file schema, target magnitude, algebraic
aliases, and basis units. Future external studies must perform all four audits
before a measured model run:

1. official file-schema verification;
2. scale-aware target normalization;
3. unique structural truth representation;
4. training-only basis-column normalization.

No predecessor result was deleted, silently repaired, or used selectively.
