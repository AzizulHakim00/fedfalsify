"""Governed Phase-3C fresh-development orchestration.

This module is intentionally separate from the sealed Phase-3B scientific
implementation.  It owns only the prospective development matrix, seed and
checkpoint firewalls, paired analysis, persistence and reporting.  It must not
change SCR, NCEE, v11, the V10 benchmark generator, or their scientific rules.
"""

from __future__ import annotations

from typing import Sequence

from .scsv_v10_benchmarks import SINGLE_FAMILIES_V10
from .scsv_v12 import PHASE3_METHODS

DEVELOPMENT_SEEDS = tuple(range(29301, 29311))
ConditionKey = tuple[str, int, str, str, float, int]
NULL_FAMILIES = {"null_role_v10", "anchor_contamination_null_v10"}
SPECIAL_QUARTER_FAMILIES = {"weak_source_role_v10", "dual_role_v10"}


def validate_development_seed_block(seeds: Sequence[int]) -> None:
    normalized = tuple(int(seed) for seed in seeds)
    if normalized != DEVELOPMENT_SEEDS:
        raise ValueError("Phase-3C development requires exactly seeds 29301--29310 in order")
    if 29300 in normalized:
        raise ValueError("engineering seed 29300 is not a development seed")
    if any(11001 <= seed <= 11999 for seed in normalized):
        raise ValueError("final-confirmation seeds 11001--11999 are blocked")


def scientific_conditions(seeds: Sequence[int] = DEVELOPMENT_SEEDS) -> tuple[ConditionKey, ...]:
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
        raise RuntimeError(f"Phase-3C condition firewall expected 1200 unique conditions, got {len(result)}")
    return result


def condition_key_string(condition: ConditionKey) -> str:
    family, clients, balance, role, noise, seed = condition
    return f"{family}|{int(clients)}|{balance}|{role}|{float(noise):.2f}|{int(seed)}"


def condition_key_from_row(row: dict) -> ConditionKey:
    return (
        str(row["family"]),
        int(row["num_clients"]),
        str(row["balance_profile"]),
        str(row["role_profile"]),
        float(row["noise_ratio"]),
        int(row["seed"]),
    )


def validate_checkpoint_groups(rows: Sequence[dict]) -> tuple[list[dict], set[ConditionKey]]:
    authorized = set(scientific_conditions())
    grouped: dict[ConditionKey, list[dict]] = {}
    for raw in rows:
        try:
            key = condition_key_from_row(raw)
        except (KeyError, TypeError, ValueError):
            continue
        if key not in authorized:
            continue
        grouped.setdefault(key, []).append(dict(raw))

    cleaned: list[dict] = []
    completed: set[ConditionKey] = set()
    required_methods = set(PHASE3_METHODS)
    for condition in scientific_conditions():
        group = grouped.get(condition, [])
        methods = [str(row.get("method", "")) for row in group]
        if (
            len(group) == len(PHASE3_METHODS)
            and set(methods) == required_methods
            and len(methods) == len(set(methods))
        ):
            by_method = {str(row["method"]): dict(row) for row in group}
            for method in PHASE3_METHODS:
                item = by_method[method]
                item["condition_key"] = condition_key_string(condition)
                cleaned.append(item)
            completed.add(condition)
    return cleaned, completed
