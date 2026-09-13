from __future__ import annotations

import pytest

from fedfalsify.phase3e_v13_development_runner import (
    AUTHORIZATION_TOKEN,
    DEVELOPMENT_SEEDS,
    FROZEN_PROTOCOL_SHA256,
    PHASE3E_METHODS,
    benchmark_to_v13_fixture,
    condition_key_string,
    gate_checks,
    require_development_authorization,
    scientific_conditions,
    true_role_map,
    validate_checkpoint_groups,
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
    assert FROZEN_PROTOCOL_SHA256 == "2eebcf892e3acd90c9a133f7945850f60cb8a89fd577f2c3ac6011f5f8fbeac7"


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


def test_authorization_fails_closed_until_test_gate_and_exact_token(monkeypatch) -> None:
    monkeypatch.delenv("FEDFALSIFY_PHASE3E_TEST_GATE", raising=False)
    with pytest.raises(RuntimeError):
        require_development_authorization(AUTHORIZATION_TOKEN)
    monkeypatch.setenv("FEDFALSIFY_PHASE3E_TEST_GATE", "PASS")
    with pytest.raises(RuntimeError):
        require_development_authorization("wrong")
    require_development_authorization(AUTHORIZATION_TOKEN)


def _fake_group(condition):
    family, clients, balance, role, noise, seed = condition
    key = condition_key_string(condition)
    return [
        {
            "family": family,
            "num_clients": clients,
            "balance_profile": balance,
            "role_profile": role,
            "noise_ratio": noise,
            "seed": seed,
            "condition_key": key,
            "method": method,
        }
        for method in PHASE3E_METHODS
    ]


def test_resume_accepts_only_complete_unique_four_method_groups() -> None:
    condition = scientific_conditions()[0]
    cleaned, completed = validate_checkpoint_groups(_fake_group(condition))
    assert len(cleaned) == 4
    assert completed == {condition}

    cleaned_partial, completed_partial = validate_checkpoint_groups(_fake_group(condition)[:-1])
    assert cleaned_partial == []
    assert completed_partial == set()

    duplicate = _fake_group(condition) + [_fake_group(condition)[-1]]
    cleaned_duplicate, completed_duplicate = validate_checkpoint_groups(duplicate)
    assert cleaned_duplicate == []
    assert completed_duplicate == set()


def test_gate_has_no_fake_communication_requirement_and_passes_prespecified_thresholds() -> None:
    metrics = {
        "overall_exact_gain": 0.04,
        "bootstrap_ci_low": 0.001,
        "deviation_precision_pooled": 0.995,
        "deviation_recall_pooled": 0.95,
        "shared_precision_pooled": 0.98,
        "shared_recall_pooled": 0.985,
        "null_localized_fp_rate": 0.01,
        "null_shared_fp_rate": 0.01,
        "exact_harm_rate": 0.005,
        "scope_exact_nonnull": 0.95,
        "family_recovery": {
            "quadratic_role_v10": 0.93,
            "linear_role_v10": 0.93,
            "trig_role_v10": 0.93,
            "interaction_role_v10": 0.93,
        },
        "client_recovery": {"4": 0.91, "8": 0.94, "16": 0.96},
        "high_noise_main_deviation_recovery": 0.91,
        "high_noise_main_exact_gain": 0.06,
        "weak_source_recovery": 0.91,
        "dual_role_recovery": 0.91,
        "integrity_violations": 0,
        "complete_conditions": 1200,
        "primary_rows": 4800,
    }
    checks = gate_checks(metrics)
    assert checks
    assert all(checks.values())
    assert not any("communication" in name for name in checks)
