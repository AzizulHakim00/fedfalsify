from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from fedfalsify.basis import BasisTerm, CandidateEquation
from fedfalsify.benchmarks import BenchmarkClientDataset
from fedfalsify.scsv_v8 import V8RoleHypothesis
from fedfalsify.scsv_v9 import (
    _evidence_pass,
    _pair_invariant,
    _pooled_delta,
    scsv_rcef_v9_method,
)
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


def _forced_role(datasets):
    n = len(datasets)
    role = (n - 1,)
    outside = tuple(range(n - 1))
    return V8RoleHypothesis(
        term="forced",
        admissible=True,
        role_indices=role,
        outside_indices=outside,
        role_client_ids=(datasets[-1].client_id,),
        outside_client_ids=tuple(item.client_id for item in datasets[:-1]),
        occupancies=tuple([0.0] * (n - 1) + [1.0]),
        separation_gap=1.0,
        role_mean_occupancy=1.0,
        outside_mean_occupancy=0.0,
        reason="forced pre-evidence path",
    )


def _forced_pair(pair_anchor, source, term, *args, **kwargs):
    terms = tuple(pair_anchor.active_terms) + (term,)
    coefficients = tuple(float(value) for value in pair_anchor.coefficients) + (0.5,)
    full = CandidateEquation(terms, coefficients, f"forced-full-{term}")
    reduced = CandidateEquation(terms, coefficients[:-1] + (0.0,), f"forced-reduced-{term}")
    return full, reduced, float(dict(zip(pair_anchor.active_terms, pair_anchor.coefficients))[source]), 0.5


def _forced_refit(*args, **kwargs):
    structure = tuple(args[2])
    return CandidateEquation(structure, tuple(0.1 for _ in structure), "forced-v9-refit"), 0


def _weak_source_clients(shared_beta: float):
    generated = generate_v9_benchmark(
        "weak_source_role_v9",
        seed=SMOKE_SEED,
        num_clients=8,
        balance_profile="balanced",
        role_profile="quarter",
        noise_ratio=0.10,
    )
    catalog = v9_catalog()
    clients = []
    for item in generated.clients:
        x = item.x
        y = (
            0.55 * catalog.get("x1").evaluate(x)
            + 0.65 * catalog.get("sin(x2)").evaluate(x)
            + shared_beta * catalog.get("x4^2").evaluate(x)
            + 0.75 * catalog.get(WEAK_SOURCE_DEV_V9).evaluate(x)
        )
        clients.append(BenchmarkClientDataset(item.client_id, x, y))
    return tuple(clients)


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
        ("x1", "x2^2"),
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


def test_source_absent_anchor_can_pass_explicit_source_qualification_and_be_added_only_with_deviation():
    clients = _weak_source_clients(shared_beta=0.80)
    fake = _fake_anchor(
        ("1", "x1", "sin(x2)"),
        (0.0, 0.55, 0.65),
        ("x1", "sin(x2)", "x4^2"),
    )
    with patch("fedfalsify.scsv_v9.scsv_cert_method", return_value=fake):
        output = scsv_rcef_v9_method(
            clients,
            v9_catalog(),
            seed=SMOKE_SEED,
            target_mse=1e-8,
        )
    assert WEAK_SOURCE_DEV_V9 in output.role_proposed_candidates
    matches = [item for item in output.source_diagnostics if item.source_term == "x4^2"]
    assert len(matches) == 1
    assert not matches[0].source_in_anchor
    assert matches[0].source_in_bank
    assert matches[0].invariant
    assert matches[0].qualified
    assert WEAK_SOURCE_DEV_V9 in output.accepted_deviations
    assert "x4^2" in output.added_sources


def test_source_qualification_failure_blocks_linked_deviation():
    clients = _weak_source_clients(shared_beta=0.0)
    fake = _fake_anchor(
        ("1", "x1", "sin(x2)"),
        (0.0, 0.55, 0.65),
        ("x1", "sin(x2)", "x4^2"),
    )
    with patch("fedfalsify.scsv_v9.scsv_cert_method", return_value=fake):
        output = scsv_rcef_v9_method(
            clients,
            v9_catalog(),
            seed=SMOKE_SEED,
            target_mse=1e-8,
        )
    matches = [item for item in output.source_diagnostics if item.source_term == "x4^2"]
    assert len(matches) == 1
    assert not matches[0].qualified
    assert WEAK_SOURCE_DEV_V9 not in output.accepted_deviations
    assert "x4^2" not in output.added_sources


