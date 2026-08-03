from __future__ import annotations

from fedfalsify.transactions_ablation_fixed import (
    coefficient_certificate_settings,
    run_ablation_study,
)


def test_no_heterogeneity_removes_discovery_and_replacement_evidence() -> None:
    use_heterogeneity, replacement = coefficient_certificate_settings(
        "fedfalsify-no-heterogeneity"
    )
    assert use_heterogeneity is False
    assert replacement == {
        "min_incoming_support_fraction": 0.0,
        "min_incoming_sign_agreement": 0.0,
        "min_incoming_local_z": 0.0,
        "min_incoming_global_z": 0.0,
        "coefficient_prune_z": 0.0,
    }


def test_full_method_retains_default_coefficient_evidence() -> None:
    use_heterogeneity, replacement = coefficient_certificate_settings(
        "fedfalsify-full"
    )
    assert use_heterogeneity is True
    assert replacement == {}


def test_corrected_variant_runs() -> None:
    rows = run_ablation_study(
        benchmarks=("base",),
        scenarios=("complementary",),
        noise_ratios=(0.03,),
        samples_per_client=(60,),
        client_counts=(4,),
        seeds=(10003,),
        variants=(
            "fedfalsify-full",
            "fedfalsify-no-heterogeneity",
        ),
        max_terms=6,
    )
    assert len(rows) == 2
    assert {row.method for row in rows} == {
        "fedfalsify-full",
        "fedfalsify-no-heterogeneity",
    }
