from __future__ import annotations

import os

import pytest

from fedfalsify.phase3_development_runner import (
    DEVELOPMENT_SEEDS,
    PHASE3_METHODS,
    condition_key_string,
    scientific_conditions,
    validate_checkpoint_groups,
    validate_development_seed_block,
)


def test_development_seed_block_is_exact_and_final_namespace_is_excluded():
    assert DEVELOPMENT_SEEDS == tuple(range(29301, 29311))
    validate_development_seed_block(DEVELOPMENT_SEEDS)

    with pytest.raises(ValueError):
        validate_development_seed_block((29301,))
    with pytest.raises(ValueError):
        validate_development_seed_block(tuple(range(29300, 29310)))
    with pytest.raises(ValueError):
        validate_development_seed_block(tuple(range(11001, 11011)))


def test_scientific_matrix_has_120_conditions_per_seed_and_1200_total():
    conditions = scientific_conditions(DEVELOPMENT_SEEDS)
    assert len(conditions) == 1200
    assert len(set(conditions)) == 1200

    by_seed = {seed: 0 for seed in DEVELOPMENT_SEEDS}
    for condition in conditions:
        by_seed[condition[-1]] += 1
    assert set(by_seed.values()) == {120}


def test_scientific_matrix_uses_only_legal_v10_geometries():
    conditions = scientific_conditions(DEVELOPMENT_SEEDS)
    for family, clients, balance, role, noise, seed in conditions:
        assert clients in {4, 8, 16}
        assert balance in {"balanced", "imbalanced"}
        assert noise in {0.10, 0.30}
        assert seed in DEVELOPMENT_SEEDS

        if family in {"null_role_v10", "anchor_contamination_null_v10"}:
            assert role == "none"
        elif family in {"weak_source_role_v10", "dual_role_v10"}:
            assert clients in {8, 16}
            assert role == "quarter"
        else:
            assert family in {
                "quadratic_role_v10",
                "linear_role_v10",
                "trig_role_v10",
                "interaction_role_v10",
            }
            if clients == 4:
                assert role == "single"
            else:
                assert role in {"single", "quarter"}


def _row(condition, method):
    family, clients, balance, role, noise, seed = condition
    return {
        "family": family,
        "num_clients": clients,
        "balance_profile": balance,
        "role_profile": role,
        "noise_ratio": noise,
        "seed": seed,
        "method": method,
        "condition_key": condition_key_string(condition),
        "integrity_violations": 0,
    }


def test_checkpoint_keeps_only_complete_unique_authorized_four_method_groups():
    condition = scientific_conditions(DEVELOPMENT_SEEDS)[0]
    complete = [_row(condition, method) for method in PHASE3_METHODS]
    cleaned, completed = validate_checkpoint_groups(complete)
    assert len(cleaned) == 4
    assert completed == {condition}

    partial = complete[:-1]
    cleaned, completed = validate_checkpoint_groups(partial)
    assert cleaned == []
    assert completed == set()

    duplicate = complete + [dict(complete[0])]
    cleaned, completed = validate_checkpoint_groups(duplicate)
    assert cleaned == []
    assert completed == set()

    unauthorized = [dict(row) for row in complete]
    for row in unauthorized:
        row["seed"] = 29300
    cleaned, completed = validate_checkpoint_groups(unauthorized)
    assert cleaned == []
    assert completed == set()
