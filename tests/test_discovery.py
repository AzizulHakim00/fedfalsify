from __future__ import annotations

import json

import numpy as np

from fedfalsify import (
    FedFalsifyDiscovery,
    FederatedFalsifierClient,
    TermCatalog,
    generate_heterogeneous_clients,
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


def test_each_round_adds_at_most_one_counterexample_supported_term() -> None:
    catalog, clients = _build(seed=123)
    result = FedFalsifyDiscovery(clients, catalog, max_rounds=6).discover()

    sizes = [len(record.candidate.active_terms) for record in result.history]
    assert sizes == sorted(sizes)
    assert all((right - left) in {0, 1} for left, right in zip(sizes, sizes[1:]))
