from __future__ import annotations

import json

import numpy as np

from fedfalsify import (
    FedFalsifyDiscovery,
    FederatedFalsifierClient,
    TermCatalog,
    generate_exception_clients,
    generate_heterogeneous_clients,
    generate_spurious_correlation_clients,
)


def _build(seed: int = 2026):
    catalog = TermCatalog()
    datasets = generate_heterogeneous_clients(
        samples_per_client=700,
        noise_std=0.02,
        seed=seed,
    )
    clients = [FederatedFalsifierClient(dataset, catalog) for dataset in datasets]
    return catalog, clients


def test_recovers_known_mechanism_terms_and_coefficients() -> None:
    catalog, clients = _build()
    result = FedFalsifyDiscovery(
        clients,
        catalog,
        max_rounds=7,
        max_terms=5,
        target_mse=0.0015,
        min_repair_score=0.05,
    ).discover()

    terms = set(result.candidate.active_terms)
    assert {"1", "x1", "sin(x2)", "x3^2"}.issubset(terms)

    coefficients = dict(
        zip(result.candidate.active_terms, result.candidate.coefficients)
    )
    assert np.isclose(coefficients["x1"], 2.0, atol=0.03)
    assert np.isclose(coefficients["sin(x2)"], 1.0, atol=0.04)
    assert np.isclose(coefficients["x3^2"], 0.5, atol=0.03)
    assert result.converged


def test_certificate_is_json_serializable_and_contains_no_raw_rows() -> None:
    catalog, clients = _build(seed=77)
    result = FedFalsifyDiscovery(clients, catalog, max_rounds=1).discover()
    payload = result.certificates[0].to_dict()
    encoded = json.dumps(payload)

    assert "term_evidence" in payload
    assert "worst_region" in payload
    assert '"x"' not in encoded
    assert '"y"' not in encoded
    assert payload["support"] == 700
    assert "observed_support" in payload["term_evidence"][0]


def test_each_round_adds_at_most_one_counterexample_supported_term() -> None:
    catalog, clients = _build(seed=123)
    result = FedFalsifyDiscovery(clients, catalog, max_rounds=6).discover()

    sizes = [len(record.candidate.active_terms) for record in result.history]
    assert sizes == sorted(sizes)
    assert all((right - left) in {0, 1} for left, right in zip(sizes, sizes[1:]))


def test_rejects_a_single_client_spurious_shortcut() -> None:
    catalog = TermCatalog()
    datasets = generate_spurious_correlation_clients(
        samples_per_client=800,
        noise_std=0.02,
        seed=191,
    )
    clients = [FederatedFalsifierClient(dataset, catalog) for dataset in datasets]
    result = FedFalsifyDiscovery(
        clients,
        catalog,
        max_rounds=7,
        max_terms=5,
        target_mse=0.0015,
        min_repair_score=0.05,
        min_core_support_fraction=0.6,
    ).discover()

    active = set(result.candidate.active_terms)
    assert {"1", "x1", "x2^2"}.issubset(active)
    assert "x3" not in active
    coefficients = dict(
        zip(result.candidate.active_terms, result.candidate.coefficients)
    )
    assert np.isclose(coefficients["x1"], 3.0, atol=0.04)
    assert np.isclose(coefficients["x2^2"], 0.8, atol=0.04)
    assert result.converged


def test_discovers_invariant_core_and_domain_restricted_exception() -> None:
    catalog = TermCatalog(include_exception_terms=True)
    datasets = generate_exception_clients(
        samples_per_client=900,
        noise_std=0.015,
        seed=229,
    )
    clients = [FederatedFalsifierClient(dataset, catalog) for dataset in datasets]
    result = FedFalsifyDiscovery(
        clients,
        catalog,
        max_rounds=8,
        max_terms=6,
        target_mse=0.001,
        min_repair_score=0.04,
        min_core_support_fraction=0.6,
        min_exception_support_fraction=0.8,
    ).discover()

    active = set(result.candidate.active_terms)
    assert {"1", "x1", "sin(x2)", "I(x3>1)*x3^2"}.issubset(active)
    assert set(result.candidate.core_terms(catalog)) >= {"1", "x1", "sin(x2)"}
    assert result.candidate.exception_terms(catalog) == ("I(x3>1)*x3^2",)

    coefficients = dict(
        zip(result.candidate.active_terms, result.candidate.coefficients)
    )
    assert np.isclose(coefficients["x1"], 2.0, atol=0.04)
    assert np.isclose(coefficients["sin(x2)"], 1.0, atol=0.04)
    assert np.isclose(coefficients["I(x3>1)*x3^2"], 0.75, atol=0.04)
    assert result.converged
