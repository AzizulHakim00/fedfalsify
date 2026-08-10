# SCSV-RCEF v9 engineering authorization

This authorization releases **engineering seed 26001 only** for SCSV-RCEF v9 smoke testing.

## Frozen scientific sources

- protocol: `research/TRANSACTIONS_SCSV_RCEF_V9_PROTOCOL.md`
- novelty audit: `research/TRANSACTIONS_SCSV_RCEF_V9_NOVELTY_AUDIT.md`
- v8 forensic basis: `research/TRANSACTIONS_SCSV_SPCC_V8_POST_DEVELOPMENT_FORENSICS.md`
- implementation: `src/fedfalsify/scsv_v9.py`
- benchmark grammar: `src/fedfalsify/scsv_v9_benchmarks.py`
- study harness: `src/fedfalsify/scsv_v9_study.py`
- tests: `tests/test_scsv_v9.py`

## Boundary

- v8 remains `DEVELOPMENT-NO-GO`.
- `25101--25105` remain spent forever.
- v9 fresh seeds `26101--26105` remain untouched and unauthorized.
- no development run may start until dedicated v9 smoke and the full repository regression are green at an implementation-equivalent state.
- smoke results are engineering diagnostics only and cannot change A--W gates or the fresh matrix.