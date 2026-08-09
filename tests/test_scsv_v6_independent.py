from __future__ import annotations

import numpy as np
import pytest

from fedfalsify import scsv_v6
from fedfalsify.benchmarks import BENCHMARKS, benchmark_catalog
from fedfalsify.scsv_v6_independent import (
    INDEPENDENT_BENCHMARKS,
    generate_independent_benchmark,
    independent_client_sizes,
)
from fedfalsify import scsv_v6_independent_study as study


def test_independent_truth_families_use_frozen_catalog_and_reserve_x4() -> None:
    catalog = benchmark_catalog(scenario="exception")
    names = set(catalog.names())
    development_truths = {frozenset(spec.target_terms) for spec in BENCHMARKS.values()}
    independent_truths = []
    for spec in INDEPENDENT_BENCHMARKS.values():
        truth = frozenset(spec.target_terms)
        independent_truths.append(truth)
        assert truth <= names
        assert "x4" not in truth
        assert "x4^2" not in truth
        assert truth not in development_truths
    assert len(set(independent_truths)) == len(INDEPENDENT_BENCHMARKS)


def test_client_size_profiles_are_deterministic_and_v6_feasible() -> None:
    balanced = independent_client_sizes(100, 16, profile="balanced", seed=20001)
    first = independent_client_sizes(100, 16, profile="imbalanced", seed=20001)
    second = independent_client_sizes(100, 16, profile="imbalanced", seed=20001)
    assert balanced == (100,) * 16
    assert first == second
    assert min(first) >= 70
    assert len(set(first)) > 1


def test_generator_is_deterministic_and_supports_scaling_counts() -> None:
    for clients in (4, 8, 16, 32):
        first = generate_independent_benchmark(
            "multi_quadratic",
            scenario="exception",
            nominal_samples_per_client=100,
            noise_ratio=0.20,
            seed=20001,
            num_clients=clients,
            balance_profile="imbalanced",
        )
        second = generate_independent_benchmark(
            "multi_quadratic",
            scenario="exception",
            nominal_samples_per_client=100,
            noise_ratio=0.20,
            seed=20001,
            num_clients=clients,
            balance_profile="imbalanced",
        )
        assert len(first.clients) == clients
        assert min(len(item.y) for item in first.clients) >= 70
        for a, b in zip(first.clients, second.clients):
            assert np.array_equal(a.x, b.x)
            assert np.array_equal(a.y, b.y)


def test_spurious_shortcut_does_not_change_truth_definition() -> None:
    generated = generate_independent_benchmark(
        "fourier_quadratic",
        scenario="spurious",
        nominal_samples_per_client=100,
        noise_ratio=0.10,
        seed=20001,
        num_clients=4,
    )
    assert "x4" not in generated.target_terms
    assert "x4^2" not in generated.target_terms


def test_independent_study_imports_exact_frozen_v6_function() -> None:
    assert study.scsv_cert_method is scsv_v6.scsv_cert_method


def test_seed_firewall() -> None:
    study._validate_seeds((20001,), smoke=True)
    study._validate_seeds((20101, 20102, 20103, 20104, 20105), smoke=False)
    with pytest.raises(ValueError):
        study._validate_seeds((20101,), smoke=True)
    with pytest.raises(ValueError):
        study._validate_seeds((19101,), smoke=False)


def test_independent_smoke_does_not_evaluate_gate() -> None:
    rows = study.run_smoke()
    assert len(rows) == 1
    assert {row.seed for row in rows} == {20001}
    assert {row.method for row in rows} == {"scsv-v6-full"}
    summary = study.summarize(rows, evaluate_gate=False)
    assert summary["independent_gate"]["evaluated"] is False
    assert summary["independent_gate"]["passed"] is None
