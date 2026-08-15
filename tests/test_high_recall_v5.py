from __future__ import annotations

import numpy as np
import pytest

from fedfalsify.benchmarks import benchmark_catalog, generate_benchmark
from fedfalsify.crossfit_redesign import partition_clients
from fedfalsify.high_recall_v5 import (
    _aggregate_column_correlations,
    high_recall_verified_forward_method,
)
from fedfalsify.high_recall_v5_study import (
    DEVELOPMENT_SEEDS,
    SMOKE_SEED,
    _validate_seeds,
)


def test_v5_seed_governance_separates_smoke_and_evidence() -> None:
    assert SMOKE_SEED == 17001
    assert DEVELOPMENT_SEEDS == tuple(range(17101, 17106))
    assert SMOKE_SEED not in set(DEVELOPMENT_SEEDS)
    _validate_seeds(DEVELOPMENT_SEEDS, allow_engineering_smoke=False)
    _validate_seeds((SMOKE_SEED,), allow_engineering_smoke=True)
    with pytest.raises(ValueError):
        _validate_seeds((SMOKE_SEED,), allow_engineering_smoke=False)
    with pytest.raises(ValueError):
        _validate_seeds((16101,), allow_engineering_smoke=True)


def test_discovery_correlation_is_aggregate_and_finite() -> None:
    generated = generate_benchmark(
        "poly3",
        scenario="complementary",
        samples_per_client=120,
        noise_ratio=0.20,
        seed=SMOKE_SEED,
        num_clients=4,
    )
    catalog = benchmark_catalog(scenario="complementary")
    partitions = partition_clients(
        generated.clients, seed=SMOKE_SEED, validation_fraction=0.30
    )
    correlations, communication = _aggregate_column_correlations(partitions, catalog)
    assert communication > 0
    assert ("x1", "x1^3") in correlations
    assert all(
        np.isfinite(value) and 0.0 <= value <= 1.0 + 1e-12
        for value in correlations.values()
    )


def test_v5_forward_only_smoke_invariants() -> None:
    generated = generate_benchmark(
        "poly3",
        scenario="exception",
        samples_per_client=120,
        noise_ratio=0.20,
        seed=SMOKE_SEED,
        num_clients=4,
    )
    catalog = benchmark_catalog(scenario="exception")
    output = high_recall_verified_forward_method(
        generated.clients,
        catalog,
        seed=SMOKE_SEED,
        max_terms=6,
        target_mse=max(generated.noise_std**2 * 2.5, 1e-8),
        min_repair_score=0.05,
    )

    assert len(output.candidate_profile.candidate_terms) <= 10
    assert "I(x3>1)*x3^2" not in {
        term
        for pair in output.candidate_profile.correlated_pairs
        for term in pair.terms
    }
    assert all(item.stage == "v5-forward-single" for item in output.forward_decisions)
    assert all(item.stage == "v5-pair-rescue" for item in output.pair_decisions)
    for item in output.pair_decisions:
        if item.accepted:
            assert item.selector_passed
            assert item.joint_probe_passed
            assert item.first_necessary
            assert item.second_necessary
    assert output.candidate.active_terms[0] == "1"
    assert output.communication_bytes > 0
