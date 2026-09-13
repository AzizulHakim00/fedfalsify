"""Prospective Phase-3E fresh-noisy evaluation for frozen FedFalsify v13.

This module is additive orchestration only.  It must not alter v11, v12, v13,
the scope-contrast mechanism, or the frozen V10 benchmark generator.
"""

from __future__ import annotations

from typing import Mapping, Sequence

from .phase3d_fixtures import Phase3DFixture
from .scsv_v10_benchmarks import (
    INTERACTION_DEV_V10,
    LINEAR_DEV_V10,
    QUADRATIC_DEV_V10,
    SINGLE_FAMILIES_V10,
    TRUE_DEVIATIONS_V10,
    TRIG_DEV_V10,
    WEAK_SOURCE_DEV_V10,
)

DEVELOPMENT_SEEDS = tuple(range(29401, 29411))
PHASE3E_METHODS = (
    "scsv-elrc-v11-full",
    "scsv-ncsc",
    "scope-contrast-only",
    "v13-full",
)

ConditionKey = tuple[str, int, str, str, float, int]
NULL_FAMILIES = {"null_role_v10", "anchor_contamination_null_v10"}


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


def _client_ids(indices: Sequence[int]) -> tuple[str, ...]:
    return tuple(f"client-{int(index) + 1}" for index in indices)


def true_role_map(condition: ConditionKey) -> dict[str, tuple[str, ...]]:
    """Return benchmark truth for evaluation only; never used for v13-full decisions."""
    family, num_clients, _balance, role, _noise, _seed = condition
    if family in NULL_FAMILIES:
        return {}

    family_term = {
        "quadratic_role_v10": QUADRATIC_DEV_V10,
        "linear_role_v10": LINEAR_DEV_V10,
        "trig_role_v10": TRIG_DEV_V10,
        "interaction_role_v10": INTERACTION_DEV_V10,
    }
    if family in family_term:
        count = 1 if role == "single" else max(1, int(num_clients) // 4)
        indices = tuple(range(int(num_clients) - count, int(num_clients)))
        return {family_term[family]: _client_ids(indices)}

    quarter = max(1, int(num_clients) // 4)
    last = tuple(range(int(num_clients) - quarter, int(num_clients)))
    if family == "weak_source_role_v10":
        return {WEAK_SOURCE_DEV_V10: _client_ids(last)}
    if family == "dual_role_v10":
        prior = tuple(range(int(num_clients) - 2 * quarter, int(num_clients) - quarter))
        return {
            QUADRATIC_DEV_V10: _client_ids(last),
            LINEAR_DEV_V10: _client_ids(prior),
        }
    raise KeyError(f"unknown Phase-3E family: {family}")


def benchmark_to_v13_fixture(generated, condition: ConditionKey) -> Phase3DFixture:
    """Adapt one frozen V10 stochastic benchmark to the already-frozen v13 API.

    Truth fields exist only because ``Phase3DFixture`` stores evaluation
    metadata.  ``v13-full`` receives the broad candidate banks and does not use
    these truth fields in its discovery/certification decisions.
    """
    roles: Mapping[str, Sequence[str]] = true_role_map(condition)
    localized = tuple(TRUE_DEVIATIONS_V10[str(generated.family)])
    scopes = tuple(
        (term, tuple(map(str, roles[term])))
        for term, _coefficient in localized
    )
    return Phase3DFixture(
        name=(
            f"{condition[0]}__K{condition[1]}__{condition[2]}__{condition[3]}"
            f"__noise{condition[4]:.2f}__seed{condition[5]}"
        ),
        clients=tuple(generated.clients),
        shared_coefficients=tuple(generated.spec.coefficients),
        localized_coefficients=localized,
        truth_scopes=scopes,
    )
