import numpy as np
import pytest

from fedfalsify.crossfit_redesign import partition_clients
from fedfalsify.crossfit_surrogate import split_selector_probe
from fedfalsify.phase3_cache import build_phase3_packet_cache
from fedfalsify.scsv_diagnostic import _build_packets as predecessor_build_packets
from fedfalsify.scsv_v10_benchmarks import generate_v10_benchmark, v10_catalog


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
    all_terms = ("1", "x1", "x3^2", "I(x3<-0.90)*x3^2")
    return generated, catalog, all_terms


def test_phase3_cache_is_deterministic_for_engineering_seed():
    generated, catalog, all_terms = _fixture()
    cache1 = build_phase3_packet_cache(generated.clients, catalog, all_terms, seed=29001)
    cache2 = build_phase3_packet_cache(generated.clients, catalog, all_terms, seed=29001)

    assert cache1.client_ids == cache2.client_ids
    assert cache1.all_terms == cache2.all_terms
    for group1, group2 in (
        (cache1.discovery, cache2.discovery),
        (cache1.selector, cache2.selector),
        (cache1.probe, cache2.probe),
    ):
        for a, b in zip(group1, group2):
            np.testing.assert_allclose(a.gram, b.gram, atol=0.0, rtol=0.0)
            np.testing.assert_allclose(a.target, b.target, atol=0.0, rtol=0.0)
            assert a.target_energy == b.target_energy
            assert a.observed_support == b.observed_support


def test_phase3_cache_matches_predecessor_packets_on_same_partitions():
    generated, catalog, all_terms = _fixture()
    partitions = partition_clients(generated.clients, seed=29001, validation_fraction=0.30)
    selectors, probes = split_selector_probe(partitions, seed=29001)
    old_discovery, old_selector, old_probe, _ = predecessor_build_packets(
        partitions, selectors, probes, catalog, all_terms
    )
    cache = build_phase3_packet_cache(generated.clients, catalog, all_terms, seed=29001)

    for old_group, new_group in (
        (old_discovery, cache.discovery),
        (old_selector, cache.selector),
        (old_probe, cache.probe),
    ):
        assert len(old_group) == len(new_group)
        for old, new in zip(old_group, new_group):
            assert old.client_id == new.client_id
            assert old.support == new.support
            assert old.terms == new.terms
            np.testing.assert_allclose(old.gram, new.gram, rtol=0.0, atol=1e-12)
            np.testing.assert_allclose(old.target, new.target, rtol=0.0, atol=1e-12)
            assert abs(old.target_energy - new.target_energy) <= 1e-12
            assert old.observed_support == new.observed_support


def test_phase3a_cache_rejects_non_engineering_seed():
    generated, catalog, all_terms = _fixture()
    with pytest.raises(ValueError, match="permits seed 29001"):
        build_phase3_packet_cache(generated.clients, catalog, all_terms, seed=29300)
