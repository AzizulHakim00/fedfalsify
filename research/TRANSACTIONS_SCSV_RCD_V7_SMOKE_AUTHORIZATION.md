# SCSV-RCD v7 engineering-smoke authorization

This commit authorizes **engineering smoke only** for the frozen successor protocol in `research/TRANSACTIONS_SCSV_RCD_V7_PROTOCOL.md`.

Allowed seed:

- `24001` only.

Prohibited in this stage:

- fresh development seeds `24101--24105`;
- any modification of A--R scientific gates based on smoke output;
- any modification of frozen historical SCSV-Cert v6 evidence;
- any reinterpretation of the v6 independent `INDEPENDENT-NO-GO`;
- external SRSD confirmation.

The engineering smoke must establish code-path correctness, seed isolation, historical-boundary preservation, source-link metadata integrity, fixed-reduced one-coefficient behavior, anchor non-deletion, null/dual benchmark plumbing, and ambiguity-guard behavior.

Formal v7 development evidence is authorized only after both the dedicated v7 smoke workflow and the full repository regression CI pass at the same implementation state.