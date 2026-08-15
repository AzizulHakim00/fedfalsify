# SCSV-RCEF v9 fresh-development authorization

This document authorizes exactly one frozen fresh-development execution of FedFalsify v9 / SCSV-RCEF.

## Scientific freeze

The canonical protocol is `research/TRANSACTIONS_SCSV_RCEF_V9_PROTOCOL.md`. The A--W development gates, benchmark matrix, finite grammar, role thresholds, source-qualification rule, cross-view evidence-fusion rule, ambiguity guards, method list, and seed namespace are frozen.

No scientific rule may be changed after this authorization exposes a fresh development seed.

## Pre-evidence provenance

- implementation-equivalent engineering state: `93bbf454e6eea07ebb5604b40842bc83407aff69`
- corrected hardened v9 smoke run: `31435354261` -- SUCCESS
- corrected hardened smoke artifact: `scsv-rcef-v9-engineering-smoke`
- smoke artifact ID: `9080822760`
- smoke artifact digest: `sha256:254b047a668233f9c890d17c8f98023812b47dba995eb3c8ce55ac54ede52d0f`
- full repository regression run: `31435357739` -- SUCCESS
- historical v8 sealed evidence commit: `a80477308f84c93e02108ff0e9528613f9561f90`

The hardened forced-path suite passed before this authorization and covers response-free role proposal, source qualification pass/fail, pooled held-out evidence, contradiction veto, fixed-pair invariants, null metadata, and ambiguity guards.

The earlier hardened engineering run that failed did so only because of two test-fixture issues; no fresh seed had been exposed. Those fixtures were corrected without changing the frozen v9 algorithm, protocol, matrix, thresholds, or A--W gates.

## Fresh seed release

The following seeds are released exactly once for the preregistered 600-condition development matrix:

- `26101`
- `26102`
- `26103`
- `26104`
- `26105`

Engineering seed `26001` is forbidden from the fresh matrix.

Once the fresh workflow starts, all five `261xx` seeds are permanently spent regardless of technical or scientific outcome.

## Required matrix and decision

The workflow must produce exactly:

- `600` matched scientific conditions;
- `6` frozen methods per condition;
- `3600` rows;
- automatic A--W evaluation;
- `DEVELOPMENT-GO` only if every A--W criterion passes;
- otherwise `DEVELOPMENT-NO-GO`.

The sealed artifact must be uploaded before repository evidence is committed.

## Historical boundary

- v6 independent remains `INDEPENDENT-NO-GO`;
- v7 development remains `DEVELOPMENT-NO-GO`;
- v8 development remains `DEVELOPMENT-NO-GO`;
- no v9 result may relabel any historical outcome;
- a v9 development GO would authorize only a separately frozen independent-v9 validation using a new untouched seed namespace;
- external SRSD remains blocked until independent validation succeeds.