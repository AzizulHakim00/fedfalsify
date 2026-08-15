from __future__ import annotations

import pytest

from fedfalsify.transactions_ablation import (
    _parse_ints,
    run_ablation_study,
    validate_development_seeds,
)


def test_frozen_confirmatory_seeds_are_rejected() -> None:
    with pytest.raises(ValueError, match="frozen confirmatory seeds"):
        validate_development_seeds((9001, 10001))


def test_duplicate_development_seeds_are_rejected() -> None:
    with pytest.raises(ValueError, match="unique"):
        validate_development_seeds((10001, 10001))


def test_integer_range_parser() -> None:
    assert _parse_ints("10001-10003,10005") == (
        10001,
        10002,
        10003,
        10005,
    )


def test_small_ablation_matrix_runs_on_fresh_seed() -> None:
    variants = (
        "fedfalsify-full",
        "fedfalsify-no-replacement",
        "score-only-federated",
        "centralized-catalog",
        "local-consensus",
    )
    rows = run_ablation_study(
        benchmarks=("base",),
        scenarios=("complementary",),
        noise_ratios=(0.03,),
        samples_per_client=(60,),
        client_counts=(4,),
        seeds=(10001,),
        variants=variants,
        max_terms=6,
    )
    assert len(rows) == len(variants)
    assert {row.method for row in rows} == set(variants)
    assert all(row.seed == 10001 for row in rows)
    assert all(row.benchmark == "base" for row in rows)


def test_no_exception_module_is_explicit_ablation() -> None:
    rows = run_ablation_study(
        benchmarks=("base",),
        scenarios=("exception",),
        noise_ratios=(0.03,),
        samples_per_client=(60,),
        client_counts=(4,),
        seeds=(10002,),
        variants=("fedfalsify-no-exception-module",),
        max_terms=6,
    )
    assert len(rows) == 1
    row = rows[0]
    assert row.method == "fedfalsify-no-exception-module"
    assert row.exception_recovered == 0.0
    assert row.exact_recovery == 0.0
