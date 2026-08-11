# FedFalsify v10 engineering authorization

Status: **ENGINEERING-SMOKE ONLY**

This authorization permits only the SCSV-AQCC v10 engineering smoke using seed `28001` and the normal repository regression suite.

It does **not** authorize fresh-development seeds `28101--28105`.

Frozen paper-first components already present before this authorization:

- `research/TRANSACTIONS_SCSV_AQCC_V10_NOVELTY_AUDIT.md`;
- `research/TRANSACTIONS_SCSV_AQCC_V10_PROTOCOL.md`;
- `src/fedfalsify/scsv_v10_benchmarks.py`;
- `src/fedfalsify/scsv_v10.py`;
- `src/fedfalsify/scsv_v10_study.py`;
- `src/fedfalsify/scsv_v10_sharded.py`;
- `tests/test_scsv_v10.py`;
- `tests/test_scsv_v10_sharded.py`;
- `.github/workflows/scsv_v10_smoke.yml`.

The engineering firewall must demonstrate forced-path correctness, smoke isolation, and full repository regression before any v10 development workflow is authorized. If engineering smoke reveals a code/test defect, only pre-evidence engineering corrections are permitted. Scientific protocol text, A--Y gates, benchmark families, and reserved fresh seed namespace must remain unchanged unless the protocol is explicitly abandoned before fresh evidence begins.

Historical v6-v9 labels and spent-seed boundaries remain unchanged.
