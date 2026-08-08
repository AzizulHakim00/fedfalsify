from __future__ import annotations

import csv

from fedfalsify.baselines import (
    centralized_forward,
    fedfalsify_method,
    score_only_federated,
)
from fedfalsify.benchmarks import BENCHMARKS, benchmark_catalog, generate_benchmark
from fedfalsify.client import FederatedFalsifierClient
from fedfalsify.experiments import run_pilot, write_csv


def test_five_benchmarks_are_frozen() -> None:
    assert set(BENCHMARKS) == {
        "base",
        "poly3",
        "nested_sine",
        "trig_product",
        "interaction",
    }


def test_controlled_methods_recover_easy_base() -> None:
    generated = generate_benchmark(
        "base",
        scenario="complementary",
        samples_per_client=450,
        noise_ratio=0.01,
        seed=2026,
    )
    catalog = benchmark_catalog(scenario="complementary")
    clients = [
        FederatedFalsifierClient(dataset, catalog) for dataset in generated.clients
    ]
    centralized = centralized_forward(generated.clients, catalog, max_terms=6)
    score_only = score_only_federated(clients, catalog, max_terms=6)
    fed = fedfalsify_method(
        clients,
        catalog,
        max_terms=6,
        target_mse=max(generated.noise_std**2 * 2.5, 1e-8),
    )
    target = set(generated.target_terms)
    assert target.issubset(set(centralized.candidate.active_terms))
    assert target.issubset(set(score_only.candidate.active_terms))
    assert target.issubset(set(fed.candidate.active_terms))


def test_smoke_matrix_writes_auditable_csv(tmp_path) -> None:
    rows = run_pilot(
        benchmarks=("base",),
        scenarios=("complementary", "spurious", "exception"),
        noise_ratios=(0.03,),
        seeds=(2026,),
        methods=("centralized-forward", "score-only-federated", "fedfalsify"),
        samples_per_client=120,
        max_terms=6,
    )
    assert len(rows) == 9
    output = tmp_path / "smoke.csv"
    write_csv(rows, output)
    with output.open(newline="", encoding="utf-8") as handle:
        records = list(csv.DictReader(handle))
    assert len(records) == 9
    assert {
        "exact_recovery",
        "test_nmse",
        "communication_bytes",
        "discovered_terms",
    }.issubset(records[0])
