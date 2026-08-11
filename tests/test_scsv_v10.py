from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from fedfalsify.basis import BasisTerm, CandidateEquation
from fedfalsify.scsv_v8 import V8RoleHypothesis
from fedfalsify.scsv_v10 import (
    V10SourceDiagnostic,
    _consensus_pass,
    _pair_invariant,
    scsv_aqcc_v10_method,
)
from fedfalsify.scsv_v10_benchmarks import (
    QUADRATIC_DEV_V10,
    WEAK_SOURCE_DEV_V10,
    generate_v10_benchmark,
    v10_catalog,
)
from fedfalsify.scsv_v10_study import DEVELOPMENT_SEEDS, SMOKE_SEED, _scientific_conditions


def _fake_anchor(structure, coefficients, bank_terms):
    candidate = CandidateEquation(tuple(structure), tuple(coefficients), "fake-v10-anchor")
    return SimpleNamespace(
        candidate=candidate,
        selector_structure=tuple(structure),
        selector_profile=SimpleNamespace(terms=tuple(structure), coefficients=tuple(coefficients)),
        bank=SimpleNamespace(candidate_terms=tuple(bank_terms)),
        communication_bytes=0,
        runtime_seconds=0.0,
        stop_reason="forced v10 engineering anchor",
    )


def _forced_role(datasets, *, role_count=1):
    n = len(datasets)
    role = tuple(range(n - role_count, n))
    outside = tuple(range(n - role_count))
    return V8RoleHypothesis(
        term="forced",
        admissible=True,
        role_indices=role,
        outside_indices=outside,
        role_client_ids=tuple(datasets[i].client_id for i in role),
        outside_client_ids=tuple(datasets[i].client_id for i in outside),
        occupancies=tuple([0.0] * len(outside) + [1.0] * len(role)),
        separation_gap=1.0,
        role_mean_occupancy=1.0,
        outside_mean_occupancy=0.0,
        reason="forced pre-evidence v10 role",
    )


def _forced_pair(pair_anchor, source, term, *args, **kwargs):
    terms = tuple(pair_anchor.active_terms) + (term,)
    coefficients = tuple(float(value) for value in pair_anchor.coefficients) + (0.5,)
    full = CandidateEquation(terms, coefficients, f"forced-v10-full-{term}")
    reduced = CandidateEquation(terms, coefficients[:-1] + (0.0,), f"forced-v10-reduced-{term}")
    source_coef = float(dict(zip(pair_anchor.active_terms, pair_anchor.coefficients))[source])
    return full, reduced, source_coef, 0.5


def _forced_refit(*args, **kwargs):
    structure = tuple(args[2])
    return CandidateEquation(structure, tuple(0.1 for _ in structure), "forced-v10-refit"), 0


def _qualified_source(source="x3^2"):
    return V10SourceDiagnostic(
        source_term=source,
        source_in_core_anchor=True,
        source_in_bank=True,
        source_coefficient=0.8,
        selector_support=0,
        selector_full_sse=None,
        selector_reduced_sse=None,
        selector_delta=None,
        selector_state="SUPPORTED",
        probe_support=0,
        probe_full_sse=None,
        probe_reduced_sse=None,
        probe_delta=None,
        probe_state="SUPPORTED",
        pooled_delta=-1.0,
        client_gains=(),
        client_median_gain=1.0,
        client_positive_fraction=1.0,
        qualified=True,
        invariant=True,
    )


def test_v10_seed_and_matrix_firewall_is_nonredundant():
    conditions = tuple(_scientific_conditions(DEVELOPMENT_SEEDS))
    assert len(conditions) == 600
    assert len(set(conditions)) == 600
    assert SMOKE_SEED not in {item[-1] for item in conditions}
    assert set(item[-1] for item in conditions) == set(DEVELOPMENT_SEEDS)


def test_v10_consensus_requires_negative_pooled_delta_and_positive_client_median():
    assert _consensus_pass(-0.1, 0.01)
    assert not _consensus_pass(0.0, 1.0)
    assert not _consensus_pass(-1.0, 0.0)
    assert not _consensus_pass(None, 1.0)


