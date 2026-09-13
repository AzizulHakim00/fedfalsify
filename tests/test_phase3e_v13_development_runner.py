from __future__ import annotations

import pytest

from fedfalsify.phase3e_v13_development_runner import (
    DEVELOPMENT_SEEDS,
    PHASE3E_METHODS,
    benchmark_to_v13_fixture,
    scientific_conditions,
    true_role_map,
    validate_development_seed_block,
)
from fedfalsify.scsv_v10_benchmarks import (
    LINEAR_DEV_V10,
    QUADRATIC_DEV_V10,
    generate_v10_benchmark,
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


def test_single_role_truth_and_v13_fixture_are_derived_from_frozen_benchmark_metadata() -> None:
    condition = ("quadratic_role_v10", 4, "balanced", "single", 0.10, 29401)
    generated = generate_v10_benchmark(
        condition[0],
        nominal_samples_per_client=100,
        noise_ratio=condition[4],
        seed=condition[5],
        num_clients=condition[1],
        balance_profile=condition[2],
        role_profile=condition[3],
    )
    roles = true_role_map(condition)
    assert roles == {QUADRATIC_DEV_V10: ("client-4",)}

    fixture = benchmark_to_v13_fixture(generated, condition)
    assert fixture.clients == generated.clients
    assert fixture.true_shared_terms == ("1", "x3^2", "sin(x2)", "x1")
    assert fixture.true_localized_terms == (QUADRATIC_DEV_V10,)
    assert fixture.truth_scopes == ((QUADRATIC_DEV_V10, ("client-4",)),)


def test_dual_role_truth_keeps_two_nonoverlapping_client_scopes() -> None:
    condition = ("dual_role_v10", 8, "imbalanced", "quarter", 0.30, 29410)
    assert true_role_map(condition) == {
        QUADRATIC_DEV_V10: ("client-7", "client-8"),
        LINEAR_DEV_V10: ("client-5", "client-6"),
    }
