# RCCD engineering smoke recheck

Status: **AUTHORIZED FOR ENGINEERING RECHECK ONLY**.

The first RCCD engineering smoke passed, but its five real smoke conditions all had the exception already selected by frozen v6, so the production missing-exception attempt branch was not exercised end-to-end.

Before any formal spent-seed RCCD execution, a dedicated invariant test was added that uses the engineering-only seed `23001` and a test double of the frozen v6 anchor with only the already-banked exception removed. This forces the RCCD source-linked attempt path while keeping production scientific code and the frozen formal A--P criteria unchanged.

This commit authorizes a second RCCD engineering smoke and full repository regression run on the updated test suite.

- RCCD engineering seed: only `23001`.
- Spent independent seeds `20101--20105`: still not authorized.
- Fresh successor/v7 seeds: not authorized.
- No scientific RCCD signal may be inferred from this engineering recheck.