def test_pair_invariant_changes_only_tested_exception():
    full = CandidateEquation(("1", "x3^2", QUADRATIC_DEV_V10), (0.1, 0.8, 0.5), "full")
    reduced = CandidateEquation(("1", "x3^2", QUADRATIC_DEV_V10), (0.1, 0.8, 0.0), "reduced")
    bad = CandidateEquation(("1", "x3^2", QUADRATIC_DEV_V10), (0.1, 0.7, 0.0), "bad")
    assert _pair_invariant(full, reduced, QUADRATIC_DEV_V10)
    assert not _pair_invariant(full, bad, QUADRATIC_DEV_V10)


def test_quarantine_removes_uncertified_anchor_exception_but_preserves_ordinary_anchor():
    generated = generate_v10_benchmark(
        "quadratic_role_v10", seed=SMOKE_SEED, num_clients=4,
        balance_profile="balanced", role_profile="single", noise_ratio=0.10,
    )
    fake = _fake_anchor(
        ("1", "x1", "x3^2", QUADRATIC_DEV_V10),
        (0.0, 0.56, 0.86, 0.2),
        ("x1", "x3^2", QUADRATIC_DEV_V10),
    )
    denied_role = V8RoleHypothesis(
        term=QUADRATIC_DEV_V10,
        admissible=False,
        role_indices=(),
        outside_indices=tuple(range(4)),
        role_client_ids=(),
        outside_client_ids=tuple(item.client_id for item in generated.clients),
        occupancies=(0.2, 0.2, 0.2, 0.2),
        separation_gap=0.0,
        role_mean_occupancy=0.0,
        outside_mean_occupancy=0.2,
        reason="forced no role",
    )
    with patch("fedfalsify.scsv_v10.scsv_cert_method", return_value=fake), patch(
        "fedfalsify.scsv_v10._role_hypothesis", return_value=denied_role
    ), patch("fedfalsify.scsv_v10._refit", side_effect=_forced_refit):
        output = scsv_aqcc_v10_method(
            generated.clients, v10_catalog(), seed=SMOKE_SEED, target_mse=1e-8,
            quarantine_anchor=True, split_veto=False,
        )
    assert QUADRATIC_DEV_V10 in output.quarantined_anchor_exceptions
    assert QUADRATIC_DEV_V10 in output.removed_anchor_exceptions
    assert QUADRATIC_DEV_V10 not in output.final_structure
    assert {"1", "x1", "x3^2"}.issubset(set(output.final_structure))


def test_true_anchor_exception_can_be_recertified_and_retained():
    generated = generate_v10_benchmark(
        "quadratic_role_v10", seed=SMOKE_SEED, num_clients=4,
        balance_profile="balanced", role_profile="single", noise_ratio=0.10,
    )
    fake = _fake_anchor(
        ("1", "x1", "x3^2", QUADRATIC_DEV_V10),
        (0.0, 0.56, 0.86, 0.5),
        ("x1", "x3^2", QUADRATIC_DEV_V10),
    )
    role = _forced_role(generated.clients)
    summaries = [
        (20, 8.0, 10.0, -0.1, "SUPPORTED"),
        (20, 10.5, 10.0, 0.2, "CONTRADICTED"),
    ]
    with patch("fedfalsify.scsv_v10.scsv_cert_method", return_value=fake), patch(
        "fedfalsify.scsv_v10._role_hypothesis", return_value=role
    ), patch("fedfalsify.scsv_v10._estimate_pair", side_effect=_forced_pair), patch(
        "fedfalsify.scsv_v10._conditional_summary", side_effect=summaries
    ), patch("fedfalsify.scsv_v10._client_gains", return_value=((2.0,), 2.0, 1.0)), patch(
        "fedfalsify.scsv_v10._outside_safety", return_value=(5.0, 5.0, True)
    ), patch("fedfalsify.scsv_v10._refit", side_effect=_forced_refit):
        output = scsv_aqcc_v10_method(
            generated.clients, v10_catalog(), seed=SMOKE_SEED, target_mse=1e-8,
            quarantine_anchor=True, split_veto=False,
        )
    assert QUADRATIC_DEV_V10 in output.accepted_deviations
    assert QUADRATIC_DEV_V10 in output.recertified_anchor_exceptions
    assert QUADRATIC_DEV_V10 in output.final_structure
    item = next(item for item in output.diagnostics if item.term == QUADRATIC_DEV_V10)
    assert item.probe_state == "CONTRADICTED"
    assert item.client_median_gain == 2.0


