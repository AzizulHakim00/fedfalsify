# Phase 3A Engineering Parity Report

**Date:** 2026-09-06  
**Execution branch:** `research/phase3a-shadow-refactor-parity`  
**Frozen scientific source:** `e58ff85a93a7498a6220a3032d153c02290de352`  
**Verification code commit:** `9716a593e9bddc0d224029f05ac789cbfe4cf18f`  
**GitHub Actions verification run:** `33987413948`

## Scope

Phase 3A was restricted to additive engineering infrastructure and parity checks. It did **not** implement SCR, NCEE, Holm testing, partial-F scientific acceptance rules, `scsv_v12.py`, or a Phase-3 fresh-development runner.

The official v11 comparator was not refactored or rewritten. New code was added beside it for sufficient-statistic reconstruction, deterministic least-squares/rank handling, condition-local packet caching, and an engineering-only parity audit.

No runtime-speedup or communication-efficiency claim is made from Phase 3A. The cache is infrastructure for avoiding duplicate future packet construction; it is not integrated into v11 and was not evaluated as a scientific performance contribution.

## Seed use

Phase 3A used only engineering seed `29001` in the governed six-condition smoke/parity audit.

The following namespaces were not executed:

- `29101--29105` — spent Phase 1;
- `29201--29205` — spent Phase 2;
- `29300` — reserved Phase-3 engineering smoke;
- `29301--29310` — reserved fresh Phase-3 development;
- `11001--11999` — reserved final confirmation.

The Phase-3A cache builder and seed-firewall tests reject non-`29001` execution.

## Frozen comparator integrity

The final verification compared the execution branch against `research/phase3-noise-calibrated-scope-certification` and found no diff in the frozen comparator/benchmark files.

Exact Git blob identities are unchanged on both branches:

| File | Git blob SHA |
|---|---|
| `src/fedfalsify/scsv_v11.py` | `2704a9447ad19964a9eb1847c4ad081732494b6f` |
| `src/fedfalsify/scsv_v11_study.py` | `35e54100107538758c056a1a9a45cd2319f7fec2` |
| `src/fedfalsify/scsv_v10_benchmarks.py` | `11c0046f53e83d9a0b188e391eba4cdec234fac8` |

The frozen v11 unit path also passed all `6` tests in the final verification run.

## Numerical equivalence

The engineering parity audit used the six frozen v11 smoke-condition geometries at seed `29001` and compared:

1. predecessor sufficient packets vs new shadow packets;
2. additive packet aggregation vs explicit centralized row concatenation; and
3. sufficient-statistic least squares vs centralized `numpy.linalg.lstsq` on the fixed engineering term subset.

All six conditions passed packet, aggregation, and least-squares equivalence checks.

Maximum absolute discrepancies recorded across the six-condition audit were:

| Quantity | Maximum absolute error |
|---|---:|
| Gram entries | `7.275957614183426e-12` |
| target cross-products | `2.7284841053187847e-12` |
| reconstructed SSE | `2.0463630789890885e-12` |

These are numerical floating-point differences only. No scientific threshold was adjusted to obtain parity.

## Repository tests

Final verification evidence from run `33987413948`:

- frozen v11 tests: `6/6` passed;
- focused Phase-3A tests: `11/11` passed;
- full repository collection: `208` tests;
- full repository suite: exit code `0`, no failures;
- six-condition engineering parity audit: `6/6` conditions passed.

The Phase-3A focused tests cover the seed firewall, predecessor/new packet equivalence, SSE reconstruction, centralized/federated least-squares and rank behavior, cache determinism, predecessor packet compatibility, and the governed parity runner.

## Decision

**PHASE3A-ENGINEERING-PASS.**

This result establishes an additive, tested engineering foundation without changing the frozen v11 scientific comparator. It authorizes **review of a separate Phase-3B scientific implementation plan only**.

It does **not** authorize:

- SCR/NCEE scientific implementation without a reviewed plan;
- use of seed `29300`;
- execution of `29301--29310`;
- any use of `11001+`;
- a scientific superiority claim;
- an optimization/speedup claim.

Phase 3A stops here pending review of the next scientific implementation plan.
