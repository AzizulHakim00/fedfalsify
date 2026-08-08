from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

from fedfalsify.transactions_analysis import (
    analyze_rows,
    evaluate_expression,
    normalize_expression,
    run_analysis,
    semantic_metrics_for_row,
)


def test_unicode_expression_normalization_and_evaluation() -> None:
    x = np.asarray(
        [
            [1.0, 0.2, 2.0, 0.0],
            [-1.0, -0.5, 0.5, 0.0],
        ]
    )
    expression = "0.5 + 2·x₁ + 0.5·x₃² + sin(x₂)"
    prediction, normalized = evaluate_expression(expression, x)
    expected = 0.5 + 2.0 * x[:, 0] + 0.5 * x[:, 2] ** 2 + np.sin(x[:, 1])
    assert normalized == "0.5 + 2*x1 + 0.5*x3**2 + sin(x2)"
    np.testing.assert_allclose(prediction, expected)


def test_gate_and_implicit_trigonometric_product() -> None:
    x = np.asarray(
        [
            [0.5, 0.25, 2.0, 0.0],
            [-0.5, -0.25, 0.5, 0.0],
        ]
    )
    gated, normalized_gate = evaluate_expression("0.75·I(x₃>1)*x₃²", x)
    np.testing.assert_allclose(gated, np.asarray([3.0, 0.0]))
    assert normalized_gate == "0.75*indicator(x3)*x3**2"

    product, normalized_product = evaluate_expression("2·sin(x₁)cos(x₂)", x)
    np.testing.assert_allclose(
        product,
        2.0 * np.sin(x[:, 0]) * np.cos(x[:, 1]),
    )
    assert normalized_product == "2*sin(x1)*cos(x2)"


def _base_row(*, exact: str, discovered: str, expression: str) -> dict[str, str]:
    return {
        "benchmark": "base",
        "scenario": "complementary",
        "noise_ratio": "0.03",
        "samples_per_client": "60",
        "num_clients": "4",
        "seed": "9001",
        "method": "fedfalsify-v05",
        "exact_recovery": exact,
        "term_precision": "1.0",
        "term_recall": "1.0",
        "test_nmse": "0.0",
        "train_mse": "0.0",
        "spurious_accepted": "0.0",
        "exception_recovered": "1.0",
        "runtime_seconds": "0.1",
        "communication_bytes": "10",
        "search_evaluations": "1",
        "discovered_terms": discovered,
        "expression": expression,
        "stop_reason": "test",
    }


def test_true_expression_passes_all_semantic_domains() -> None:
    row = _base_row(
        exact="1.0",
        discovered="sin(x2);x1;x3^2",
        expression="2*x1 + sin(x2) + 0.5*x3^2",
    )
    metrics = semantic_metrics_for_row(row, samples=300)
    assert metrics.parse_ok == 1.0
    assert metrics.semantic_all_recovery == 1.0
    assert metrics.strong_extrapolation_nmse < 1e-12


def test_strict_mismatch_can_be_semantically_equivalent() -> None:
    row = _base_row(
        exact="0.0",
        discovered="expr:add(sin(x2),x1);expr:add(x1,x3^2)",
        expression="(sin(x2)+x1) + (x1+0.5*x3^2)",
    )
    enriched, summary = analyze_rows([row], samples=300)
    assert enriched[0]["failure_category"] == "strict_mismatch_semantic_success"
    assert enriched[0]["semantic_all_recovery"] == 1.0
    assert summary["fedfalsify_strict_failures"]["count"] == 1


def test_run_analysis_writes_reproducible_outputs(tmp_path: Path) -> None:
    input_path = tmp_path / "rows.csv"
    output_dir = tmp_path / "analysis"
    row = _base_row(
        exact="1.0",
        discovered="sin(x2);x1;x3^2",
        expression="2*x1 + sin(x2) + 0.5*x3^2",
    )
    with input_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)

    summary = run_analysis(input_path, output_dir, samples=300)
    assert summary["input_rows"] == 1
    assert (output_dir / "transactions_semantic_rows.csv").exists()
    assert (output_dir / "transactions_summary.json").exists()
    assert (output_dir / "fedfalsify_failure_taxonomy.csv").exists()


def test_normalization_rejects_no_supported_notation() -> None:
    assert normalize_expression("x₁x₂ + x₁³") == "x1*x2 + x1**3"
