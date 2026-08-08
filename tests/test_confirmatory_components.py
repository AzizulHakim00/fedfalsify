from __future__ import annotations

import numpy as np

from fedfalsify.basis import CandidateEquation
from fedfalsify.benchmarks import benchmark_catalog, generate_benchmark
from fedfalsify.client import FederatedFalsifierClient
from fedfalsify.expression_baselines import run_tree_search
from fedfalsify.expression_tree import expression_library, recognized_term
from fedfalsify.privacy import (
    NoisyCertificateClient,
    certificate_vector,
    leave_one_out_sensitivity,
)
from fedfalsify.statistics import (
    holm_adjust,
    mcnemar_exact,
    paired_bootstrap_difference,
)


def test_expression_library_contains_benchmark_structures() -> None:
    terms = {
        recognized_term(expression)
        for expression in expression_library(n_features=4, max_complexity=7)
    }
    assert {
        "x1",
        "x1^2",
        "x1^3",
        "sin(x2)",
        "x1*x2",
        "sin(x1+x1^2)",
        "sin(x1)*cos(x2)",
        "I(x3>1)*x3^2",
    }.issubset(terms)


def test_tree_search_outputs_finite_models() -> None:
    generated = generate_benchmark(
        "base",
        scenario="complementary",
        samples_per_client=60,
        noise_ratio=0.01,
        seed=4101,
    )
    for mode in ("centralized", "federated", "counterexample"):
        output = run_tree_search(
            generated.clients,
            mode=mode,
            seed=4101,
            population_size=12,
            generations=2,
            max_genes=3,
            max_complexity=7,
        )
        prediction = output.model.predict(generated.clients[0].x)
        assert np.all(np.isfinite(prediction))
        assert output.evaluations > 0
        assert output.runtime_seconds >= 0
        if mode == "federated":
            assert output.communication_bytes > 0


def test_paired_statistics_are_dependency_free_and_deterministic() -> None:
    result = mcnemar_exact([1, 1, 0, 0], [1, 0, 1, 0])
    assert result.discordant_pairs == 2
    assert result.exact_p_value == 1.0
    interval = paired_bootstrap_difference(
        [1.0, 2.0, 3.0],
        [0.5, 1.5, 2.5],
        resamples=500,
        seed=17,
    )
    assert interval.estimate == -0.5
    assert interval.lower <= interval.estimate <= interval.upper
    adjusted = holm_adjust({"a": 0.01, "b": 0.04, "c": 0.03})
    assert adjusted["a"] == 0.03
    assert adjusted["c"] == 0.06
    assert adjusted["b"] == 0.06


def test_certificate_noise_and_sensitivity_are_auditable() -> None:
    generated = generate_benchmark(
        "base",
        scenario="complementary",
        samples_per_client=60,
        noise_ratio=0.02,
        seed=4201,
    )
    catalog = benchmark_catalog(scenario="complementary")
    client = FederatedFalsifierClient(generated.clients[0], catalog)
    candidate = CandidateEquation(("1", "x1"), (0.0, 2.0), "privacy-test")
    original = client.falsify(candidate)
    noisy_a = NoisyCertificateClient(
        client, noise_multiplier=0.25, clip_value=10.0, seed=9
    ).falsify(candidate)
    noisy_b = NoisyCertificateClient(
        client, noise_multiplier=0.25, clip_value=10.0, seed=9
    ).falsify(candidate)
    assert np.allclose(certificate_vector(noisy_a), certificate_vector(noisy_b))
    assert not np.allclose(certificate_vector(original), certificate_vector(noisy_a))
    probe = leave_one_out_sensitivity(
        generated.clients[0],
        catalog,
        candidate,
        max_records=6,
        seed=3,
    )
    assert probe.sampled_records == 6
    assert probe.maximum_l2_change >= probe.median_l2_change >= 0
