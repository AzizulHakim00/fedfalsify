from __future__ import annotations

import math

import pytest

from fedfalsify.transactions_pysr_validation import (
    BUDGETS,
    PySRValidationRow,
    VALIDATION_SEEDS,
    summarize,
    validate_validation_seeds,
)


def _row(
    *,
    seed: int,
    regime: str,
    method: str,
    success: float,
    strong_nmse: float,
    runtime: float,
) -> PySRValidationRow:
    return PySRValidationRow(
        benchmark="base",
        scenario="complementary",
        noise_ratio=0.03,
        samples_per_client=300,
        num_clients=4,
        seed=seed,
        regime=regime,
        method=method,
        grammar_supported=True,
        completed=True,
        raw_data_pooled=method == "official-pysr",
        strict_exact_recovery=1.0 if method == "fedfalsify-v05" else float("nan"),
        semantic_all_1e4=success,
        semantic_all_1e3=success,
        semantic_all_1e2=success,
        interpolation_nmse=strong_nmse / 4,
        client_support_nmse=strong_nmse / 3,
        mild_extrapolation_nmse=strong_nmse / 2,
        strong_extrapolation_nmse=strong_nmse,
        expression_complexity=6 if method == "fedfalsify-v05" else 10,
        runtime_seconds=runtime,
        communication_bytes=1000 if method == "fedfalsify-v05" else 0,
        nominal_population_updates=0 if method == "fedfalsify-v05" else 100,
        expression="2*x1",
        note="test",
    )


def test_seed_policy_separates_frozen_development_validation_and_final() -> None:
    assert validate_validation_seeds(VALIDATION_SEEDS) == VALIDATION_SEEDS
    with pytest.raises(ValueError, match="frozen/development"):
        validate_validation_seeds((9001,))
    with pytest.raises(ValueError, match="frozen/development"):
        validate_validation_seeds((10012,))
    with pytest.raises(ValueError, match="final confirmation"):
        validate_validation_seeds((11001,))
    with pytest.raises(ValueError, match="permits only"):
        validate_validation_seeds((10999,))
    with pytest.raises(ValueError, match="unique"):
        validate_validation_seeds((10501, 10501))


def test_summary_requires_complete_matched_pairs() -> None:
    with pytest.raises(ValueError, match="exactly two methods"):
        summarize(
            [
                _row(
                    seed=10501,
                    regime="compact",
                    method="fedfalsify-v05",
                    success=1.0,
                    strong_nmse=0.001,
                    runtime=0.5,
                )
            ]
        )


def test_summary_preserves_regimes_and_paired_direction() -> None:
    rows: list[PySRValidationRow] = []
    for seed in (10501, 10502):
        for regime in BUDGETS:
            rows.extend(
                [
                    _row(
                        seed=seed,
                        regime=regime,
                        method="fedfalsify-v05",
                        success=1.0,
                        strong_nmse=0.001,
                        runtime=0.5,
                    ),
                    _row(
                        seed=seed,
                        regime=regime,
                        method="official-pysr",
                        success=0.0 if seed == 10501 else 1.0,
                        strong_nmse=0.01,
                        runtime=1.5,
                    ),
                ]
            )
    result = summarize(rows)
    assert result["rows"] == 8
    assert result["pairs"] == 4
    assert result["primary_endpoint"].startswith("quality-regime")
    assert result["methods"]["quality:fedfalsify-v05"]["semantic_all_1e3"] == 1.0
    assert result["methods"]["quality:official-pysr"]["semantic_all_1e3"] == 0.5
    for regime in BUDGETS:
        paired = result["paired"][regime]
        assert paired["pairs"] == 2
        assert paired["semantic_1e3_mcnemar"]["reference_only_success"] == 1
        assert paired["semantic_1e3_mcnemar"]["comparator_only_success"] == 0
        assert paired["runtime_pysr_minus_fedfalsify"]["estimate"] > 0
        assert paired["strong_extrapolation_pysr_minus_fedfalsify"]["estimate"] > 0
        assert 0 <= paired["semantic_1e3_holm_adjusted_p"] <= 1
    assert math.isnan(rows[1].strict_exact_recovery)
