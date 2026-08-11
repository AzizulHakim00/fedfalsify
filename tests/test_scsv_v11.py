import json

from fedfalsify.basis import CandidateEquation
from fedfalsify.scsv_v10_benchmarks import QUADRATIC_DEV_V10, generate_v10_benchmark, v10_catalog
from fedfalsify.scsv_v11 import (
    V11ClientEffectDiagnostic,
    _role_from_client_effects,
    _weak_heredity_pass,
    scsv_elrc_v11_method,
)
from fedfalsify.scsv_v11_forensics import classify_true_deviation
from fedfalsify.scsv_v11_study import DEVELOPMENT_SEEDS, SMOKE_SEED, _scientific_conditions, _validate_seeds


def _effect(client_id, *, positive, estimable=5, positive_folds=5):
    return V11ClientEffectDiagnostic(
        client_id=client_id,
        estimable_folds=estimable,
        positive_folds=positive_folds if positive else 0,
        coefficient_sign_agreement=1.0 if positive else 0.0,
        median_gain=1.0 if positive else -0.1,
        median_coefficient=0.5 if positive else 0.0,
        supported=positive,
    )


def test_v11_seed_firewall_and_matrix_are_fresh():
    conditions = tuple(_scientific_conditions(DEVELOPMENT_SEEDS))
    assert len(conditions) == 600
    assert len(set(conditions)) == 600
    assert SMOKE_SEED == 29001
    assert set(DEVELOPMENT_SEEDS) == {29101, 29102, 29103, 29104, 29105}
    _validate_seeds(DEVELOPMENT_SEEDS, smoke=False)
    _validate_seeds((SMOKE_SEED,), smoke=True)


def test_effect_role_uses_response_effect_not_gate_occupancy():
    effects = (
        _effect("client-1", positive=False),
        _effect("client-2", positive=False),
        _effect("client-3", positive=False),
        _effect("client-4", positive=True),
    )
    role = _role_from_client_effects(QUADRATIC_DEV_V10, effects)
    assert role.admissible
    assert role.role_client_ids == ("client-4",)
    assert role.outside_client_ids == ("client-1", "client-2", "client-3")


def test_effect_role_rejects_nonlocalized_majority_effect():
    effects = (
        _effect("client-1", positive=True),
        _effect("client-2", positive=True),
        _effect("client-3", positive=True),
        _effect("client-4", positive=False),
    )
    role = _role_from_client_effects(QUADRATIC_DEV_V10, effects)
    assert not role.admissible
    assert "not localized" in role.reason


def test_weak_heredity_allows_banked_parent_without_global_insertion():
    core = CandidateEquation(("1", "x1"), (0.0, 0.5), "core")
    assert _weak_heredity_pass("x3^2", core, ("x3^2", "cos(x2)"))
    assert not _weak_heredity_pass("x4^2", core, ("x3^2", "cos(x2)"))


def test_spent_v10_forensic_taxonomy_preserves_boundary():
    term = QUADRATIC_DEV_V10
    row = {
        "accepted_deviations": "",
        "candidate_deviations": term,
        "diagnostics_json": json.dumps([{"term": term, "rejection_reason": "ROLE-NOT-IDENTIFIED"}]),
    }
    assert classify_true_deviation(row, term) == "OCCUPANCY-ROLE-FAILURE"


def test_natural_v11_engineering_smoke_runs_without_integrity_exception():
    generated = generate_v10_benchmark(
        "quadratic_role_v10",
        seed=SMOKE_SEED,
        num_clients=4,
        balance_profile="balanced",
        role_profile="single",
        noise_ratio=0.10,
    )
    output = scsv_elrc_v11_method(
        generated.clients,
        v10_catalog(),
        seed=SMOKE_SEED,
        target_mse=max(generated.noise_std**2 * 2.5, 1e-8),
    )
    assert output.method == "scsv-elrc-v11-full"
    assert set(output.ordinary_anchor_structure).issubset(set(output.final_structure))
    assert len(output.accepted_deviations) <= 2
