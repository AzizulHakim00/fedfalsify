"""Prospective Phase-3E fresh-noisy evaluation for frozen FedFalsify v13.

This module is additive orchestration only.  It must not alter v11, v12, v13,
the scope-contrast mechanism, or the frozen V10 benchmark generator.
"""

from __future__ import annotations

from typing import Sequence

from .scsv_v10_benchmarks import SINGLE_FAMILIES_V10

DEVELOPMENT_SEEDS = tuple(range(29401, 29411))
PHASE3E_METHODS = (
    "scsv-elrc-v11-full",
    "scsv-ncsc",
    "scope-contrast-only",
    "v13-full",
)

ConditionKey = tuple[str, int, str, str, float, int]


def validate_development_seed_block(seeds: Sequence[int]) -> None:
    normalized = tuple(int(seed) for seed in seeds)
    if normalized != DEVELOPMENT_SEEDS:
        raise ValueError("Phase-3E development requires exactly seeds 29401--29410 in order")
    if 29300 in normalized or any(29301 <= seed <= 29310 for seed in normalized):
        raise ValueError("spent Phase-3C/engineering seeds are blocked")
    if any(11001 <= seed <= 11999 for seed in normalized):
        raise ValueError("final-confirmation seeds 11001--11999 are blocked")


def scientific_conditions(seeds: Sequence[int] = DEVELOPMENT_SEEDS) -> tuple[ConditionKey, ...]:
    """Return the unchanged Phase-3C benchmark geometry on the new seed block."""
    validate_development_seed_block(seeds)
    conditions: list[ConditionKey] = []

    for family in SINGLE_FAMILIES_V10:
        for num_clients in (4, 8, 16):
            roles = ("single",) if num_clients == 4 else ("single", "quarter")
            for balance in ("balanced", "imbalanced"):
                for role in roles:
                    for noise in (0.10, 0.30):
                        for seed in seeds:
                            conditions.append(
                                (family, num_clients, balance, role, float(noise), int(seed))
                            )

    for family in ("null_role_v10", "anchor_contamination_null_v10"):
        for num_clients in (4, 8, 16):
            for balance in ("balanced", "imbalanced"):
                for noise in (0.10, 0.30):
                    for seed in seeds:
                        conditions.append(
                            (family, num_clients, balance, "none", float(noise), int(seed))
                        )

    for family in ("weak_source_role_v10", "dual_role_v10"):
        for num_clients in (8, 16):
            for balance in ("balanced", "imbalanced"):
                for noise in (0.10, 0.30):
                    for seed in seeds:
                        conditions.append(
                            (family, num_clients, balance, "quarter", float(noise), int(seed))
                        )

    result = tuple(conditions)
    if len(result) != 1200 or len(set(result)) != 1200:
        raise RuntimeError(
            f"Phase-3E condition firewall expected 1200 unique conditions, got {len(result)}"
        )
    return result
