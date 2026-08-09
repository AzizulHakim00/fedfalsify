from __future__ import annotations

import numpy as np
import pytest

from fedfalsify.benchmarks import benchmark_catalog
from fedfalsify.crossfit_redesign import partition_clients
from fedfalsify.crossfit_surrogate import split_selector_probe
from fedfalsify.rcsa_diagnostic import (
    _selector_exception_indices,
    rcsa_diagnostic_method,
)
from fedfalsify.rcsa_spent_study import (
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


def test_rcsa_seed_boundary_is_spent_or_engineering_only() -> None:
    assert SMOKE_SEED == 21001
    assert SPENT_DIAGNOSTIC_SEEDS == (20101, 20102, 20103, 20104, 20105)
    _validate_seeds((SMOKE_SEED,), smoke=True)
    _validate_seeds(SPENT_DIAGNOSTIC_SEEDS, smoke=False)
    with pytest.raises(ValueError):
        _validate_seeds((SMOKE_SEED,), smoke=False)
    with pytest.raises(ValueError):
        _validate_seeds((21101,), smoke=True)
    with pytest.raises(ValueError):
        _validate_seeds((21101,), smoke=False)


def test_selector_exception_eligibility_uses_selector_support_only() -> None:
    generated = _generated("exception")
    catalog = benchmark_catalog(scenario="exception")
    partitions = partition_clients(
        generated.clients, seed=SMOKE_SEED, validation_fraction=0.30
    )
    selectors, probes = split_selector_probe(partitions, seed=SMOKE_SEED)
    terms = ("1", EXCEPTION)
    _, selector_packets, probe_packets, _ = _build_packets(
        partitions, selectors, probes, catalog, terms
    )
    eligible = _selector_exception_indices(selector_packets, terms, EXCEPTION)
    assert eligible == (3,)
    assert selector_packets[eligible[0]].client_id == "client-4"
    # Probe support is intentionally not an input to the RCSA decision helper.
    assert probe_packets[eligible[0]].client_id == "client-4"


def test_rcsa_non_exception_is_exact_frozen_v6_identity() -> None:
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
    rcsa = rcsa_diagnostic_method(
        generated.clients,
        catalog,
        seed=SMOKE_SEED,
        max_terms=6,
        target_mse=_target_mse(generated),
        min_repair_score=0.05,
    )
    assert rcsa.exception_term is None
    assert rcsa.attempted is False
    assert rcsa.augmentation_accepted is False
    assert rcsa.anchor_structure == frozen.selector_structure
    assert rcsa.final_structure == frozen.selector_structure
    assert rcsa.candidate.active_terms == frozen.candidate.active_terms
    assert np.allclose(rcsa.candidate.coefficients, frozen.candidate.coefficients)


def test_rcsa_never_deletes_or_replaces_frozen_v6_terms() -> None:
    generated = _generated("exception", profile="imbalanced")
    catalog = benchmark_catalog(scenario="exception")
    output = rcsa_diagnostic_method(
        generated.clients,
        catalog,
        seed=SMOKE_SEED,
        max_terms=6,
        target_mse=_target_mse(generated),
        min_repair_score=0.05,
    )
    assert set(output.anchor_structure).issubset(set(output.final_structure))
    assert len(output.final_structure) <= 6
    if output.exception_in_anchor:
        assert output.attempted is False
        assert output.final_structure == output.anchor_structure
    if output.augmentation_accepted:
        assert output.exception_term == EXCEPTION
        assert set(output.final_structure) == set(output.anchor_structure) | {EXCEPTION}
        assert len(output.final_structure) == len(output.anchor_structure) + 1
        assert output.eligible_selector_clients
        assert output.anchor_role_information_score is not None
        assert output.augmented_role_information_score is not None
        assert (
            output.augmented_role_information_score
            < output.anchor_role_information_score
        )
        assert output.outside_selector_sse_anchor is not None
        assert output.outside_selector_sse_augmented is not None
        assert (
            output.outside_selector_sse_augmented
            <= output.outside_selector_sse_anchor + 1e-10
        )


def test_rcsa_smoke_is_engineering_only_and_signal_not_evaluated() -> None:
    rows = run_study(seeds=(SMOKE_SEED,), smoke=True)
    assert len(rows) == 3
    assert {row.seed for row in rows} == {SMOKE_SEED}
    assert {row.method for row in rows} == {"rcsa-spent-diagnostic"}
    assert all(
        set(row.frozen_v6_anchor_structure.split(";")).issubset(
            set(row.rcsa_final_structure.split(";"))
        )
        for row in rows
    )
    summary = summarize(rows, evaluate_signal=False)
    assert summary["status"] == "rcsa-engineering-smoke"
    assert summary["mechanism_signal"]["evaluated"] is False
    assert summary["mechanism_signal"]["passed"] is None
