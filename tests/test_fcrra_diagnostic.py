from __future__ import annotations

import numpy as np
import pytest

from fedfalsify.basis import CandidateEquation
from fedfalsify.benchmarks import benchmark_catalog
from fedfalsify.crossfit_redesign import partition_clients
from fedfalsify.crossfit_surrogate import split_selector_probe
from fedfalsify.fcrra_diagnostic import (
    _anchor_discovery_candidate,
    _augment_frozen_anchor,
    _outside_selector_differences,
    _residual_exception_coefficient,
    _role_indices,
    fcrra_diagnostic_method,
)
from fedfalsify.fcrra_spent_study import (
    SMOKE_SEED,
    SPENT_DIAGNOSTIC_SEEDS,
    _validate_seeds,
    run_study,
    summarize,
)
from fedfalsify.scsv_diagnostic import _build_packets
from fedfalsify.scsv_v6 import scsv_cert_method
from fedfalsify.scsv_v6_independent import generate_independent_benchmark

EXCEPTION = "I(x3>1)*x3^2"


def _generated(scenario: str, *, profile: str = "balanced"):
    return generate_independent_benchmark(
        "cubic_cross",
        scenario=scenario,
        nominal_samples_per_client=100,
        noise_ratio=0.20,
        seed=SMOKE_SEED,
        num_clients=4,
        balance_profile=profile,
    )


def _target_mse(generated) -> float:
    return max(generated.noise_std**2 * 2.5, 1e-8)


def _without_exception(candidate: CandidateEquation) -> CandidateEquation:
    kept = [
        (term, coefficient)
        for term, coefficient in zip(candidate.active_terms, candidate.coefficients)
        if term != EXCEPTION
    ]
    return CandidateEquation(
        tuple(term for term, _ in kept),
        tuple(float(coefficient) for _, coefficient in kept),
        "test-missing-exception-anchor",
    )


def test_fcrra_seed_boundary_is_spent_or_engineering_only() -> None:
    assert SMOKE_SEED == 22001
    assert SPENT_DIAGNOSTIC_SEEDS == (20101, 20102, 20103, 20104, 20105)
    _validate_seeds((SMOKE_SEED,), smoke=True)
    _validate_seeds(SPENT_DIAGNOSTIC_SEEDS, smoke=False)
    with pytest.raises(ValueError):
        _validate_seeds((SMOKE_SEED,), smoke=False)
    with pytest.raises(ValueError):
        _validate_seeds((22101,), smoke=True)
    with pytest.raises(ValueError):
        _validate_seeds((22101,), smoke=False)


def test_residual_gamma_matches_direct_eligible_discovery_residual() -> None:
    generated = _generated("exception", profile="imbalanced")
    catalog = benchmark_catalog(scenario="exception")
    anchor = scsv_cert_method(
        generated.clients,
        catalog,
        seed=SMOKE_SEED,
        max_terms=6,
        target_mse=_target_mse(generated),
        min_repair_score=0.05,
        use_score_proposer=True,
    )
    discovery_anchor = _without_exception(_anchor_discovery_candidate(anchor))
    partitions = partition_clients(
        generated.clients, seed=SMOKE_SEED, validation_fraction=0.30
    )
    selectors, probes = split_selector_probe(partitions, seed=SMOKE_SEED)
    names = tuple(catalog.names())
    all_terms = ("1",) + tuple(term for term in names if term != "1")
    fit_packets, _, _, _ = _build_packets(
        partitions, selectors, probes, catalog, all_terms
    )
    eligible = _role_indices(fit_packets, all_terms, EXCEPTION)
    assert eligible == (3,)
    numerator, denominator, gamma = _residual_exception_coefficient(
        fit_packets, all_terms, discovery_anchor, EXCEPTION, eligible
    )

    direct_num = 0.0
    direct_den = 0.0
    term = catalog.get(EXCEPTION)
    for index in eligible:
        dataset = partitions[index].discovery
        e = np.asarray(term.evaluate(dataset.x), dtype=float)
        residual = dataset.y - discovery_anchor.predict(dataset.x, catalog)
        direct_num += float(e @ residual)
        direct_den += float(e @ e)
    expected = direct_num / (direct_den + 1e-10)
    assert np.isclose(numerator, direct_num, rtol=1e-10, atol=1e-10)
    assert np.isclose(denominator, direct_den, rtol=1e-10, atol=1e-10)
    assert np.isclose(gamma, expected, rtol=1e-10, atol=1e-10)


