# RCSA reference-preservation engineering clarification

Status: **ENGINEERING-ONLY CORRECTION BEFORE ANY RCSA SPENT-SEED DIAGNOSTIC ROW WAS EXECUTED**.

The first authorized RCSA spent-seed workflow attempt, run `31324426057`, stopped safely before the 590-row diagnostic. Exact source pin and frozen RCSA tests passed, but the historical independent-reference checksum step failed on `results/scsv_v6_independent/rows.csv`.

## Failure boundary

The failed step was `Verify sealed independent reference exists`. The subsequent scientific diagnostic, audit, artifact upload, and evidence commit steps were all skipped. Therefore no RCSA condition on spent seeds `20101--20105` was evaluated in this failed attempt.

## Root cause

The historical independent evidence directory was sealed before repository commit with a SHA-256 checksum over the workflow-produced CSV bytes. Python's CSV writer produced CRLF record separators. The repository has `.gitattributes` with `* text=auto`, so Git normalized the text file to LF when it entered the repository. As a result, the pre-commit byte-level SHA-256 recorded for `rows.csv` does not match a later Git checkout even though the committed CSV content has not changed.

This diagnosis is supported by Git identity, not by scientific content comparison:

- historical independent evidence commit: `25fd323c54bfa49dfcd55f36f39d9f1305195eb8`;
- `rows.csv` Git blob at that evidence commit: `92f25b499bc77499ad924e14d26feb95031b82f8`;
- `rows.csv` Git blob at the RCSA authorization commit `62616ae9a72896feba2ab1fc1b955c2d907569d0`: the same `92f25b499bc77499ad924e14d26feb95031b82f8`.

Thus the repository reference has not drifted since the sealed independent evidence commit. The mismatch is line-ending normalization between pre-commit artifact bytes and Git-normalized repository bytes.

## Corrected preservation check

For the RCSA diagnostic, historical reference preservation is verified by:

1. requiring the independent evidence files to exist;
2. requiring the current `rows.csv` Git blob SHA to be exactly identical to the blob at historical evidence commit `25fd323c...`;
3. verifying the SHA-256 entries for `summary.json`, `decision.json`, and `manifest.json`, which are unaffected by CSV line-ending normalization;
4. requiring the historical `SHA256SUMS` to retain the original artifact checksum record unchanged;
5. retaining the historical evidence commit and historical Actions artifact as immutable provenance.

No historical file is rewritten and no scientific row is modified.

## Scientific firewall

This correction changes only the provenance-verification plumbing. It does not change:

- frozen SCSV-Cert v6;
- RCSA augmentation logic;
- selector eligibility;
- role-local information criterion;
- outside-domain non-degradation;
- spent seeds;
- 590-condition geometry;
- criteria A--K;
- the historical independent-validation NO-GO.

The recovery attempt may proceed on the same already-spent independent seeds only after the corrected reference check is committed. It is still the first RCSA scientific diagnostic execution because run `31324426057` consumed no diagnostic rows.
