# FedFalsify v9 infrastructure-recovery protocol

## Status and purpose

This protocol is frozen after the infrastructure-cancelled v9 fresh-development attempt recorded in `research/TRANSACTIONS_SCSV_RCEF_V9_INFRASTRUCTURE_CANCELLATION.md` and before any replacement recovery seed is executed.

The cancelled run `31435708338` produced **no scientific verdict**. Its seeds `26101--26105` are permanently spent and are not reused here.

This recovery changes **execution only**. It does not change the FedFalsify v9 SCSV-RCEF scientific mechanism, benchmark grammar, coefficients, role rule, proposal rule, source-qualification rule, evidence-fusion rule, ambiguity guards, methods, or A--W scientific gates frozen in `research/TRANSACTIONS_SCSV_RCEF_V9_PROTOCOL.md`.

## Historical boundaries

The following remain permanent and cannot be relabelled by this recovery:

- v6 independent validation: `INDEPENDENT-NO-GO`;
- v7 fresh development: `DEVELOPMENT-NO-GO`;
- v8 fresh development: `DEVELOPMENT-NO-GO`;
- v9 run `31435708338`: `INFRASTRUCTURE-CANCELLED / NO SCIENTIFIC VERDICT`;
- v9 seeds `26101--26105`: permanently spent.

## Seed collision audit and namespaces

Repository-wide collision search was completed before this recovery protocol was written. No prior occurrence was found for the reserved recovery namespace.

- engineering-only recovery smoke seed: `27001`;
- fresh replacement development seeds: `27101, 27102, 27103, 27104, 27105`.

The engineering seed must never appear in scientific recovery evidence.

Once any scientific shard begins evaluating any `271xx` seed, all `27101--27105` become permanently spent regardless of workflow outcome. A failed or cancelled shard does not authorize reuse of the namespace as fresh evidence.

## Frozen scientific study

The scientific study is exactly the v9 study already frozen in `research/TRANSACTIONS_SCSV_RCEF_V9_PROTOCOL.md`, except that the replacement seed namespace is `27101--27105`.

Exactly the same 600-condition design is used:

- 400 conditions across the four main single-deviation families;
- 60 null-role conditions;
- 60 diffuse-null conditions;
- 40 weak-source conditions;
- 40 dual-role conditions.

Exactly six methods are evaluated per condition:

1. `scsv-rcef-v9-full`;
2. `scsv-rcef-v9-no-role-proposer`;
3. `scsv-rcef-v9-selector-only`;
4. `scsv-spcc-v8-style`;
5. `scsv-v6-anchor`;
6. `centralized-forward`.

The final evidence must therefore contain exactly `600 x 6 = 3600` rows.

## Frozen A--W gates

The recovery uses the **same A--W gate definitions and numeric thresholds** as the frozen v9 protocol. The only seed-specific substitution is that Gate A requires seeds exactly `27101--27105` and excludes both engineering seed `27001` and spent v9 seeds `26101--26105`.

No other gate text, threshold, comparison method, family definition, or aggregation rule may change.

One failed gate means `DEVELOPMENT-NO-GO` for the replacement v9 recovery evidence. All 23 gates must pass for `DEVELOPMENT-GO`.

## Sharded execution architecture

The original monolithic run executed for roughly six hours and was cancelled before producing any sealed evidence. To remove that infrastructure bottleneck, the replacement run is partitioned **only by seed**.

Five independent scientific shards are run in parallel:

- shard `27101`: all 120 frozen conditions for seed 27101 x 6 methods = 720 rows;
- shard `27102`: all 120 frozen conditions for seed 27102 x 6 methods = 720 rows;
- shard `27103`: all 120 frozen conditions for seed 27103 x 6 methods = 720 rows;
- shard `27104`: all 120 frozen conditions for seed 27104 x 6 methods = 720 rows;
- shard `27105`: all 120 frozen conditions for seed 27105 x 6 methods = 720 rows.

A shard must not evaluate another shard's seed. No shard computes scientific gates independently.

Each shard must:

1. checkout the exact authorization SHA;
2. verify historical v6/v7/v8 evidence boundaries and the v9 cancellation record;
3. run the hardened v9 forced-path test suite;
4. evaluate exactly one fresh recovery seed;
5. produce exactly 720 rows over exactly 120 condition keys and all six frozen methods;
6. upload its raw shard rows and a shard manifest before any final aggregation.

## Final aggregation and sealing

A separate aggregation job begins only if all five shard jobs succeed.

The aggregator must:

1. checkout the exact same authorization SHA used by the shards;
2. download all five shard artifacts;
3. verify exactly five unique seeds `27101--27105`;
4. verify 720 rows and 120 unique condition keys per shard;
5. verify exactly 3600 total rows and 600 unique condition keys after concatenation;
6. verify exactly six frozen methods per condition;
7. reject duplicates, missing methods, NaN/Inf in required numeric fields, engineering seed 27001, and spent seeds 26101--26105;
8. compute the original frozen A--W gates only after the complete 3600-row matrix is assembled;
9. write `rows.csv`, `summary.json`, `decision.json`, `manifest.json`, `SHA256SUMS`, and `COMPLETE`;
10. upload the sealed combined artifact before repository write;
11. commit the sealed evidence with `[skip ci]` only after all integrity checks pass.

No partial shard may be interpreted as a v9 scientific result.

## Engineering firewall before fresh recovery

Before any `271xx` shard may start, all of the following must pass at an implementation-equivalent SHA:

1. v6/v7/v8 sealed evidence remains unchanged;
2. the v9 cancellation boundary remains present and unchanged;
3. `src/fedfalsify/scsv_v9.py` and `src/fedfalsify/scsv_v9_benchmarks.py` are unchanged from the cancelled-run scientific source;
4. the original hardened `tests/test_scsv_v9.py` passes;
5. recovery-specific tests verify 120 conditions per single-seed shard, 720 rows per shard, disjoint shard seeds, 600 combined conditions, 3600 combined rows, exact six-method coverage, and exact A--W gate-key parity with v9;
6. engineering smoke uses only seed `27001` and never any `271xx` seed;
7. full repository regression passes.

The recovery harness/workflow may add only infrastructure capabilities required to partition, aggregate, audit, and seal the unchanged scientific study.

## Scientific boundary after recovery

- `DEVELOPMENT-GO`: freeze v9 and seeds `27101--27105` permanently, then design a separately frozen independent-validation protocol using a completely new untouched seed namespace. No external confirmation begins before that independent protocol passes its own firewall.
- `DEVELOPMENT-NO-GO`: freeze v9 and seeds `27101--27105` permanently; only clearly labelled read-only/spent-data diagnostics may use the recovery evidence. No retuning on recovery seeds is allowed.
- infrastructure failure after any `271xx` shard begins: `27101--27105` remain spent and no scientific verdict is assigned unless the complete preregistered 3600-row matrix was already independently sealed.

No outcome changes the historical v6/v7/v8/v9-cancellation labels.