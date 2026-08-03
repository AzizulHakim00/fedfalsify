from __future__ import annotations

import json
import math

from fedfalsify.transactions_pysr_validation_fixed import (
    BUDGETS,
    PySRValidationRow,
    summarize,
)


def _row(
    *,
    seed: int,
    regime: str,
    method: str,
    completed: bool,
    semantic: float,
    nmse: float,
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
        completed=completed,
        raw_data_pooled=method == "official-pysr",
        strict_exact_recovery=1.0 if method == "fedfalsify-v05" else float("nan"),
        semantic_all_1e4=semantic,
        semantic_all_1e3=semantic,
        semantic_all_1e2=semantic,
        interpolation_nmse=nmse,
        client_support_nmse=nmse,
        mild_extrapolation_nmse=nmse,
        strong_extrapolation_nmse=nmse,
        expression_complexity=5 if completed else -1,
        runtime_seconds=0.5 if method == "fedfalsify-v05" else 1.5,
        communication_bytes=100 if method == "fedfalsify-v05" else 0,
        nominal_population_updates=0 if method == "fedfalsify-v05" else 100,
        expression="2*x1" if completed else "",
        note="ok" if completed else "equation export parse failure",
    )


def test_incomplete_pysr_row_is_retained_as_binary_failure() -> None:
    rows: list[PySRValidationRow] = []
    for regime in BUDGETS:
        rows.extend(
            [
                _row(
                    seed=10501,
                    regime=regime,
                    method="fedfalsify-v05",
                    completed=True,
                    semantic=1.0,
                    nmse=1e-5,
                ),
                _row(
                    seed=10501,
                    regime=regime,
                    method="official-pysr",
                    completed=False,
                    semantic=0.0,
                    nmse=float("nan"),
                ),
            ]
        )

    result = summarize(rows)
    for regime in BUDGETS:
        method = result["methods"][f"{regime}:official-pysr"]
        assert method["runs"] == 1
        assert method["completed"] == 0
        assert method["failed_or_incomplete"] == 1
        assert method["semantic_all_1e3"] == 0.0
        assert method["strong_extrapolation_nmse"]["mean"] is None
        assert method["strong_extrapolation_nmse"]["finite_rows"] == 0

        paired = result["paired"][regime]
        assert paired["pairs"] == 1
        assert paired["pysr_failed_or_incomplete_pairs"] == 1
        assert paired["semantic_1e3_mcnemar"]["reference_only_success"] == 1
        assert paired["strong_extrapolation_pysr_minus_fedfalsify"]["finite_pairs"] == 0
        assert paired["strong_extrapolation_pysr_minus_fedfalsify"]["estimate"] is None

    encoded = json.dumps(result, allow_nan=False)
    assert "NaN" not in encoded


def test_finite_pysr_rows_still_contribute_to_continuous_analysis() -> None:
    rows: list[PySRValidationRow] = []
    for regime in BUDGETS:
        for seed, pysr_nmse in ((10501, 0.02), (10502, float("nan"))):
            rows.extend(
                [
                    _row(
                        seed=seed,
                        regime=regime,
                        method="fedfalsify-v05",
                        completed=True,
                        semantic=1.0,
                        nmse=0.001,
                    ),
                    _row(
                        seed=seed,
                        regime=regime,
                        method="official-pysr",
                        completed=math.isfinite(pysr_nmse),
                        semantic=float(math.isfinite(pysr_nmse)),
                        nmse=pysr_nmse,
                    ),
                ]
            )

    result = summarize(rows)
    for regime in BUDGETS:
        paired = result["paired"][regime]
        assert paired["strong_extrapolation_pysr_minus_fedfalsify"]["finite_pairs"] == 1
        assert paired["strong_extrapolation_pysr_minus_fedfalsify"]["estimate"] is None
        summary = result["methods"][f"{regime}:official-pysr"]
        assert summary["strong_extrapolation_nmse"]["finite_rows"] == 1
        assert summary["strong_extrapolation_nmse"]["mean"] == 0.02
