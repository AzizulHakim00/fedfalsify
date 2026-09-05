import numpy as np

from fedfalsify.basis import CandidateEquation
from fedfalsify.benchmarks import BenchmarkClientDataset
from fedfalsify.scsv_diagnostic import _packet as predecessor_packet
from fedfalsify.scsv_diagnostic import _packet_sse as predecessor_packet_sse
from fedfalsify.scsv_v10_benchmarks import generate_v10_benchmark, v10_catalog
from fedfalsify.sufficient_stats import (
    aggregate_packets,
    packet_from_dataset,
    sse_from_packet,
)


def _fixture():
    generated = generate_v10_benchmark(
        "quadratic_role_v10",
        seed=29001,
        num_clients=4,
        balance_profile="balanced",
        role_profile="single",
        noise_ratio=0.10,
    )
    catalog = v10_catalog()
    terms = ("1", "x1", "x3^2", "I(x3<-0.90)*x3^2")
    return generated, catalog, terms


def test_shadow_packet_matches_predecessor_packet_numerically():
    generated, catalog, terms = _fixture()
    dataset = generated.clients[0]
    old = predecessor_packet(dataset, catalog, terms)
    new = packet_from_dataset(dataset, catalog, terms)
    assert new.client_id == old.client_id
    assert new.support == old.support
    assert new.terms == old.terms
    np.testing.assert_allclose(new.gram, old.gram, rtol=0.0, atol=1e-12)
    np.testing.assert_allclose(new.target, old.target, rtol=0.0, atol=1e-12)
    assert abs(new.target_energy - old.target_energy) <= 1e-12
    assert new.observed_support == old.observed_support


def test_shadow_sse_matches_predecessor_sse():
    generated, catalog, terms = _fixture()
    dataset = generated.clients[0]
    old = predecessor_packet(dataset, catalog, terms)
    new = packet_from_dataset(dataset, catalog, terms)
    coefficients = np.asarray([0.1, 0.5, 0.8, 0.2], dtype=float)
    candidate = CandidateEquation(terms, tuple(coefficients), "phase3a-parity")
    expected = predecessor_packet_sse(old, terms, candidate)
    observed = sse_from_packet(new, terms, coefficients)
    assert abs(observed - expected) <= 1e-10


def test_aggregate_packets_matches_explicit_row_concatenation():
    generated, catalog, terms = _fixture()
    packets = tuple(packet_from_dataset(client, catalog, terms) for client in generated.clients)
    aggregate = aggregate_packets(packets)

    concatenated = BenchmarkClientDataset(
        "pooled",
        np.concatenate([client.x for client in generated.clients], axis=0),
        np.concatenate([client.y for client in generated.clients], axis=0),
    )
    direct = packet_from_dataset(concatenated, catalog, terms)

    assert aggregate.support == direct.support
    assert aggregate.terms == direct.terms
    np.testing.assert_allclose(aggregate.gram, direct.gram, rtol=1e-12, atol=1e-10)
    np.testing.assert_allclose(aggregate.target, direct.target, rtol=1e-12, atol=1e-10)
    assert abs(aggregate.target_energy - direct.target_energy) <= 1e-10
    assert aggregate.observed_support == direct.observed_support
