from __future__ import annotations

import copy

import pytest

from fedfalsify.phase3_development_runner import (
    AUTHORIZATION_TOKEN,
    DEVELOPMENT_SEEDS,
    PHASE3_METHODS,
    condition_key_string,
    gate_checks,
    paired_analysis,
    require_development_authorization,
    scientific_conditions,
    scope_exact_recovery,
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


def test_authorization_fails_closed_until_test_gate_and_explicit_token(monkeypatch):
    monkeypatch.delenv("FEDFALSIFY_PHASE3_TEST_GATE", raising=False)
    with pytest.raises(RuntimeError):
        require_development_authorization(AUTHORIZATION_TOKEN)

    monkeypatch.setenv("FEDFALSIFY_PHASE3_TEST_GATE", "PASS")
    with pytest.raises(RuntimeError):
        require_development_authorization("wrong-token")

    require_development_authorization(AUTHORIZATION_TOKEN)


def test_scope_exact_recovery_requires_exact_term_to_client_role_mapping():
    truth = {"dev-a": ("client-4",), "dev-b": ("client-2", "client-3")}
    assert scope_exact_recovery(truth, truth) == 1.0
    assert scope_exact_recovery({}, {}) == 1.0
    assert scope_exact_recovery({"dev-a": ("client-4",)}, {"dev-a": ("client-3",)}) == 0.0
    assert scope_exact_recovery({"dev-a": ("client-4",)}, {"dev-a": ("client-4",), "extra": ("client-2",)}) == 0.0


def _paired_row(key: str, seed: int, method: str, exact: float) -> dict:
    return {
        "condition_key": key,
        "seed": seed,
        "method": method,
        "exact_recovery": exact,
    }


def test_paired_analysis_counts_repairs_harms_and_is_deterministic():
    rows = [
        _paired_row("a", 29301, PHASE3_METHODS[0], 1.0),
        _paired_row("a", 29301, PHASE3_METHODS[-1], 1.0),
        _paired_row("b", 29301, PHASE3_METHODS[0], 1.0),
        _paired_row("b", 29301, PHASE3_METHODS[-1], 0.0),
        _paired_row("c", 29302, PHASE3_METHODS[0], 0.0),
        _paired_row("c", 29302, PHASE3_METHODS[-1], 1.0),
        _paired_row("d", 29302, PHASE3_METHODS[0], 0.0),
        _paired_row("d", 29302, PHASE3_METHODS[-1], 1.0),
    ]
    first = paired_analysis(rows, bootstrap_reps=500)
    second = paired_analysis(rows, bootstrap_reps=500)
    assert first == second
    assert first["matched_conditions"] == 4
    assert first["repairs"] == 2
    assert first["harms"] == 1
    assert first["exact_gain"] == pytest.approx(0.25)
    assert 0.0 <= first["mcnemar_exact_p"] <= 1.0
    assert 0.0 <= first["seed_sign_flip_p_one_sided"] <= 1.0
    assert len(first["seed_level_gain"]) == 2


def _passing_gate_metrics() -> dict:
    return {
        "overall_exact_gain": 0.03,
        "bootstrap_ci_low": 1e-6,
        "deviation_precision_pooled": 0.99,
        "deviation_recall_pooled": 0.94,
        "shared_precision_pooled": 0.975,
        "shared_recall_pooled": 0.98,
        "null_localized_fp_rate": 0.02,
        "null_shared_fp_rate": 0.02,
        "exact_harm_rate": 0.01,
        "family_recovery": {
            "quadratic_role_v10": 0.92,
            "linear_role_v10": 0.92,
            "trig_role_v10": 0.92,
            "interaction_role_v10": 0.92,
        },
        "client_recovery": {"4": 0.90, "8": 0.93, "16": 0.95},
        "high_noise_main_deviation_recovery": 0.90,
        "high_noise_main_exact_gain": 0.05,
        "weak_source_recovery": 0.90,
        "dual_role_recovery": 0.90,
        "communication_ratio_vs_v11": 1.25,
        "runtime_ratio_vs_v11": 1.50,
        "integrity_violations": 0,
        "complete_conditions": 1200,
        "primary_rows": 4800,
    }


def test_gate_is_conjunctive_and_boundary_values_pass():
    metrics = _passing_gate_metrics()
    checks = gate_checks(metrics)
    assert checks
    assert all(checks.values())

    broken = copy.deepcopy(metrics)
    broken["overall_exact_gain"] = 0.029999
    failed = gate_checks(broken)
    assert failed["overall_exact_gain"] is False
    assert not all(failed.values())

    broken = copy.deepcopy(metrics)
    broken["integrity_violations"] = 1
    assert gate_checks(broken)["integrity_zero"] is False
