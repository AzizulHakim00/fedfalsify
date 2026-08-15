from __future__ import annotations

from fedfalsify.transactions_ablation_v2 import (
    EXTENDED_VARIANTS,
    run_ablation_study,
)


def test_extended_suite_contains_pooled_equivalent_federated_baseline() -> None:
    assert "federated-information-catalog" in EXTENDED_VARIANTS


def test_federated_information_variant_runs_in_extended_matrix() -> None:
    rows = run_ablation_study(
        benchmarks=("base",),
        scenarios=("spurious",),
        noise_ratios=(0.03,),
        samples_per_client=(60,),
        client_counts=(4,),
        seeds=(10005,),
        variants=(
            "centralized-catalog",
            "federated-information-catalog",
            "fedfalsify-full",
        ),
        max_terms=6,
    )
    assert len(rows) == 3
    by_method = {row.method: row for row in rows}
    centralized = by_method["centralized-catalog"]
    federated = by_method["federated-information-catalog"]
    assert centralized.discovered_terms == federated.discovered_terms
    assert abs(centralized.test_nmse - federated.test_nmse) < 1e-10
    assert federated.communication_bytes > 0
