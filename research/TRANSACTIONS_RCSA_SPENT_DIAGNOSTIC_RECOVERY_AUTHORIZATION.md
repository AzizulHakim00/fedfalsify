# RCSA spent-seed diagnostic recovery authorization

Status: **AUTHORIZED AFTER PRE-DIAGNOSTIC REFERENCE-CHECK FAILURE; NO RCSA SCIENTIFIC ROWS WERE CONSUMED IN THE FAILED ATTEMPT**.

The initial authorized workflow run `31324426057` passed exact source pin and frozen RCSA invariant tests but stopped at the historical independent-reference verification step. The 590-row RCSA diagnostic step and all downstream scientific/audit/artifact steps were skipped.

The root cause and correction are documented in `research/TRANSACTIONS_RCSA_REFERENCE_PRESERVATION_CLARIFICATION.md`: the historical CSV pre-commit SHA-256 reflected CRLF workflow bytes, while Git `text=auto` normalized the committed repository copy to LF. The historical evidence commit and the current branch contain the exact same `rows.csv` Git blob `92f25b499bc77499ad924e14d26feb95031b82f8`, so there is no reference drift.

The corrected workflow verifies immutable historical Git-blob identity, retains the original artifact SHA-256 record unchanged, and separately verifies the unaffected JSON checksums. No historical result file is rewritten.

This recovery authorizes the same frozen RCSA protocol and criteria A--K on only the already-spent independent seeds `20101--20105`. No fresh successor seed is authorized. The RCSA algorithm, v6 anchor, 590-condition geometry, selector role test, outside-domain rule, and mechanism-signal thresholds are unchanged.

Because the failed attempt executed zero RCSA scientific conditions, this recovery is the first actual RCSA spent-seed diagnostic execution. It must still be interpreted only as post-independent spent-data mechanism analysis and cannot alter the historical SCSV-Cert v6 independent-validation NO-GO.
