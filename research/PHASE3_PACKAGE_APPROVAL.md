# Phase 3 Package Approval

**Date:** 2026-09-06  
**Branch:** `research/phase3-noise-calibrated-scope-certification`  
**Base scientific source:** `e58ff85a93a7498a6220a3032d153c02290de352`

## Decision

The human research owner approved proceeding with the recommended Phase-3 direction after reviewing the research flow, the failed PQCR/DR-PQCR directions, the Phase-2 forensic evidence, the novelty boundary, and the proposed sequential shared/localized certification architecture.

This approval authorizes **planning and engineering-only implementation work** for Phase 3. It does **not** authorize fresh scientific development runs.

## Approved scientific direction

Phase 3 will investigate federated recovery of:

1. a shared symbolic core; and
2. sparse client-localized symbolic deviations,

with noise-calibrated structural evidence, independent Discovery/Selector/Probe data use, multiplicity-controlled final structural claims, additive sufficient-statistic computation, and outside-role safety.

PQCR-v1 and DR-PQCR-v2 are frozen historical/mechanistic studies and are not to be extended as the main research direction.

## Engineering safety rule

The frozen v11 comparator is a scientific artifact. Phase-3 engineering should use an **additive shadow-refactor strategy**:

- do not rewrite `src/fedfalsify/scsv_v11.py` merely for cleanliness;
- first implement reusable Phase-3 statistical primitives in new modules;
- prove numerical/decision equivalence against the frozen predecessor helpers on deterministic fixtures and engineering-only data;
- keep the official v11 comparator path unchanged for future matched evaluation unless an independently reviewed compatibility change is strictly necessary.

This is safer than modifying the comparator before the successor is implemented.

## Seed firewall

- `29001`: predecessor engineering/parity only;
- `29101--29105`: spent Phase 1, forbidden for tuning or regeneration;
- `29201--29205`: spent Phase 2, forbidden for tuning or regeneration;
- `29300`: reserved Phase-3 engineering-only smoke, not yet authorized by this approval alone;
- `29301--29310`: reserved Phase-3 fresh development, **not authorized**;
- `11001+`: reserved final confirmation, **not authorized**.

No fresh-seed execution may occur until a separately frozen development protocol and explicit authorization are committed.

## Next authorized action

Write and review the detailed Phase-3A implementation plan for shadow refactor, mathematical equivalence tests, deterministic rank/SSE primitives, and frozen-v11 parity. Do not implement Phase-3B scientific behavior until Phase-3A verification is complete and reviewed.
