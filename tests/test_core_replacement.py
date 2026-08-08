from __future__ import annotations

import csv

from fedfalsify.basis import CandidateEquation
from fedfalsify.benchmarks import benchmark_catalog, generate_benchmark
from fedfalsify.client import FederatedFalsifierClient
from fedfalsify.core_replacement_study import run_study, write_csv
from fedfalsify.replacement import FederatedCoreReplacement


def _clients(*, benchmark: str = "base", seed: int = 2030, samples: int = 240):
    generated = generate_benchmark(
        benchmark,
        scenario="exception",
        samples_per_client=samples,
        noise_ratio=0.03,
        seed=seed,
    )
    catalog = benchmark_catalog(scenario="exception")
    clients = [
        FederatedFalsifierClient(dataset, catalog) for dataset in generated.clients
    ]
    return generated, catalog, clients


def test_two_for_one_replacement_removes_correlated_base_surrogates() -> None:
    _, catalog, clients = _clients(samples=300)
    starting = CandidateEquation(
        (
            "1",
            "x1",
            "sin(x2)",
            "x3",
            "cos(x3)",
            "I(x3>1)*x3^2",
        ),
        (0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
        "surrogate-start",
    )
    result = FederatedCoreReplacement(
        clients,
        catalog,
        max_rounds=3,
        max_removed_terms=2,
    ).refine(starting)

    active = set(result.candidate.active_terms)
    assert "x3^2" in active
    assert "x3" not in active
    assert "cos(x3)" not in active
    assert result.replacements
    assert any(item.added_term == "x3^2" for item in result.replacements)


def test_exact_structure_is_not_replaced_without_evidence() -> None:
    _, catalog, clients = _clients(seed=3031, samples=300)
    starting = CandidateEquation(
        ("1", "x1", "sin(x2)", "x3^2", "I(x3>1)*x3^2"),
        (0.0, 0.0, 0.0, 0.0, 0.0),
        "exact-start",
    )
    result = FederatedCoreReplacement(clients, catalog).refine(starting)

    assert set(result.candidate.active_terms) == set(starting.active_terms)
    assert result.replacements == ()


def test_core_replacement_study_writes_replacement_ledger(tmp_path) -> None:
    rows = run_study(
        benchmarks=("base",),
        seeds=(2030,),
        sample_sizes=(120,),
        noise_ratio=0.03,
    )
    assert len(rows) == 2
    output = tmp_path / "v05.csv"
    write_csv(rows, output)
    with output.open(newline="", encoding="utf-8") as handle:
        records = list(csv.DictReader(handle))
    assert len(records) == 2
    assert {
        "samples_per_client",
        "replacement_count",
        "replacement_ledger",
    }.issubset(records[0])
