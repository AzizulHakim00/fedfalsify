from __future__ import annotations

import pytest

from fedfalsify.phase3e_v13_development_runner import (
    DEVELOPMENT_SEEDS,
    PHASE3E_METHODS,
    scientific_conditions,
    validate_development_seed_block,
)


def test_phase3e_uses_new_unspent_ten_seed_block() -> None:
    assert DEVELOPMENT_SEEDS == tuple(range(29401, 29411))
    validate_development_seed_block(DEVELOPMENT_SEEDS)


@pytest.mark.parametrize(
    "bad_seeds",
    [
        tuple(range(29301, 29311)),
        (29300,) + tuple(range(29402, 29411)),
        tuple(range(11001, 11011)),
        tuple(range(29401, 29410)),
    ],
)
def test_phase3e_seed_firewall_rejects_spent_engineering_final_and_incomplete_blocks(
    bad_seeds: tuple[int, ...],
) -> None:
    with pytest.raises(ValueError):
        validate_development_seed_block(bad_seeds)


def test_phase3e_reuses_complete_phase3c_matrix_without_changing_benchmark_geometry() -> None:
    conditions = scientific_conditions()
    assert len(conditions) == 1200
    assert len(set(conditions)) == 1200
    assert {item[-1] for item in conditions} == set(DEVELOPMENT_SEEDS)

    per_seed = {seed: sum(item[-1] == seed for item in conditions) for seed in DEVELOPMENT_SEEDS}
    assert set(per_seed.values()) == {120}

    family_counts = {}
    for family, *_rest in conditions:
        family_counts[family] = family_counts.get(family, 0) + 1
    assert family_counts == {
        "quadratic_role_v10": 200,
        "linear_role_v10": 200,
        "trig_role_v10": 200,
        "interaction_role_v10": 200,
        "null_role_v10": 120,
        "anchor_contamination_null_v10": 120,
        "weak_source_role_v10": 80,
        "dual_role_v10": 80,
    }


def test_phase3e_method_family_contains_frozen_predecessors_ablation_and_v13() -> None:
    assert PHASE3E_METHODS == (
        "scsv-elrc-v11-full",
        "scsv-ncsc",
        "scope-contrast-only",
        "v13-full",
    )
