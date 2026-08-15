# SCSV spent-seed diagnostic authorization

Status: **authorized exploratory run; not v6 evidence**.

Pre-run requirements verified before this authorization:

- `research/TRANSACTIONS_SCSV_EXPLORATORY_PROTOCOL.md` is frozen;
- SCSV implementation and invariant tests are committed;
- dedicated engineering smoke seed `18001` passed;
- full repository regression CI passed;
- no fresh successor-development seed is authorized or referenced by the diagnostic workflow.

Authorized diagnostic seeds are only the already-spent HR-VFS v5 development seeds:

`17101, 17102, 17103, 17104, 17105`.

The diagnostic result must be labelled only `MECHANISM-SIGNAL` or `NO-MECHANISM-SIGNAL`. It is post-hoc exploratory evidence and must never be represented as a v6 GO/NO-GO result, independent validation, or confirmatory evidence.

A mechanism signal may justify freezing a separate v6 protocol with untouched seeds. A no-signal result freezes this SCSV variant as an unsuccessful exploratory mechanism.