# SCSV-RCEF v9 sharded recovery fresh-development authorization

This document authorizes the replacement fresh-development execution defined in `research/TRANSACTIONS_SCSV_RCEF_V9_INFRASTRUCTURE_RECOVERY_PROTOCOL.md`.

## Frozen scientific identity

The scientific v9 mechanism remains the cancelled-run source frozen at `f291f05f1c0f0916b4450e9dcc8bbec4322bb110`. The recovery adds only sharded execution, aggregation, auditing, and sealing.

No change has been made to:

- `src/fedfalsify/scsv_v9.py`;
- `src/fedfalsify/scsv_v9_benchmarks.py`;
- `src/fedfalsify/scsv_v9_study.py`;
- the original v9 protocol;
- benchmark family definitions or coefficients;
- the six frozen methods;
- A--W gate definitions or numeric thresholds.

The only scientific-study substitution is the new untouched replacement seed namespace required after the infrastructure cancellation.

## Historical boundary

- v6 independent validation remains `INDEPENDENT-NO-GO`;
- v7 development remains `DEVELOPMENT-NO-GO`;
- v8 development remains `DEVELOPMENT-NO-GO`;
- v9 run `31435708338` remains `INFRASTRUCTURE-CANCELLED / NO SCIENTIFIC VERDICT`;
- seeds `26101--26105` remain permanently spent and forbidden as fresh evidence.

## Engineering firewall evidence

Exact engineering authorization SHA: `f535601532641959488f04d67f0f874912c881eb`.

Dedicated recovery smoke:

- run `31464955216`;
- conclusion: `SUCCESS`;
- engineering seed: `27001` only;
- frozen-source equality check: PASS;
- original v9 + recovery firewall tests: PASS;
- smoke isolation audit: PASS;
- artifact upload: PASS;
- artifact `scsv-rcef-v9-recovery-engineering-smoke`, digest `sha256:ce85502e3f606e3888ea7016cfe52f5006380aee52f7c24927b199beb8a975f1`.

Full repository regression:

- run `31464955171`;
- conclusion: `SUCCESS`;
- all repository test/demo/smoke stages: PASS.

## Fresh seed release

The following fresh replacement seeds are now authorized exactly once:

`27101, 27102, 27103, 27104, 27105`.

The workflow must execute five parallel seed shards, each containing exactly 120 conditions x 6 methods = 720 rows, followed by a single complete aggregation of exactly 600 conditions x 6 methods = 3600 rows.

Once any shard begins scientific computation, all five `271xx` seeds are permanently spent regardless of workflow outcome. They may never be retuned on, rerun as fresh evidence, or recycled for independent validation.

One failed A--W gate means `DEVELOPMENT-NO-GO`. A partial shard or infrastructure failure has no scientific verdict unless the complete preregistered 3600-row evidence was already independently sealed.
