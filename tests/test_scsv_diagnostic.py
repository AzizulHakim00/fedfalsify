from __future__ import annotations

import numpy as np
import pytest

from fedfalsify.benchmarks import benchmark_catalog, generate_benchmark
from fedfalsify.crossfit_redesign import partition_clients
from fedfalsify.crossfit_surrogate import split_selector_probe
from fedfalsify.scsv_diagnostic import (
    _build_packets,
    _eligible_exception_indices,
    _fit_from_packets,
    _packet_sse,
    scsv_diagnostic_method,
)
from fedfalsify.scsv_diagnostic_study import (
    SMOKE_SEED,
    SPENT_DIAGNOSTIC_SEEDS,
    _validate_seeds,
)


def test_scsv_seed_boundary_is_spent_or_engineering_only() -> None:
    assert SMOKE_SEED == 18001
    assert SPENT_DIAGNOSTIC_SEEDS == tuple(range(17101, 17106))
    _validate_seeds(SPENT_DIAGNOSTIC_SEEDS, allow_engineering_smoke=False)
    _validate_seeds((SMOKE_SEED,), allow_engineering_smoke=True)
    with pytest.raises(ValueError):
        _validate_seeds((SMOKE_SEED,), allow_engineering_smoke=False)
    with pytest.raises(ValueError):
        _validate_seeds((18101,), allow_engineering_smoke=True)


def test_sufficient_packet_reconstructs_local_sse() -> None:
    generated = generate_benchmark(
        "base",
        scenario="complementary",
        samples_per_client=120,
        noise_ratio=0.20,
        seed=SMOKE_SEED,
    )
    catalog = benchmark_catalog(scenario="complementary")
    partitions = partition_clients(
        generated.clients, seed=SMOKE_SEED, validation_fraction=0.30
    )
    selectors, probes = split_selector_probe(partitions, seed=SMOKE_SEED)
    terms = ("1", "x1", "sin(x2)", "x3^2")
    fit_packets, _, _, communication = _build_packets(
        partitions, selectors, probes, catalog, terms
    )
    candidate = _fit_from_packets(
        fit_packets,
        terms,
        terms,
        candidate_id="packet-test",
    )
    packet = fit_packets[0]
    reconstructed = _packet_sse(packet, terms, candidate)
    direct_residual = (
        partitions[0].discovery.y
        - candidate.predict(partitions[0].discovery.x, catalog)
    )
    direct = float(direct_residual @ direct_residual)
    assert communication > 0
    assert np.isclose(reconstructed, direct, rtol=1e-9, atol=1e-8)


def test_exception_eligibility_uses_gated_selector_probe_support() -> None:
    generated = generate_benchmark(
        "interaction",
        scenario="exception",
        samples_per_client=120,
        noise_ratio=0.20,
        seed=SMOKE_SEED,
    )
    catalog = benchmark_catalog(scenario="exception")
    partitions = partition_clients(
        generated.clients, seed=SMOKE_SEED, validation_fraction=0.30
    )
    selectors, probes = split_selector_probe(partitions, seed=SMOKE_SEED)
    terms = ("1", "I(x3>1)*x3^2")
    _, selector_packets, probe_packets, _ = _build_packets(
        partitions, selectors, probes, catalog, terms
    )
    eligible = _eligible_exception_indices(
        selector_packets,
        probe_packets,
        terms,
        "I(x3>1)*x3^2",
    )
    assert eligible == (3,)
    assert selector_packets[eligible[0]].client_id == "client-4"
    assert probe_packets[eligible[0]].client_id == "client-4"


def test_scsv_smoke_is_bounded_and_forward_non_destructive() -> None:
    generated = generate_benchmark(
        "poly3",
        scenario="complementary",
        samples_per_client=120,
        noise_ratio=0.20,
        seed=SMOKE_SEED,
    )
    catalog = benchmark_catalog(scenario="complementary")
    output = scsv_diagnostic_method(
        generated.clients,
        catalog,
        seed=SMOKE_SEED,
        max_terms=6,
        target_mse=max(generated.noise_std**2 * 2.5, 1e-8),
        min_repair_score=0.05,
    )
    assert len(output.bank.candidate_terms) <= 10
    assert output.candidate_sets_evaluated <= 638
    assert output.selector_structure[0] == "1"
    assert output.validated_structure[0] == "1"
    assert len(output.selector_structure) <= 6
    assert len(output.validated_structure) <= 6
    assert np.isfinite(output.selector_profile.weighted_mse)
    assert output.communication_bytes > 0
    if output.probe_passed:
        assert output.validated_structure == output.selector_structure
        assert all(item.passed for item in output.term_diagnostics)
    else:
        assert output.validated_structure == output.anchor_structure
