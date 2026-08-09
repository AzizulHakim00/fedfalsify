# RCCD spent-seed diagnostic authorization

Status: **AUTHORIZED FOR POST-INDEPENDENT SPENT-SEED DIAGNOSTIC ONLY**.

This file releases only the already-spent independent seeds `20101--20105` for the frozen Role-Contrast Conditional Deviation (RCCD) mechanism diagnostic. It does not authorize fresh successor/v7 evidence or external SRSD confirmation.

## 1. Frozen scientific prerequisites

- SCSV-Cert v6 independent evidence remains final NO-GO because frozen Gate N failed.
- Historical independent evidence commit: `25fd323c54bfa49dfcd55f36f39d9f1305195eb8`.
- Historical independent rows Git blob: `92f25b499bc77499ad924e14d26feb95031b82f8`.
- Historical pre-commit rows SHA-256: `6462f268775ae7c52595e3a87c0b56e70e65745aca66df1e062891678367d9af`.
- Frozen SCSV-Cert v6 source SHA-256: `f56a38da25a60752b5580e449a7213e88ef6d7a6006759272274331e5ff174fb`.
- RCSA and FCRRA spent diagnostics remain NO-GO and are not overwritten.
- FCRRA post-diagnostic forensics are preserved in `research/TRANSACTIONS_FCRRA_POST_DIAGNOSTIC_FORENSICS.md`.
- RCCD protocol is frozen in `research/TRANSACTIONS_RCCD_SPENT_DIAGNOSTIC_PROTOCOL.md`.

## 2. Engineering gate

The initial RCCD smoke passed but did not naturally enter the missing-exception attempt branch because frozen v6 already selected the exception in all five engineering smoke conditions. Before formal authorization, an engineering-only forced-anchor invariant test was added to exercise that branch without changing production scientific code.

Authoritative updated engineering checks:

- RCCD engineering smoke seed: only `23001`;
- RCCD smoke recheck run: `31331848557`;
- smoke source SHA: `798c6cc574bd91af5c9af79d93708659186011d0`;
- exact source pin: PASS;
- frozen v6 hash/reference preservation: PASS;
- RCCD invariant tests including forced attempt path: PASS;
- five-row engineering smoke: PASS;
- smoke isolation audit: PASS;
- artifact upload: PASS;
- full repository regression run: `31331850727`;
- full regression conclusion: PASS.

The earlier proposed RCCD engineering seed `22001` was never executed by RCCD and was replaced by `23001` because `22001` had already been used by FCRRA engineering smoke.

## 3. Authorized formal diagnostic

Authorized seeds:

- `20101`
- `20102`
- `20103`
- `20104`
- `20105`

These seeds are already spent by the independent v6 study. No fresh seed is authorized.

Authorized matrix:

- exactly 590 frozen independent conditions;
- exactly one RCCD diagnostic output per condition;
- Panel G: 300;
- Panel S: 270;
- Panel S32: 20.

The historical frozen `scsv-v6-full` rows are read as the comparator and must not be regenerated into a replacement historical artifact.

## 4. Frozen decision boundary

The A--P mechanism-signal criteria in `TRANSACTIONS_RCCD_SPENT_DIAGNOSTIC_PROTOCOL.md` are immutable for this run.

The formal result is **RCCD-MECHANISM-SIGNAL** only if every A--P criterion passes. Any failed criterion yields **RCCD-MECHANISM-SIGNAL-NO-GO**.

No threshold relaxation, subgroup rescue, benchmark removal, seed removal, alternative refit, or post-result rule change is permitted.

## 5. Claim boundary

Even a PASS is exploratory mechanism evidence on already-spent data. It may authorize only design and preregistration of a separately versioned successor using genuinely untouched seeds.

A PASS does not:

- convert SCSV-Cert v6 to independent GO;
- create confirmatory v7 evidence;
- authorize retrospective SRSD confirmation;
- establish novelty by itself.

A NO-GO retires this RCCD formulation under the frozen rules and preserves the existing independent failure boundary.