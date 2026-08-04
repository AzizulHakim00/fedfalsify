from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from fedfalsify.benchmarks import benchmark_catalog, generate_benchmark
from fedfalsify.crossfit_redesign import (
    SplitFederatedFalsifierClient,
    _refit,
    _validation_term_support,
    crossfit_fedfalsify_method,
    partition_clients,
)


def _toy_clients() -> list[SimpleNamespace]:
    output = []
    for client_index in range(2):
        base = client_index * 1000
        row_id = np.arange(base, base + 60, dtype=float)
        x = np.column_stack([row_id, row_id + 1, row_id + 2, row_id + 3])
        y = 2.0 * row_id
        output.append(SimpleNamespace(client_id=f"client-{client_index}", x=x, y=y))
    return output


def test_partition_is_deterministic_disjoint_and_exhaustive() -> None:
    first = partition_clients(_toy_clients(), seed=13001)
    second = partition_clients(_toy_clients(), seed=13001)
    for left, right in zip(first, second):
        assert np.array_equal(left.fold_a.x, right.fold_a.x)
        assert np.array_equal(left.fold_b.x, right.fold_b.x)
        assert np.array_equal(left.validation.x, right.validation.x)

        a = set(left.fold_a.x[:, 0])
        b = set(left.fold_b.x[:, 0])
        validation = set(left.validation.x[:, 0])
        full = set(left.full.x[:, 0])
        assert not (a & b)
        assert not (a & validation)
        assert not (b & validation)
        assert a | b | validation == full
        assert len(a) == 24
        assert len(b) == 24
        assert len(validation) == 12


def test_split_client_fits_and_certifies_on_different_support() -> None:
    generated = generate_benchmark(
        "base",
        scenario="complementary",
        samples_per_client=120,
        noise_ratio=0.03,
        seed=13001,
    )
    catalog = benchmark_catalog(scenario="complementary")
    partition = partition_clients(generated.clients, seed=13001)[0]
    client = SplitFederatedFalsifierClient(
        partition.fold_a,
        partition.fold_b,
        catalog,
    )
    summary = client.fit_summary(("1", "x1"))
    candidate, _ = _refit(
        (partition,),
        catalog,
        ("1", "x1"),
        include_validation=False,
        candidate_id="test",
    )
    certificate = client.falsify(candidate)
    assert summary.support == len(partition.fold_a.y)
    assert certificate.support == len(partition.fold_b.y)


def test_validation_support_accepts_consistent_missing_term() -> None:
    generated = generate_benchmark(
        "base",
        scenario="complementary",
        samples_per_client=300,
        noise_ratio=0.03,
        seed=13002,
    )
    catalog = benchmark_catalog(scenario="complementary")
    partitions = partition_clients(generated.clients, seed=13002)
    primary, _ = _refit(
        partitions,
        catalog,
        ("1", "x1", "x3^2"),
        include_validation=False,
        candidate_id="missing-sine",
    )
    supported, _, diagnostics = _validation_term_support(
        primary,
        {"sin(x2)"},
        partitions,
        catalog,
    )
    assert supported
    assert diagnostics["sin(x2)"]["support_fraction"] >= 0.5


def test_validation_support_rejects_single_client_shortcut() -> None:
    generated = generate_benchmark(
        "base",
        scenario="spurious",
        samples_per_client=300,
        noise_ratio=0.03,
        seed=13003,
    )
    catalog = benchmark_catalog(scenario="spurious")
    partitions = partition_clients(generated.clients, seed=13003)
    primary, _ = _refit(
        partitions,
        catalog,
        ("1", "x1", "sin(x2)", "x3^2"),
        include_validation=False,
        candidate_id="true-core",
    )
    supported, _, diagnostics = _validation_term_support(
        primary,
        {"x4"},
        partitions,
        catalog,
    )
    assert not supported
    assert diagnostics["x4"]["support_fraction"] < 0.5


def test_crossfit_redesign_returns_finite_aggregate_only_candidate() -> None:
    generated = generate_benchmark(
        "interaction",
        scenario="complementary",
        samples_per_client=120,
        noise_ratio=0.10,
        seed=13004,
    )
    catalog = benchmark_catalog(scenario="complementary")
    output = crossfit_fedfalsify_method(
        generated.clients,
        catalog,
        seed=13004,
        target_mse=max(generated.noise_std**2 * 2.5, 1e-8),
        allow_fallback=True,
    )
    prediction = output.candidate.predict(generated.clients[0].x, catalog)
    assert output.method == "crossfit-governed"
    assert output.candidate.active_terms[0] == "1"
    assert np.all(np.isfinite(prediction))
    assert output.communication_bytes > 0
    assert output.validation_profiles
