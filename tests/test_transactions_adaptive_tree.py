from __future__ import annotations

import json

import pytest

from fedfalsify.transactions_adaptive_tree_fixed import (
    METHODS,
    run_study,
    summarize,
    validate_fresh_seeds,
)


def test_frozen_adaptive_seeds_are_rejected() -> None:
    with pytest.raises(ValueError, match="frozen seeds"):
        validate_fresh_seeds((9001, 10011))


def test_duplicate_adaptive_seeds_are_rejected() -> None:
    with pytest.raises(ValueError, match="unique"):
        validate_fresh_seeds((10011, 10011))


def test_matched_adaptive_smoke_matrix_runs() -> None:
    rows = run_study(
        benchmarks=("base",),
        scenarios=("spurious",),
        noise_ratios=(0.03,),
        samples_per_client=(60,),
        client_counts=(4,),
        seeds=(10011,),
        methods=METHODS,
        population_size=8,
        generations=1,
        max_genes=2,
        max_complexity=5,
    )
    assert len(rows) == 4
    assert {row.method for row in rows} == set(METHODS)
    assert {row.seed for row in rows} == {10011}
    certificate = next(
        row for row in rows
        if row.method == "certificate-guided-federated-tree"
    )
    assert certificate.violating_certificates >= 0
    assert certificate.certificate_penalty >= 0.0
    assert certificate.communication_bytes > 0
    assert 0.0 <= certificate.mean_certificate_support <= 1.0
    assert 0.0 <= certificate.mean_certificate_sign_agreement <= 1.0


def test_adaptive_summary_is_json_serializable() -> None:
    rows = run_study(
        benchmarks=("base",),
        scenarios=("complementary",),
        noise_ratios=(0.03,),
        samples_per_client=(50,),
        client_counts=(4,),
        seeds=(10012,),
        methods=METHODS,
        population_size=8,
        generations=1,
        max_genes=2,
        max_complexity=3,
    )
    summary = summarize(rows, bootstrap_resamples=200)
    encoded = json.dumps(summary)
    assert "certificate-guided-federated-tree" in encoded
    assert summary["status"] == "development"
    assert len(summary["methods"]) == 4
    assert all(item["pairs"] == 1 for item in summary["paired"].values())