def test_client_consensus_rescues_split_direction_disagreement_while_split_veto_rejects():
    generated = generate_v10_benchmark(
        "quadratic_role_v10", seed=SMOKE_SEED, num_clients=4,
        balance_profile="balanced", role_profile="single", noise_ratio=0.10,
    )
    fake = _fake_anchor(("1", "x1", "x3^2"), (0.0, 0.56, 0.86), ("x1", "x3^2"))
    role = _forced_role(generated.clients)
    summaries = [
        (20, 10.5, 10.0, 0.2, "CONTRADICTED"),
        (20, 4.0, 10.0, -0.5, "SUPPORTED"),
    ]
    common = (
        patch("fedfalsify.scsv_v10.scsv_cert_method", return_value=fake),
        patch("fedfalsify.scsv_v10._role_hypothesis", return_value=role),
        patch("fedfalsify.scsv_v10._estimate_pair", side_effect=_forced_pair),
        patch("fedfalsify.scsv_v10._outside_safety", return_value=(5.0, 5.0, True)),
        patch("fedfalsify.scsv_v10._client_gains", return_value=((4.0,), 4.0, 1.0)),
        patch("fedfalsify.scsv_v10._refit", side_effect=_forced_refit),
    )
    with common[0], common[1], common[2], common[3], common[4], common[5], patch(
        "fedfalsify.scsv_v10._conditional_summary", side_effect=summaries
    ):
        full = scsv_aqcc_v10_method(
            generated.clients, v10_catalog(), seed=SMOKE_SEED, target_mse=1e-8,
            quarantine_anchor=True, split_veto=False,
        )
    assert QUADRATIC_DEV_V10 in full.accepted_deviations

    common = (
        patch("fedfalsify.scsv_v10.scsv_cert_method", return_value=fake),
        patch("fedfalsify.scsv_v10._role_hypothesis", return_value=role),
        patch("fedfalsify.scsv_v10._estimate_pair", side_effect=_forced_pair),
        patch("fedfalsify.scsv_v10._outside_safety", return_value=(5.0, 5.0, True)),
        patch("fedfalsify.scsv_v10._client_gains", return_value=((4.0,), 4.0, 1.0)),
    )
    with common[0], common[1], common[2], common[3], common[4], patch(
        "fedfalsify.scsv_v10._conditional_summary", side_effect=summaries
    ):
        split = scsv_aqcc_v10_method(
            generated.clients, v10_catalog(), seed=SMOKE_SEED, target_mse=1e-8,
            quarantine_anchor=True, split_veto=True,
        )
    assert QUADRATIC_DEV_V10 not in split.accepted_deviations


def test_positive_pooled_evidence_is_rejected_when_client_median_is_nonpositive():
    generated = generate_v10_benchmark(
        "quadratic_role_v10", seed=SMOKE_SEED, num_clients=4,
        balance_profile="balanced", role_profile="single", noise_ratio=0.10,
    )
    fake = _fake_anchor(("1", "x1", "x3^2"), (0.0, 0.56, 0.86), ("x1", "x3^2"))
    role = _forced_role(generated.clients)
    with patch("fedfalsify.scsv_v10.scsv_cert_method", return_value=fake), patch(
        "fedfalsify.scsv_v10._role_hypothesis", return_value=role
    ), patch("fedfalsify.scsv_v10._estimate_pair", side_effect=_forced_pair), patch(
        "fedfalsify.scsv_v10._conditional_summary",
        side_effect=[(20, 8.0, 10.0, -0.1, "SUPPORTED"), (20, 8.0, 10.0, -0.1, "SUPPORTED")],
    ), patch("fedfalsify.scsv_v10._client_gains", return_value=((-0.1,), -0.1, 0.0)), patch(
        "fedfalsify.scsv_v10._outside_safety", return_value=(5.0, 5.0, True)
    ):
        output = scsv_aqcc_v10_method(
            generated.clients, v10_catalog(), seed=SMOKE_SEED, target_mse=1e-8,
        )
    assert QUADRATIC_DEV_V10 not in output.accepted_deviations
    item = next(item for item in output.diagnostics if item.term == QUADRATIC_DEV_V10)
    assert item.rejection_reason == "CLIENT-MEDIAN-CONTRADICTED"


