# RCCD engineering smoke authorization

Status: **AUTHORIZED FOR ENGINEERING SMOKE ONLY**.

This authorization permits execution of the frozen Role-Contrast Conditional Deviation (RCCD) engineering smoke using only seed `23001`.

## Frozen prerequisites

- FCRRA post-diagnostic forensics are preserved.
- RCCD spent-seed diagnostic protocol is frozen.
- The initial RCCD engineering seed proposal `22001` was corrected to `23001` before any RCCD execution because `22001` had already been used by FCRRA smoke.
- RCCD implementation, spent-study harness, invariant tests, guarded smoke workflow, and guarded spent workflow are committed.
- Frozen SCSV-Cert v6 source hash remains `f56a38da25a60752b5580e449a7213e88ef6d7a6006759272274331e5ff174fb`.
- Historical independent rows remain the Git blob `92f25b499bc77499ad924e14d26feb95031b82f8` from evidence commit `25fd323c54bfa49dfcd55f36f39d9f1305195eb8`.

## Authorized execution

- engineering seed: only `23001`;
- formal spent seeds `20101--20105`: **not authorized by this file**;
- no fresh successor/v7 seed is authorized;
- smoke mechanism-signal criteria A--P must remain unevaluated;
- smoke may test only engineering invariants, source-link semantics, fixed-reduced coefficient identity, selector/probe isolation, outside-role safety plumbing, and bounded execution.

Formal RCCD spent execution requires a separate authorization only after this smoke and the full repository regression suite both pass.