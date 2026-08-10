# SCSV-SPCC v8 engineering authorization

This commit authorizes engineering validation of the frozen v8 successor only.

- Engineering seed: `25001` only.
- Fresh development seeds `25101--25105` remain locked and may not be generated, inspected, or used.
- Frozen protocol: `research/TRANSACTIONS_SCSV_SPCC_V8_PROTOCOL.md`.
- Dedicated smoke must run the v8 invariant/forced-path tests and the seven-condition engineering matrix.
- Complete repository regression must also pass before any fresh-development authorization.
- A smoke failure permits engineering repair only; it does not permit changing scientific gates using fresh evidence because no fresh v8 evidence has been released.
