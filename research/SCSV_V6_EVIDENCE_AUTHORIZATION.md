# SCSV-Cert v6 development-evidence authorization

Authorized stage: **fresh synthetic development evidence only**.

Protocol: `research/TRANSACTIONS_SCSV_CERT_V6_PROTOCOL.md`.

Frozen implementation parent: `f088f99d6d0cfe536d0d081f5227f08aa253c168`.

Pre-evidence checks completed before authorization:

- dedicated SCSV-Cert v6 invariant tests: PASS;
- engineering smoke seed `19001`: PASS;
- 28-row smoke matrix: PASS;
- smoke seed-isolation audit: PASS;
- development gate not evaluated in smoke mode: PASS;
- full repository regression CI: PASS.

Fresh development seeds authorized exactly once for the frozen full-study path:

`19101, 19102, 19103, 19104, 19105`.

Once this authorization commit triggers the full study, all five seeds are considered spent development seeds regardless of the scientific outcome.

No post-result changes to bank construction, selector ranking, probe certificate logic, method set, thresholds, endpoints or GO/NO-GO criteria are permitted using these seeds.

A GO permits only a separately frozen scalability/external-validation stage. A failure is preserved as v6 NO-GO.