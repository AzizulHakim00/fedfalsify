from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from fedfalsify.basis import CandidateEquation
from fedfalsify.benchmarks import benchmark_catalog
from fedfalsify.crossfit_redesign import partition_clients
from fedfalsify.crossfit_surrogate import split_selector_probe
from fedfalsify.rccd_diagnostic import (
    _banked_exception,
    _conditional_test,
    _fit_from_packets,
    _role_indices,
    _zero_exception,
    rccd_diagnostic_method,
)
from fedfalsify.rccd_spent_study import (
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
SOURCE = "x3^2"


def _generated(scenario: str, *, profile: str = "balanced", clients: int = 4):
    return generate_independent_benchmark(
        "cubic_cross",
        scenario=scenario,
        nominal_samples_per_client=100,
        noise_ratio=0.20,
        seed=SMOKE_SEED,
        num_clients=clients,
        balance_profile=profile,
    )


def _target_mse(generated) -> float:
    return max(generated.noise_std**2 * 2.5, 1e-8)


def test_rccd_seed_boundary_is_spent_or_engineering_only() -> None:
    assert SMOKE_SEED == 23001
    assert SPENT_DIAGNOSTIC_SEEDS == (20101, 20102, 20103, 20104, 20105)
    _validate_seeds((SMOKE_SEED,), smoke=True)
    _validate_seeds(SPENT_DIAGNOSTIC_SEEDS, smoke=False)
    with pytest.raises(ValueError):
        _validate_seeds((SMOKE_SEED,), smoke=False)
    with pytest.raises(ValueError):
        _validate_seeds((22001,), smoke=True)
    with pytest.raises(ValueError):
        _validate_seeds((23101,), smoke=True)
    with pytest.raises(ValueError):
        _validate_seeds((23101,), smoke=False)


def test_fixed_reduced_comparator_changes_only_exception_coefficient() -> None:
    full = CandidateEquation(
        ("1", SOURCE, EXCEPTION),
        (0.2, 0.55, 0.71),
        "rccd-test-full",
    )
    zero = _zero_exception(full, EXCEPTION)
    assert zero.active_terms == full.active_terms
    full_map = dict(zip(full.active_terms, full.coefficients))
    zero_map = dict(zip(zero.active_terms, zero.coefficients))
    assert zero_map[EXCEPTION] == 0.0
    for term in ("1", SOURCE):
        assert zero_map[term] == full_map[term]


def test_source_link_metadata_blocks_orphan_deviation() -> None:
    catalog = benchmark_catalog(scenario="exception")
    fake = SimpleNamespace(
        bank=SimpleNamespace(candidate_terms=(EXCEPTION,)),
        selector_structure=("1", "x1", "x1*x2"),
    )
    exception, source, in_bank, in_anchor, source_in_anchor = _banked_exception(
        fake, catalog
    )
    assert exception == EXCEPTION
    assert source == SOURCE
    assert in_bank is True
    assert in_anchor is False
    assert source_in_anchor is False


def test_one_parameter_conditional_delta_matches_direct_formula() -> None:
    generated = _generated("exception", profile="imbalanced")
    catalog = benchmark_catalog(scenario="exception")
    partitions = partition_clients(
        generated.clients, seed=SMOKE_SEED, validation_fraction=0.30
    )
    selectors, probes = split_selector_probe(partitions, seed=SMOKE_SEED)
    all_terms = ("1", SOURCE, EXCEPTION)
    fit_packets, selector_packets, probe_packets, _ = _build_packets(
        partitions, selectors, probes, catalog, all_terms
    )
    full = _fit_from_packets(
        fit_packets,
        all_terms,
        all_terms,
        candidate_id="rccd-test-discovery-full",
    )
    zero = _zero_exception(full, EXCEPTION)
    selector_eligible = _role_indices(selector_packets, all_terms, EXCEPTION)
    probe_eligible = _role_indices(probe_packets, all_terms, EXCEPTION)
    assert selector_eligible == (3,)
    assert probe_eligible == (3,)

    support, full_sse, zero_sse, delta, passed = _conditional_test(
        full, zero, selector_packets, all_terms, selector_eligible
    )
    expected = np.log(max(full_sse, 1e-15) / max(zero_sse, 1e-15)) + np.log(
        max(support, 2)
    ) / max(support, 1)
    assert np.isclose(delta, expected, rtol=1e-12, atol=1e-12)
    assert passed == bool(expected < 0.0)


def test_rccd_non_exception_is_exact_frozen_v6_identity() -> None:
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
    output = rccd_diagnostic_method(
        generated.clients,
        catalog,
        seed=SMOKE_SEED,
        max_terms=6,
        target_mse=_target_mse(generated),
        min_repair_score=0.05,
    )
    assert output.exception_term is None
    assert output.attempted is False
    assert output.accepted is False
    assert output.final_structure == frozen.selector_structure
    assert output.candidate.active_terms == frozen.candidate.active_terms
    assert np.allclose(output.candidate.coefficients, frozen.candidate.coefficients)


def test_rccd_never_deletes_anchor_and_attempts_are_source_linked() -> None:
    for profile in ("balanced", "imbalanced"):
        generated = _generated("exception", profile=profile)
        catalog = benchmark_catalog(scenario="exception")
        output = rccd_diagnostic_method(
            generated.clients,
            catalog,
            seed=SMOKE_SEED,
            max_terms=6,
            target_mse=_target_mse(generated),
            min_repair_score=0.05,
        )
        assert set(output.anchor_structure).issubset(set(output.final_structure))
        assert len(output.final_structure) <= 6
        if output.attempted:
            assert output.exception_in_bank is True
            assert output.exception_in_anchor is False
            assert output.source_term == SOURCE
            assert output.source_in_anchor is True
            assert output.discovery_full_structure
            full_map = dict(
                zip(output.discovery_full_structure, output.discovery_full_coefficients)
            )
            assert EXCEPTION in full_map
            assert output.selector_eligible_clients
            assert output.probe_eligible_clients
            if output.accepted:
                assert output.selector_passed is True
                assert output.probe_passed is True
                assert output.selector_delta < 0.0
                assert output.probe_delta < 0.0
                assert output.selector_outside_safe is True
                assert output.probe_outside_safe is True
                assert EXCEPTION in output.final_structure


def test_rccd_smoke_is_engineering_only_and_signal_not_evaluated() -> None:
    rows = run_study(seeds=(SMOKE_SEED,), smoke=True)
    assert len(rows) == 5
    assert {row.seed for row in rows} == {SMOKE_SEED}
    assert {row.method for row in rows} == {"rccd-spent-diagnostic"}
    assert all(
        set(row.frozen_v6_anchor_structure.split(";")).issubset(
            set(row.rccd_final_structure.split(";"))
        )
        for row in rows
    )
    assert all(
        (not bool(row.rccd_attempted)) or bool(row.source_in_anchor)
        for row in rows
    )
    summary = summarize(rows, evaluate_signal=False)
    assert summary["status"] == "rccd-engineering-smoke"
    assert summary["mechanism_signal"]["evaluated"] is False
    assert summary["mechanism_signal"]["passed"] is None