def test_frozen_core_augmentation_preserves_shared_coefficients_and_outside_predictions() -> None:
    generated = _generated("exception", profile="imbalanced")
    catalog = benchmark_catalog(scenario="exception")
    anchor = scsv_cert_method(
        generated.clients,
        catalog,
        seed=SMOKE_SEED,
        max_terms=6,
        target_mse=_target_mse(generated),
        min_repair_score=0.05,
        use_score_proposer=True,
    )
    discovery_anchor = _without_exception(_anchor_discovery_candidate(anchor))
    partitions = partition_clients(
        generated.clients, seed=SMOKE_SEED, validation_fraction=0.30
    )
    selectors, probes = split_selector_probe(partitions, seed=SMOKE_SEED)
    names = tuple(catalog.names())
    all_terms = ("1",) + tuple(term for term in names if term != "1")
    fit_packets, selector_packets, _, _ = _build_packets(
        partitions, selectors, probes, catalog, all_terms
    )
    discovery_eligible = _role_indices(fit_packets, all_terms, EXCEPTION)
    selector_eligible = _role_indices(selector_packets, all_terms, EXCEPTION)
    _, _, gamma = _residual_exception_coefficient(
        fit_packets, all_terms, discovery_anchor, EXCEPTION, discovery_eligible
    )
    augmented = _augment_frozen_anchor(
        discovery_anchor, catalog, EXCEPTION, gamma
    )
    anchor_map = dict(zip(discovery_anchor.active_terms, discovery_anchor.coefficients))
    augmented_map = dict(zip(augmented.active_terms, augmented.coefficients))
    for term, coefficient in anchor_map.items():
        assert augmented_map[term] == coefficient
    sse_diff, prediction_diff = _outside_selector_differences(
        discovery_anchor,
        augmented,
        selectors,
        selector_packets,
        all_terms,
        selector_eligible,
        catalog,
    )
    assert sse_diff <= 1e-10
    assert prediction_diff <= 1e-10


def test_fcrra_rejects_helper_reaugmentation_of_selected_exception() -> None:
    generated = _generated("exception", profile="imbalanced")
    catalog = benchmark_catalog(scenario="exception")
    anchor = scsv_cert_method(
        generated.clients,
        catalog,
        seed=SMOKE_SEED,
        max_terms=6,
        target_mse=_target_mse(generated),
        min_repair_score=0.05,
        use_score_proposer=True,
    )
    discovery_anchor = _anchor_discovery_candidate(anchor)
    if EXCEPTION in discovery_anchor.active_terms:
        with pytest.raises(ValueError):
            _augment_frozen_anchor(discovery_anchor, catalog, EXCEPTION, 0.1)


def test_fcrra_non_exception_is_exact_frozen_v6_identity() -> None:
    generated = _generated("complementary")
    catalog = benchmark_catalog(scenario="complementary")
    frozen = scsv_cert_method(
        generated.clients,
        catalog,
        seed=SMOKE_SEED,
        max_terms=6,
        target_mse=_target_mse(generated),
        min_repair_score=0.05,
        use_score_proposer=True,
    )
    output = fcrra_diagnostic_method(
        generated.clients,
        catalog,
        seed=SMOKE_SEED,
        max_terms=6,
        target_mse=_target_mse(generated),
        min_repair_score=0.05,
    )
    assert output.exception_term is None
    assert output.attempted is False
    assert output.augmentation_accepted is False
    assert output.final_structure == frozen.selector_structure
    assert output.candidate.active_terms == frozen.candidate.active_terms
    assert np.allclose(output.candidate.coefficients, frozen.candidate.coefficients)


def test_fcrra_never_deletes_anchor_and_accepted_case_keeps_core_coefficients() -> None:
    generated = _generated("exception", profile="imbalanced")
    catalog = benchmark_catalog(scenario="exception")
    output = fcrra_diagnostic_method(
        generated.clients,
        catalog,
        seed=SMOKE_SEED,
        max_terms=6,
        target_mse=_target_mse(generated),
        min_repair_score=0.05,
    )
    assert set(output.anchor_structure).issubset(set(output.final_structure))
    assert len(output.final_structure) <= 6
    if output.augmentation_accepted:
        assert output.exception_term == EXCEPTION
        assert output.eligible_discovery_clients
        assert output.eligible_selector_clients
        assert output.augmented_role_information_score < output.anchor_role_information_score
        assert output.outside_selector_sse_max_difference <= 1e-10
        assert output.outside_selector_prediction_max_difference <= 1e-10
        anchor_map = dict(
            zip(output.anchor_structure, output.anchor_discovery_coefficients)
        )
        final_map = dict(zip(output.final_structure, output.final_coefficients))
        for term, coefficient in anchor_map.items():
            assert final_map[term] == coefficient


def test_fcrra_smoke_is_engineering_only_and_signal_not_evaluated() -> None:
    rows = run_study(seeds=(SMOKE_SEED,), smoke=True)
    assert len(rows) == 3
    assert {row.seed for row in rows} == {SMOKE_SEED}
    assert {row.method for row in rows} == {"fcrra-spent-diagnostic"}
    assert all(
        set(row.frozen_v6_anchor_structure.split(";")).issubset(
            set(row.fcrra_final_structure.split(";"))
        )
        for row in rows
    )
    summary = summarize(rows, evaluate_signal=False)
    assert summary["status"] == "fcrra-engineering-smoke"
    assert summary["mechanism_signal"]["evaluated"] is False
    assert summary["mechanism_signal"]["passed"] is None
