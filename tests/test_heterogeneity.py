from __future__ import annotations

from statistics import mean

from fedfalsify.benchmarks import benchmark_catalog, generate_benchmark
from fedfalsify.client import FederatedFalsifierClient
from fedfalsify.experiments import run_one
from fedfalsify.server import FedFalsifyDiscovery


def test_low_sample_exception_certificate_beats_ablation() -> None:
    new_rows = []
    old_rows = []
    for seed in (2026, 2027, 2028):
        new_rows.append(
            run_one(
                benchmark="base",
                scenario="exception",
                noise_ratio=0.03,
                seed=seed,
                method="fedfalsify",
                samples_per_client=120,
                max_terms=6,
            )
        )
        old_rows.append(
            run_one(
                benchmark="base",
                scenario="exception",
                noise_ratio=0.03,
                seed=seed,
                method="fedfalsify-no-heterogeneity",
                samples_per_client=120,
                max_terms=6,
            )
        )

    assert mean(row.exception_recovered for row in new_rows) == 1.0
    assert mean(row.exact_recovery for row in new_rows) >= 2 / 3
    assert mean(row.exception_recovered for row in new_rows) > mean(
        row.exception_recovered for row in old_rows
    )


def test_selected_exception_records_coefficient_contrast() -> None:
    generated = generate_benchmark(
        "base",
        scenario="exception",
        samples_per_client=120,
        noise_ratio=0.03,
        seed=2026,
    )
    catalog = benchmark_catalog(scenario="exception")
    clients = [
        FederatedFalsifierClient(dataset, catalog) for dataset in generated.clients
    ]
    result = FedFalsifyDiscovery(
        clients,
        catalog,
        max_rounds=8,
        max_terms=6,
        target_mse=max(generated.noise_std**2 * 2.5, 1e-8),
        min_repair_score=0.05,
        use_coefficient_heterogeneity=True,
    ).discover()
    exception_records = [
        record
        for record in result.history
        if record.selected_repair == "I(x3>1)*x3^2"
    ]
    assert exception_records
    record = exception_records[0]
    assert record.heterogeneity_score >= 0.20
    assert record.coefficient_contrast > 0.5
    assert record.heterogeneity_z > 3.0


def test_nonexception_catalog_cannot_produce_gated_term() -> None:
    row = run_one(
        benchmark="base",
        scenario="spurious",
        noise_ratio=0.03,
        seed=2026,
        method="fedfalsify",
        samples_per_client=120,
        max_terms=6,
    )
    assert "I(x3>1)*x3^2" not in row.discovered_terms
