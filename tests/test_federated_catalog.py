from __future__ import annotations

import numpy as np

from fedfalsify.baselines import centralized_forward
from fedfalsify.benchmarks import benchmark_catalog, generate_benchmark
from fedfalsify.client import FederatedFalsifierClient
from fedfalsify.federated_catalog import (
    candidates_numerically_equivalent,
    federated_information_forward,
)


def _compare(
    benchmark: str,
    scenario: str,
    noise_ratio: float,
    seed: int,
) -> None:
    generated = generate_benchmark(
        benchmark,
        scenario=scenario,
        samples_per_client=120,
        noise_ratio=noise_ratio,
        seed=seed,
        num_clients=4,
    )
    catalog = benchmark_catalog(scenario=scenario)
    clients = [
        FederatedFalsifierClient(dataset, catalog)
        for dataset in generated.clients
    ]
    centralized = centralized_forward(
        generated.clients,
        catalog,
        max_terms=6,
    )
    federated = federated_information_forward(
        clients,
        catalog,
        max_terms=6,
    )
    assert federated.method == "federated-information-catalog"
    assert federated.communication_bytes > 0
    assert candidates_numerically_equivalent(
        centralized.candidate,
        federated.candidate,
        coefficient_tolerance=1e-7,
    )

    pooled_x = np.concatenate([dataset.x for dataset in generated.clients], axis=0)
    np.testing.assert_allclose(
        centralized.candidate.predict(pooled_x, catalog),
        federated.candidate.predict(pooled_x, catalog),
        atol=1e-7,
        rtol=1e-7,
    )


def test_federated_information_matches_pooled_base() -> None:
    _compare("base", "complementary", 0.03, 10001)


def test_federated_information_matches_pooled_high_noise_poly3() -> None:
    _compare("poly3", "spurious", 0.10, 10002)


def test_federated_information_matches_pooled_exception_catalog() -> None:
    _compare("interaction", "exception", 0.03, 10003)


def test_client_sample_count_is_protocol_support_metadata() -> None:
    generated = generate_benchmark(
        "base",
        scenario="complementary",
        samples_per_client=60,
        noise_ratio=0.03,
        seed=10004,
        num_clients=4,
    )
    catalog = benchmark_catalog(scenario="complementary")
    clients = [
        FederatedFalsifierClient(dataset, catalog)
        for dataset in generated.clients
    ]
    assert [client.sample_count for client in clients] == [60, 60, 60, 60]