def test_evidence_fusion_can_rescue_directional_selector_without_overriding_contradiction():
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
        ("x1", "x2^2"),
    )
    role = _forced_role(generated.clients)
    selector_directional = (20, 9.5, 10.0, 0.10, False)
    probe_supported = (20, 8.0, 10.0, -0.10, True)

    common = (
        patch("fedfalsify.scsv_v9.scsv_cert_method", return_value=fake),
        patch("fedfalsify.scsv_v9._role_hypothesis", return_value=role),
        patch("fedfalsify.scsv_v9._estimate_pair", side_effect=_forced_pair),
        patch("fedfalsify.scsv_v9._outside_safety", return_value=(5.0, 5.0, True)),
        patch("fedfalsify.scsv_v9._refit", side_effect=_forced_refit),
    )
    with common[0], common[1], common[2], common[3], common[4], patch(
        "fedfalsify.scsv_v9._conditional_test",
        side_effect=[selector_directional, probe_supported],
    ):
        fused = scsv_rcef_v9_method(
            generated.clients,
            v9_catalog(),
            seed=SMOKE_SEED,
            target_mse=1e-8,
            evidence_fusion=True,
        )
    assert QUADRATIC_DEV_V9 in fused.accepted_deviations
    item = next(item for item in fused.diagnostics if item.term == QUADRATIC_DEV_V9)
    assert item.selector_state == "INCONCLUSIVE-DIRECTIONAL"
    assert item.probe_state == "SUPPORTED"
    assert item.pooled_delta is not None and item.pooled_delta < 0.0

    common = (
        patch("fedfalsify.scsv_v9.scsv_cert_method", return_value=fake),
        patch("fedfalsify.scsv_v9._role_hypothesis", return_value=role),
        patch("fedfalsify.scsv_v9._estimate_pair", side_effect=_forced_pair),
        patch("fedfalsify.scsv_v9._outside_safety", return_value=(5.0, 5.0, True)),
    )
    with common[0], common[1], common[2], common[3], patch(
        "fedfalsify.scsv_v9._conditional_test",
        side_effect=[selector_directional, probe_supported],
    ):
        selector_only = scsv_rcef_v9_method(
            generated.clients,
            v9_catalog(),
            seed=SMOKE_SEED,
            target_mse=1e-8,
            evidence_fusion=False,
        )
    assert QUADRATIC_DEV_V9 not in selector_only.accepted_deviations

    selector_contradicted = (20, 10.5, 10.0, 0.20, False)
    common = (
        patch("fedfalsify.scsv_v9.scsv_cert_method", return_value=fake),
        patch("fedfalsify.scsv_v9._role_hypothesis", return_value=role),
        patch("fedfalsify.scsv_v9._estimate_pair", side_effect=_forced_pair),
        patch("fedfalsify.scsv_v9._outside_safety", return_value=(5.0, 5.0, True)),
    )
    with common[0], common[1], common[2], common[3], patch(
        "fedfalsify.scsv_v9._conditional_test",
        side_effect=[selector_contradicted, (20, 1.0, 10.0, -2.0, True)],
    ):
        contradicted = scsv_rcef_v9_method(
            generated.clients,
            v9_catalog(),
            seed=SMOKE_SEED,
            target_mse=1e-8,
            evidence_fusion=True,
        )
    assert QUADRATIC_DEV_V9 not in contradicted.accepted_deviations
    item = next(item for item in contradicted.diagnostics if item.term == QUADRATIC_DEV_V9)
    assert item.selector_state == "CONTRADICTED"


def test_source_ambiguity_rejects_multiple_positive_deviations_linked_to_same_source():
    generated = generate_v9_benchmark(
        "quadratic_role_v9", seed=SMOKE_SEED, num_clients=4, balance_profile="balanced", role_profile="single", noise_ratio=0.10
    )
    catalog = v9_catalog()
    alt = "I(x2>0.90)*x2^2-alt"
    catalog._terms[alt] = BasisTerm(
        alt,
        lambda x: np.where(x[:, 1] > 0.90, x[:, 1] ** 2, 0.0),
        4,
        "alt",
        kind="exception",
        validity="x2 > 0.90",
        source_term="x2^2",
    )
    fake = _fake_anchor(("1", "x2^2"), (0.0, 0.85), ("x2^2",))
    role = _forced_role(generated.clients)
    with patch("fedfalsify.scsv_v9.scsv_cert_method", return_value=fake), patch(
        "fedfalsify.scsv_v9._role_hypothesis", return_value=role
    ), patch("fedfalsify.scsv_v9._estimate_pair", side_effect=_forced_pair), patch(
        "fedfalsify.scsv_v9._conditional_test", return_value=(20, 8.0, 10.0, -0.2, True)
    ), patch("fedfalsify.scsv_v9._outside_safety", return_value=(5.0, 5.0, True)):
        output = scsv_rcef_v9_method(generated.clients, catalog, seed=SMOKE_SEED, target_mse=1e-8)
    assert output.source_ambiguity
    assert output.accepted_deviations == ()
    assert set(output.final_structure) == set(output.anchor_structure)


def test_global_ambiguity_rejects_more_than_two_positive_distinct_sources():
    generated = generate_v9_benchmark(
        "quadratic_role_v9", seed=SMOKE_SEED, num_clients=4, balance_profile="balanced", role_profile="single", noise_ratio=0.10
    )
    fake = _fake_anchor(
        ("1", "x2^2", "x4", "sin(x3)"),
        (0.0, 0.85, 0.90, 0.75),
        ("x2^2", "x4", "sin(x3)"),
    )
    role = _forced_role(generated.clients)
    with patch("fedfalsify.scsv_v9.scsv_cert_method", return_value=fake), patch(
        "fedfalsify.scsv_v9._role_hypothesis", return_value=role
    ), patch("fedfalsify.scsv_v9._estimate_pair", side_effect=_forced_pair), patch(
        "fedfalsify.scsv_v9._conditional_test", return_value=(20, 8.0, 10.0, -0.2, True)
    ), patch("fedfalsify.scsv_v9._outside_safety", return_value=(5.0, 5.0, True)):
        output = scsv_rcef_v9_method(generated.clients, v9_catalog(), seed=SMOKE_SEED, target_mse=1e-8)
    assert output.global_ambiguity
    assert output.accepted_deviations == ()
    assert set(output.final_structure) == set(output.anchor_structure)


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
