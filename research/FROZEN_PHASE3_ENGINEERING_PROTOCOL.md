# Frozen Phase-3 Engineering Protocol

**Study:** FedFalsify Phase-3B / SCSV-NCSC engineering integration smoke  
**Protocol status:** frozen before any execution of seed `29300`  
**Scientific implementation checkpoint before protocol freeze:** `0d387269b1d82393267de20dad04a0b5209dacfe`  
**Frozen comparator reference:** `78d0ab7ca7afb1edfa4725a45dfd20ce2db39659`

## 1. Purpose and boundary

This protocol defines an engineering-only integration smoke for the Phase-3B implementation. Its purpose is to verify that the four prespecified branches execute reproducibly, emit the complete mechanism ledger, respect the seed/split firewalls, checkpoint atomically, and produce a complete archival package.

Seed `29300` is **not** a development-performance sample and cannot support a scientific GO/NO-GO claim. Exact recovery, NMSE, precision, recall, communication, and runtime are descriptive only in this engineering smoke and cannot change any scientific constant or rule.

## 2. Exact engineering condition matrix

The condition key is

`(family, num_clients, balance_profile, role_profile, noise_ratio, seed)`.

Exactly these six conditions are authorized, in this order:

1. `("quadratic_role_v10", 4, "balanced", "single", 0.10, 29300)`
2. `("trig_role_v10", 4, "balanced", "single", 0.30, 29300)`
3. `("null_role_v10", 8, "balanced", "none", 0.10, 29300)`
4. `("anchor_contamination_null_v10", 8, "balanced", "none", 0.30, 29300)`
5. `("weak_source_role_v10", 8, "balanced", "quarter", 0.10, 29300)`
6. `("dual_role_v10", 8, "imbalanced", "quarter", 0.30, 29300)`

No additional condition, seed, family, noise level, role profile, or client count may be added in response to the engineering results.

## 3. Exact method set

Every condition must produce exactly one row for each method, in this order:

1. `scsv-elrc-v11-full` — frozen unmodified v11 comparator.
2. `scr-only` — SCR shared structure plus frozen-v11 localized logic through the parity adapter.
3. `ncee-only` — frozen-v11 ordinary shared structure plus NCEE localized certification.
4. `scsv-ncsc` — SCR shared structure plus NCEE localized certification.

No fifth method or rescue branch is permitted in this engineering protocol.

## 4. Frozen scientific constants and capacities

The engineering run must use the already reviewed Phase-3B constants without adaptation:

- Shared Selector final family-wise error control: Holm, `alpha_shared = 0.05`.
- Discovery client-role construction: BH, `q_role = 0.10`, exploratory only.
- Final localized Probe family-wise error control: Holm, `alpha_dev = 0.05`.
- Minimum localized active support per client: `10` rows.
- Minimum localized FULL-model residual degrees of freedom: `5`.
- Maximum localized role fraction: `0.50` of clients, with at least one outside client.
- Candidate sign tolerance: machine-fixed implementation convention, not a tunable study parameter.
- Outside-role non-degradation tolerance: `1e-10` SSE units exactly.
- Shared operational capacity: intercept plus at most `5` non-intercept shared terms (`6` total).
- Localized operational capacity: at most `2` accepted deviations.
- Final structure capacity: at most `10` total terms including intercept.
- Rank/identifiability handling: deterministic machine-scale rank convention from the sealed Phase-3A linear-algebra layer; no tuned ridge or outcome-dependent rank threshold.
- Final coefficient refit occurs only after structural acceptance is frozen and cannot change accepted term identities.

The frozen v11 comparator retains its own existing scientific constants and caps unchanged.

## 5. Evidence-split firewall

The scientific split discipline is unchanged:

- Discovery nominates ordinary/localized candidates and constructs provisional NCEE roles.
- Selector independently certifies the shared core and may only screen/remove frozen localized hypotheses.
- Probe is untouched until the surviving localized family is frozen and is used only for final localized certification.
- Probe cannot nominate terms, change roles, alter sources, or modify Discovery signs.
- Benchmark truth is evaluation metadata only and cannot enter any scientific acceptance function.

## 6. Seed firewall

- `29001`: predecessor engineering/parity only; not part of this engineering smoke.
- `29101–29105`: spent Phase-1 development; blocked.
- `29201–29205`: spent Phase-2 development; blocked.
- `29300`: the **only** authorized Phase-3 engineering integration seed.
- `29301–29310`: fresh Phase-3 development namespace; blocked during this protocol.
- `11001–11999`: final-confirmation namespace; blocked.

A Colab disconnect may resume the same `29300` matrix from valid completed checkpoints. Seed `29300` may not be used to tune alpha/q values, support floors, capacities, rank behavior, outside-role tolerance, candidate grammar, or rescue rules.

## 7. Checkpoint and resume semantics

A completed engineering condition is an atomic matched group containing exactly four unique method rows with the exact method set in Section 3.

After each complete condition group:

1. update the in-memory rows;
2. write checkpoint data to a temporary file in the same directory;
3. atomically replace the prior checkpoint;
4. atomically refresh PKL/joblib convenience state;
5. print the completed condition index and saved status.

On resume, only complete valid four-method groups may be skipped. Partial groups, duplicate groups, or wrong-method groups must be discarded and recomputed as a whole. A partial group is never treated as completed evidence.

## 8. Engineering decision definition

The only permitted decision values are:

- `PHASE3-ENGINEERING-PASS`
- `PHASE3-ENGINEERING-FAIL`

`PHASE3-ENGINEERING-PASS` requires all of the following:

1. the required deterministic test gate passed before scientific execution;
2. all six exact condition groups are complete;
3. every group contains exactly four unique method rows with the prespecified method set;
4. there are zero duplicate primary method rows;
5. there are zero seed/firewall/integrity violations;
6. all required archival artifacts are present and hashable;
7. the ZIP archive passes integrity verification.

The engineering decision **must not inspect or threshold** exact recovery, NMSE, term/shared/deviation precision or recall, runtime, communication, or any method comparison.

## 9. Descriptive outputs

Performance and efficiency summaries are saved only to diagnose integration and verify reporting. They may include exact recovery, term/shared/deviation precision and recall, NMSE, communication bytes, and method-only runtime. These values have no engineering PASS/FAIL role and cannot justify scientific-rule changes.

The mechanism ledger must retain the prespecified shared and localized diagnostics even when a branch accepts no new term.

## 10. Change control after first `29300` execution

After `29300` is first executed, only software/infrastructure defects may be repaired and rerun. Such a repair must not change any scientific constant, hypothesis family definition, split use, capacity, structural acceptance rule, or evaluation target. Any scientifically motivated rule change would require a separately reviewed protocol and must not be justified using observed `29300` outcomes.
