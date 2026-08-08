# RC-DES v4 evidence execution authorization

Status: **AUTHORIZED FOR ONE FROZEN DEVELOPMENT EXECUTION**

Authorization date: 2026-08-08

## Preconditions satisfied

- The v3 study is permanently recorded as NO-GO.
- The v3 forensic analysis and v4 motivation were written before v4 evidence execution.
- `TRANSACTIONS_ROLE_CONDITIONAL_V4_PROTOCOL.md` was frozen before v4 evidence execution.
- `TRANSACTIONS_ROLE_CONDITIONAL_V4_IMPLEMENTATION_CLARIFICATION.md` was frozen before engineering smoke and v4 evidence execution.
- Unit tests for role-conditioned candidate admission, path persistence, restricted-exception eligibility, seed isolation, and structural budgets passed.
- CI run `31262990545` completed successfully, including the dedicated `Role-conditioned v4 engineering smoke test`.
- Engineering smoke used only seed `16001`; this seed is permanently excluded from evidence.
- No development seed `16101--16105` has been inspected through the full v4 evidence path before this authorization.
- Final-confirmation seeds `11001+` remain untouched.
- The evidence workflow is pinned to the triggering commit SHA, audits 4,500 rows / 450 matched conditions / ten methods, seals source and output SHA-256 digests, and uploads the artifact before attempting a repository commit.

## Frozen execution

The only permitted primary v4 development seeds are:

`16101, 16102, 16103, 16104, 16105`.

The full matrix is:

- five benchmarks;
- three scenarios;
- three noise ratios;
- two samples-per-client levels;
- five development seeds;
- ten preregistered methods/ablations;
- 450 matched conditions;
- 4,500 retained method rows.

All thirteen preregistered v4 gate criteria are evaluated together. Failure of any criterion is a NO-GO.

## Governance after this commit

Once the evidence workflow begins, the v4 algorithm, evidence-channel rules, selector/probe thresholds, role definitions, ranking, endpoints, matrix, and go/no-go criteria are immutable for this study.

Seeds `16101--16105` become spent development seeds. They may not be selectively replaced, rerun after outcome-driven tuning, or described as independent replications of themselves.

A positive v4 development result would permit only independent external validation and scalability work. It would not establish Transactions readiness, universal superiority, catalog-free discovery, causality, or formal privacy.
