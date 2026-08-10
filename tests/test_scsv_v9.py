from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from fedfalsify.basis import CandidateEquation
from fedfalsify.scsv_v9 import _evidence_pass, _pair_invariant, _pooled_delta, scsv_rcef_v9_method
from fedfalsify.scsv_v9_benchmarks import (
    QUADRATIC_DEV_V9,
    WEAK_SOURCE_DEV_V9,
    generate_v9_benchmark,
    v9_catalog,
)
from fedfalsify.scsv_v9_study import DEVELOPMENT_SEEDS, SMOKE_SEED, _scientific_conditions


def _fake_anchor(structure, coefficients, bank_terms):
    candidate = CandidateEquation(tuple(structure), tuple(coefficients), "fake-v9-anchor")
    return SimpleNamespace(
        candidate=candidate,
        selector_structure=tuple(structure),
        selector_profile=SimpleNamespace(terms=tuple(structure), coefficients=tuple(coefficients)),
        bank=SimpleNamespace(candidate_terms=tuple(bank_terms)),
        communication_bytes=0,
        runtime_seconds=0.0,
        stop_reason="forced engineering anchor",
    )


def test_v9_seed_and_matrix_firewall_is_nonredundant():
    conditions = tuple(_scientific_conditions(DEVELOPMENT_SEEDS))
    assert len(conditions) == 600
    assert len(set(conditions)) == 600
    assert SMOKE_SEED not in {item[-1] for item in conditions}
    assert set(item[-1] for item in conditions) == set(DEVELOPMENT_SEEDS)


def test_cross_view_evidence_requires_no_contradiction():
    assert _evidence_pass("SUPPORTED", "INCONCLUSIVE-DIRECTIONAL", -0.1)
    assert _evidence_pass("INCONCLUSIVE-DIRECTIONAL", "SUPPORTED", -0.1)
    assert _evidence_pass("INCONCLUSIVE-DIRECTIONAL", "INCONCLUSIVE-DIRECTIONAL", -0.1)
    assert not _evidence_pass("CONTRADICTED", "SUPPORTED", -1.0)
    assert not _evidence_pass("SUPPORTED", "CONTRADICTED", -1.0)
    assert not _evidence_pass("SUPPORTED", "SUPPORTED", 0.0)


def test_pooled_delta_uses_combined_heldout_support_once():
    value = _pooled_delta(20, 8.0, 10.0, 20, 8.0, 10.0)
    expected = np.log(16.0 / 20.0) + np.log(40.0) / 40.0
    assert value is not None
    assert abs(value - expected) < 1e-12
    assert value < 0.0


def test_pair_invariant_changes_only_tested_term():
    full = CandidateEquation(("1", "x2^2", QUADRATIC_DEV_V9), (0.1, 0.8, 0.5), "full")
    reduced = CandidateEquation(("1", "x2^2", QUADRATIC_DEV_V9), (0.1, 0.8, 0.0), "reduced")
    bad = CandidateEquation(("1", "x2^2", QUADRATIC_DEV_V9), (0.1, 0.7, 0.0), "bad")
    assert _pair_invariant(full, reduced, QUADRATIC_DEV_V9)
    assert not _pair_invariant(full, bad, QUADRATIC_DEV_V9)


def test_role_proposer_can_admit_deviation_absent_from_response_bank():
    generated = generate_v9_benchmark(
        "quadratic_role_v9",
        seed=SMOKE_SEED,
        num_clients=4,
        balance_profile="balanced",
        role_profile="single",
        noise_ratio=0.10,
    )
    fake = _fake_anchor(
        ("1", "x1", "x2^2", "sin(x3)"),
        (0.0, 0.55, 0.85, 0.75),
        ("x1", "x2^2", "sin(x3)"),
    )
    with patch("fedfalsify.scsv_v9.scsv_cert_method", return_value=fake):
        output = scsv_rcef_v9_method(
            generated.clients,
            v9_catalog(),
            seed=SMOKE_SEED,
            target_mse=max(generated.noise_std**2 * 2.5, 1e-8),
        )
    assert QUADRATIC_DEV_V9 not in fake.bank.candidate_terms
    assert QUADRATIC_DEV_V9 in output.role_proposed_candidates
    matches = [item for item in output.diagnostics if item.term == QUADRATIC_DEV_V9]
    assert len(matches) == 1
    assert matches[0].role_proposed
    assert matches[0].role_admissible
    assert matches[0].pair_invariant


def test_source_absent_anchor_uses_explicit_source_qualification_path():
    generated = generate_v9_benchmark(
        "weak_source_role_v9",
        seed=SMOKE_SEED,
        num_clients=8,
        balance_profile="balanced",
        role_profile="quarter",
        noise_ratio=0.10,
    )
    fake = _fake_anchor(
        ("1", "x1", "sin(x2)"),
        (0.0, 0.55, 0.65),
        ("x1", "sin(x2)", "x4^2"),
    )
    with patch("fedfalsify.scsv_v9.scsv_cert_method", return_value=fake):
        output = scsv_rcef_v9_method(
            generated.clients,
            v9_catalog(),
            seed=SMOKE_SEED,
            target_mse=max(generated.noise_std**2 * 2.5, 1e-8),
        )
    assert WEAK_SOURCE_DEV_V9 in output.role_proposed_candidates
    matches = [item for item in output.source_diagnostics if item.source_term == "x4^2"]
    assert len(matches) == 1
    assert not matches[0].source_in_anchor
    assert matches[0].source_in_bank
    assert matches[0].invariant
    if "x4^2" in output.added_sources:
        assert matches[0].qualified
        assert WEAK_SOURCE_DEV_V9 in output.accepted_deviations


def test_null_and_diffuse_null_do_not_require_a_true_role_label():
    for family in ("null_role_v9", "diffuse_null_v9"):
        generated = generate_v9_benchmark(
            family,
            seed=SMOKE_SEED,
            num_clients=8,
            balance_profile="balanced",
            role_profile="none",
            noise_ratio=0.10,
        )
        assert generated.true_deviations == ()