def test_source_qualification_failure_blocks_weak_source_deviation():
    generated = generate_v10_benchmark(
        "weak_source_role_v10", seed=SMOKE_SEED, num_clients=8,
        balance_profile="balanced", role_profile="quarter", noise_ratio=0.10,
    )
    fake = _fake_anchor(("1", "x1", "sin(x2)"), (0.0, 0.55, 0.65), ("x1", "sin(x2)", "x4^2"))
    role = _forced_role(generated.clients, role_count=2)
    failed_source = V10SourceDiagnostic(
        source_term="x4^2", source_in_core_anchor=False, source_in_bank=True,
        source_coefficient=0.2, selector_support=20, selector_full_sse=10.5,
        selector_reduced_sse=10.0, selector_delta=0.2, selector_state="CONTRADICTED",
        probe_support=20, probe_full_sse=9.5, probe_reduced_sse=10.0,
        probe_delta=0.1, probe_state="INCONCLUSIVE-DIRECTIONAL", pooled_delta=0.05,
        client_gains=(-0.2, 0.1, 0.1, 0.1, 0.1, 0.1), client_median_gain=0.1,
        client_positive_fraction=5/6, qualified=False, invariant=True,
    )
    with patch("fedfalsify.scsv_v10.scsv_cert_method", return_value=fake), patch(
        "fedfalsify.scsv_v10._role_hypothesis", return_value=role
    ), patch("fedfalsify.scsv_v10._qualify_source", return_value=(failed_source, None)):
        output = scsv_aqcc_v10_method(
            generated.clients, v10_catalog(), seed=SMOKE_SEED, target_mse=1e-8,
        )
    assert WEAK_SOURCE_DEV_V10 not in output.accepted_deviations
    item = next(item for item in output.diagnostics if item.term == WEAK_SOURCE_DEV_V10)
    assert item.rejection_reason == "SOURCE-NOT-QUALIFIED"


def test_source_ambiguity_rejects_multiple_positive_exceptions_linked_to_same_source():
    generated = generate_v10_benchmark(
        "quadratic_role_v10", seed=SMOKE_SEED, num_clients=4,
        balance_profile="balanced", role_profile="single", noise_ratio=0.10,
    )
    catalog = v10_catalog()
    alt = "I(x3<-1.10)*x3^2-alt"
    catalog._terms[alt] = BasisTerm(
        alt, lambda x: np.where(x[:, 2] < -1.10, x[:, 2] ** 2, 0.0), 4, "alt",
        kind="exception", validity="x3 < -1.10", source_term="x3^2",
    )
    fake = _fake_anchor(("1", "x3^2"), (0.0, 0.86), ("x3^2",))
    role = _forced_role(generated.clients)
    with patch("fedfalsify.scsv_v10.scsv_cert_method", return_value=fake), patch(
        "fedfalsify.scsv_v10._role_hypothesis", return_value=role
    ), patch("fedfalsify.scsv_v10._estimate_pair", side_effect=_forced_pair), patch(
        "fedfalsify.scsv_v10._conditional_summary", return_value=(20, 8.0, 10.0, -0.2, "SUPPORTED")
    ), patch("fedfalsify.scsv_v10._client_gains", return_value=((2.0,), 2.0, 1.0)), patch(
        "fedfalsify.scsv_v10._outside_safety", return_value=(5.0, 5.0, True)
    ):
        output = scsv_aqcc_v10_method(generated.clients, catalog, seed=SMOKE_SEED, target_mse=1e-8)
    assert output.source_ambiguity
    assert output.accepted_deviations == ()


def test_natural_v10_smoke_families_run_without_integrity_exception():
    for family, clients, role, noise in (
        ("quadratic_role_v10", 4, "single", 0.10),
        ("anchor_contamination_null_v10", 8, "none", 0.30),
        ("weak_source_role_v10", 8, "quarter", 0.10),
        ("dual_role_v10", 8, "quarter", 0.10),
    ):
        generated = generate_v10_benchmark(
            family, seed=SMOKE_SEED, num_clients=clients, balance_profile="balanced",
            role_profile=role, noise_ratio=noise,
        )
        output = scsv_aqcc_v10_method(
            generated.clients, v10_catalog(), seed=SMOKE_SEED,
            target_mse=max(generated.noise_std**2 * 2.5, 1e-8),
        )
        assert set(output.ordinary_anchor_structure).issubset(set(output.final_structure))
