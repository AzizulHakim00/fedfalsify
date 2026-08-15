# SCSV-Cert v6 independent-validation engineering clarification

Status: **FROZEN BEFORE ANY INDEPENDENT SEED `20101--20105` WAS EXECUTED**.

Two engineering smokes on seed `20001` failed before any scientific output. Neither failure evaluated an independent-validation gate and neither touched seeds `20101--20105`.

## Smoke 1: held-out selector/probe feasibility

The first adapter allowed a 50-row imbalanced client. Frozen SCSV-Cert v6 calls `partition_clients(..., validation_fraction=0.30)` and then `split_selector_probe`, which requires at least 20 observations in the held-out validation partition. For 50 rows, `round(0.30*50)=15`, so the frozen algorithm correctly rejected the adapter input before scientific evaluation.

## Smoke 2: five discovery-fold feasibility

The initial engineering correction used a 70-row floor. This satisfies the held-out requirement because `round(0.30*70)=21`, but leaves `70-21=49` discovery rows. Frozen v6 then calls `_split_discovery_folds`, which uses `numpy.array_split(..., 5)` and constructs an `ExternalClientData` object for each fold. Every such object requires at least 10 rows, while 49 rows split into five folds includes one 9-row fold. The second smoke therefore also stopped before any scientific output.

## Minimal exact correction

The independent imbalanced-size adapter now uses a minimum of **71 observations/client**. This is the smallest integer satisfying both inherited constraints under the unchanged v6 partitioning:

- `round(0.30*71)=21 >= 20` held-out rows;
- `71-21=50` discovery rows;
- `numpy.array_split(50, 5)` yields exactly five 10-row discovery folds.

Using 71 rather than a larger convenience floor preserves as much of the preregistered imbalance stress as possible and follows the minimum-change principle.

The following remain unchanged:

- SCSV-Cert v6 algorithm and `scsv_v6.py`;
- all thresholds, ranking rules, bank logic, score proposer and certificate semantics;
- five independent truth families and the nuisance-only role of `x4`;
- scenarios, noise levels, nominal sample sizes and client counts;
- six comparison methods;
- fresh seeds `20101--20105`;
- 590 matched conditions / 3,540 rows;
- independent-validation gates A--R.

The corrected smoke on seed `20001` and full repository regression CI must both pass before the authorization marker `[run-scsv-v6-independent]` is committed. The final evidence manifest must hash this clarification together with the frozen independent protocol and implementation files.
