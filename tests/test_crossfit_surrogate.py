from __future__ import annotations

import numpy as np

from fedfalsify.basis import CandidateEquation
from fedfalsify.benchmarks import benchmark_catalog, generate_benchmark
from fedfalsify.crossfit_redesign import PartitionedClient, partition_clients
from fedfalsify.crossfit_surrogate import (
    _term_probe_diagnostic,
    split_selector_probe,
    structural_crossfit_method,
)
from fedfalsify.external_common import ExternalClientData


def _partition(client_id: str, selector_x1: np.ndarray, probe_x1: np.ndarray) -> tuple[PartitionedClient, PartitionedClient]:
    def matrix(x1: np.ndarray) -> np.ndarray:
        return np.column_stack(
            [x1, np.zeros(len(x1)), np.zeros(len(x1)), np.zeros(len(x1))]
        )

    selector = ExternalClientData(client_id, matrix(selector_x1), selector_x1**3)
    probe = ExternalClientData(client_id, matrix(probe_x1), probe_x1**3)
    filler_x = matrix(np.linspace(-1.0, 1.0, 20))
    filler = ExternalClientData(client_id, filler_x, filler_x[:, 0] ** 3)
    full = ExternalClientData(
        client_id,
        np.concatenate([selector.x, probe.x, filler.x], axis=0),
        np.concatenate([selector.y, probe.y, filler.y], axis=0),
    )
    selector_partition = PartitionedClient(client_id, filler, filler, selector, full)
    probe_partition = PartitionedClient(client_id, filler, filler, probe, full)
    return selector_partition, probe_partition


def test_true_cubic_beats_correlated_surrogates_on_independent_probe() -> None:
    catalog = benchmark_catalog(scenario="complementary")
    selectors = []
    probes = []
    for index, shift in enumerate((-0.15, -0.05, 0.05, 0.15), start=1):
        selector, probe = _partition(
            f"client-{index}",
            np.linspace(-1.4 + shift, 1.4 + shift, 80),
            np.concatenate(
                [np.linspace(-3.0 + shift, -2.0 + shift, 40), np.linspace(2.0 + shift, 3.0 + shift, 40)]
            ),
        )
        selectors.append(selector)
        probes.append(probe)

    primary = CandidateEquation(("1",), (0.0,), "primary")
    cubic = CandidateEquation(("1", "x1^3"), (0.0, 1.0), "cubic")
    sine = CandidateEquation(("1", "sin(x1)"), (0.0, 1.0), "sine")

    cubic_result = _term_probe_diagnostic(
        "x1^3", primary, cubic, selectors, probes, catalog
    )
    sine_result = _term_probe_diagnostic(
        "sin(x1)", primary, sine, selectors, probes, catalog
    )
    assert cubic_result.passed
    assert cubic_result.best_rival in {"x1", "sin(x1)"}
    assert cubic_result.relative_advantage > 0.01
    assert not sine_result.passed
    assert sine_result.best_rival in {"x1", "x1^3"}


def test_selector_probe_split_is_disjoint_and_exhaustive() -> None:
    generated = generate_benchmark(
        "base", scenario="complementary", samples_per_client=120, seed=14001
    )
    partitions = partition_clients(
        generated.clients, seed=14001, validation_fraction=0.30
    )
    selectors, probes = split_selector_probe(partitions, seed=14001)
    for original, selector, probe in zip(partitions, selectors, probes):
        original_rows = {tuple(row) for row in original.validation.x}
        selector_rows = {tuple(row) for row in selector.validation.x}
        probe_rows = {tuple(row) for row in probe.validation.x}
        assert selector_rows.isdisjoint(probe_rows)
        assert selector_rows | probe_rows == original_rows


def test_structural_method_never_selects_score_only_source() -> None:
    generated = generate_benchmark(
        "poly3",
        scenario="complementary",
        samples_per_client=120,
        noise_ratio=0.10,
        seed=14001,
    )
    catalog = benchmark_catalog(scenario="complementary")
    result = structural_crossfit_method(
        generated.clients,
        catalog,
        seed=14001,
        max_terms=6,
        target_mse=max(generated.noise_std**2 * 3.0, 1e-5),
    )
    assert result.selected_source in {
        "crossfit-intersection",
        "direction-a",
        "direction-b",
        "crossfit-union",
    }
    assert result.selected_source != "score-only"
