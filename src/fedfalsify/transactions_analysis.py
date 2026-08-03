"""Transactions-level semantic equivalence and failure analysis.

This module intentionally analyzes frozen confirmatory CSV files without
modifying or re-running the original experiments.  It evaluates reported
expressions on deterministic interpolation and extrapolation domains, then
separates strict structural failures from functional-equivalence successes.
"""

from __future__ import annotations

import argparse
import ast
from collections import defaultdict
import csv
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
from typing import Any, Iterable

import numpy as np

from .benchmarks import (
    BENCHMARKS,
    benchmark_catalog,
    evaluate_terms,
    generate_benchmark,
    generate_global_test_data,
)


DEFAULT_INPUT = Path(
    "results/colab/v06-primary-confirmatory/final/v06_confirmatory.csv"
)
DEFAULT_OUTPUT_DIR = Path("results/transactions_phase1")
STRICT_SEMANTIC_THRESHOLD = 1e-3
RELAXED_SEMANTIC_THRESHOLD = 1e-2

_SUBSCRIPT_TRANSLATION = str.maketrans(
    {
        "₀": "0",
        "₁": "1",
        "₂": "2",
        "₃": "3",
        "₄": "4",
        "₅": "5",
        "₆": "6",
        "₇": "7",
        "₈": "8",
        "₉": "9",
        "−": "-",
        "–": "-",
        "—": "-",
        "·": "*",
        "×": "*",
    }
)


@dataclass(frozen=True)
class SemanticMetrics:
    normalized_expression: str
    expression_complexity: int
    interpolation_nmse: float
    client_support_nmse: float
    mild_extrapolation_nmse: float
    strong_extrapolation_nmse: float
    semantic_interpolation_recovery: float
    semantic_mild_recovery: float
    semantic_strong_recovery: float
    semantic_all_recovery: float
    semantic_all_relaxed_recovery: float
    parse_ok: float
    parse_error: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def normalize_expression(expression: str) -> str:
    """Normalize the two human-readable expression formats used in the CSV."""

    text = expression.strip().translate(_SUBSCRIPT_TRANSLATION)
    text = text.replace("²", "**2").replace("³", "**3")
    text = re.sub(
        r"I\s*\(\s*x3\s*>\s*1(?:\.0+)?\s*\)",
        "indicator(x3)",
        text,
    )
    text = text.replace("^", "**")
    text = re.sub(r"\bx([1-9])x([1-9])\b", r"x\1*x\2", text)
    text = re.sub(
        r"\)\s*(?=(?:sin|cos|indicator)\s*\(|x[1-9]\b|\()",
        ")*",
        text,
    )
    text = re.sub(r"\s+", " ", text).strip()
    return text


class _SafeExpressionEvaluator(ast.NodeVisitor):
    """Evaluate a deliberately small numeric expression language."""

    _binary_operators = {
        ast.Add: lambda left, right: left + right,
        ast.Sub: lambda left, right: left - right,
        ast.Mult: lambda left, right: left * right,
        ast.Div: lambda left, right: left / right,
    }

    def __init__(self, x: np.ndarray) -> None:
        if x.ndim != 2:
            raise ValueError("x must be a two-dimensional matrix")
        self.x = np.asarray(x, dtype=float)

    def visit_Expression(self, node: ast.Expression) -> Any:
        return self.visit(node.body)

    def visit_Constant(self, node: ast.Constant) -> float:
        if not isinstance(node.value, (int, float)):
            raise ValueError("only numeric constants are allowed")
        value = float(node.value)
        if not np.isfinite(value):
            raise ValueError("non-finite constants are not allowed")
        return value

    def visit_Name(self, node: ast.Name) -> np.ndarray:
        match = re.fullmatch(r"x([1-9][0-9]*)", node.id)
        if match is None:
            raise ValueError(f"unknown variable: {node.id}")
        index = int(match.group(1)) - 1
        if index >= self.x.shape[1]:
            raise ValueError(
                f"expression requests x{index + 1}, but x has {self.x.shape[1]} columns"
            )
        return self.x[:, index]

    def visit_UnaryOp(self, node: ast.UnaryOp) -> Any:
        operand = self.visit(node.operand)
        if isinstance(node.op, ast.UAdd):
            return operand
        if isinstance(node.op, ast.USub):
            return -operand
        raise ValueError("unsupported unary operator")

    def visit_BinOp(self, node: ast.BinOp) -> Any:
        left = self.visit(node.left)
        right = self.visit(node.right)
        for operator_type, implementation in self._binary_operators.items():
            if isinstance(node.op, operator_type):
                with np.errstate(all="raise"):
                    return implementation(left, right)
        if isinstance(node.op, ast.Pow):
            exponent = right
            if isinstance(exponent, np.ndarray):
                raise ValueError("array-valued exponents are not allowed")
            exponent_float = float(exponent)
            if exponent_float not in {2.0, 3.0}:
                raise ValueError("only square and cube powers are allowed")
            with np.errstate(all="raise"):
                return np.power(left, exponent_float)
        raise ValueError("unsupported binary operator")

    def visit_Call(self, node: ast.Call) -> Any:
        if not isinstance(node.func, ast.Name):
            raise ValueError("only direct function calls are allowed")
        if len(node.args) != 1 or node.keywords:
            raise ValueError("functions must have exactly one positional argument")
        argument = self.visit(node.args[0])
        if node.func.id == "sin":
            return np.sin(argument)
        if node.func.id == "cos":
            return np.cos(argument)
        if node.func.id == "square":
            return np.asarray(argument) ** 2
        if node.func.id == "indicator":
            return (np.asarray(argument) > 1.0).astype(float)
        raise ValueError(f"unsupported function: {node.func.id}")

    def generic_visit(self, node: ast.AST) -> Any:
        raise ValueError(f"unsupported syntax: {type(node).__name__}")


def evaluate_expression(expression: str, x: np.ndarray) -> tuple[np.ndarray, str]:
    normalized = normalize_expression(expression)
    tree = ast.parse(normalized, mode="eval")
    values = _SafeExpressionEvaluator(x).visit(tree)
    result = np.asarray(values, dtype=float)
    if result.ndim == 0:
        result = np.full(x.shape[0], float(result), dtype=float)
    if result.shape != (x.shape[0],):
        raise ValueError(
            f"expression returned shape {result.shape}; expected {(x.shape[0],)}"
        )
    if not np.all(np.isfinite(result)):
        raise ValueError("expression produced non-finite values")
    return result, normalized


def expression_complexity(expression: str) -> int:
    tree = ast.parse(normalize_expression(expression), mode="eval")
    ignored = (ast.Expression, ast.Load)
    return sum(1 for node in ast.walk(tree) if not isinstance(node, ignored))


def normalized_mse(prediction: np.ndarray, target: np.ndarray) -> float:
    prediction = np.asarray(prediction, dtype=float)
    target = np.asarray(target, dtype=float)
    return float(
        np.mean((target - prediction) ** 2) / max(float(np.var(target)), 1e-12)
    )


def _extrapolation_data(
    generated: Any,
    *,
    scale: float,
    samples: int,
    seed: int,
) -> tuple[np.ndarray, np.ndarray]:
    if scale <= 1.0:
        raise ValueError("extrapolation scale must be greater than one")
    rng = np.random.default_rng(seed)
    x = np.column_stack(
        [
            rng.uniform(-3.0 * scale, 3.0 * scale, size=samples),
            rng.uniform(-np.pi * scale, np.pi * scale, size=samples),
            rng.uniform(-2.5 * scale, 2.5 * scale, size=samples),
            rng.normal(0.0, scale, size=samples),
        ]
    )
    catalog = benchmark_catalog(scenario=generated.scenario)
    y = evaluate_terms(x, generated.target_coefficients, catalog)
    return x, y


def semantic_metrics_for_row(
    row: dict[str, str],
    *,
    samples: int = 4000,
    strict_threshold: float = STRICT_SEMANTIC_THRESHOLD,
    relaxed_threshold: float = RELAXED_SEMANTIC_THRESHOLD,
) -> SemanticMetrics:
    """Evaluate one reported equation on deterministic unseen domains."""

    benchmark = row["benchmark"]
    scenario = row["scenario"]
    seed = int(row["seed"])
    generated = generate_benchmark(
        benchmark,
        scenario=scenario,
        samples_per_client=int(row["samples_per_client"]),
        noise_ratio=float(row["noise_ratio"]),
        seed=seed,
        num_clients=int(row["num_clients"]),
    )
    x_interpolation, y_interpolation = generate_global_test_data(
        generated,
        samples=samples,
        seed=seed + 100_000,
    )
    client_x = np.concatenate([client.x for client in generated.clients], axis=0)
    client_y = evaluate_terms(
        client_x,
        generated.target_coefficients,
        benchmark_catalog(scenario=scenario),
    )
    x_mild, y_mild = _extrapolation_data(
        generated,
        scale=1.25,
        samples=samples,
        seed=seed + 200_000,
    )
    x_strong, y_strong = _extrapolation_data(
        generated,
        scale=1.50,
        samples=samples,
        seed=seed + 300_000,
    )

    try:
        interpolation_prediction, normalized = evaluate_expression(
            row["expression"], x_interpolation
        )
        client_prediction, _ = evaluate_expression(row["expression"], client_x)
        mild_prediction, _ = evaluate_expression(row["expression"], x_mild)
        strong_prediction, _ = evaluate_expression(row["expression"], x_strong)
        interpolation_nmse = normalized_mse(
            interpolation_prediction, y_interpolation
        )
        client_nmse = normalized_mse(client_prediction, client_y)
        mild_nmse = normalized_mse(mild_prediction, y_mild)
        strong_nmse = normalized_mse(strong_prediction, y_strong)
        complexity = expression_complexity(row["expression"])
        strict_values = (
            interpolation_nmse,
            client_nmse,
            mild_nmse,
            strong_nmse,
        )
        return SemanticMetrics(
            normalized_expression=normalized,
            expression_complexity=complexity,
            interpolation_nmse=interpolation_nmse,
            client_support_nmse=client_nmse,
            mild_extrapolation_nmse=mild_nmse,
            strong_extrapolation_nmse=strong_nmse,
            semantic_interpolation_recovery=float(
                interpolation_nmse <= strict_threshold
            ),
            semantic_mild_recovery=float(mild_nmse <= strict_threshold),
            semantic_strong_recovery=float(strong_nmse <= strict_threshold),
            semantic_all_recovery=float(
                max(strict_values) <= strict_threshold
            ),
            semantic_all_relaxed_recovery=float(
                max(strict_values) <= relaxed_threshold
            ),
            parse_ok=1.0,
            parse_error="",
        )
    except (SyntaxError, ValueError, FloatingPointError, OverflowError) as exc:
        return SemanticMetrics(
            normalized_expression=normalize_expression(row["expression"]),
            expression_complexity=-1,
            interpolation_nmse=float("nan"),
            client_support_nmse=float("nan"),
            mild_extrapolation_nmse=float("nan"),
            strong_extrapolation_nmse=float("nan"),
            semantic_interpolation_recovery=0.0,
            semantic_mild_recovery=0.0,
            semantic_strong_recovery=0.0,
            semantic_all_recovery=0.0,
            semantic_all_relaxed_recovery=0.0,
            parse_ok=0.0,
            parse_error=f"{type(exc).__name__}: {exc}",
        )


def target_terms(benchmark: str, scenario: str) -> set[str]:
    terms = set(BENCHMARKS[benchmark].target_terms)
    if scenario == "exception":
        terms.add("I(x3>1)*x3^2")
    return terms


def discovered_terms(row: dict[str, str]) -> set[str]:
    return {
        item.strip()
        for item in row.get("discovered_terms", "").replace(" | ", ";").split(";")
        if item.strip()
    }


def classify_row(
    row: dict[str, str],
    metrics: SemanticMetrics,
) -> dict[str, object]:
    expected = target_terms(row["benchmark"], row["scenario"])
    predicted = discovered_terms(row)
    missing = sorted(expected - predicted)
    extra = sorted(predicted - expected)
    strict_success = float(row["exact_recovery"]) >= 0.5

    if strict_success:
        category = "strict_success"
    elif metrics.parse_ok < 0.5:
        category = "expression_parse_failure"
    elif metrics.semantic_all_recovery >= 0.5:
        category = "strict_mismatch_semantic_success"
    elif missing and extra:
        category = "missing_and_extra_terms"
    elif missing:
        category = "missing_true_terms"
    elif extra:
        category = "extra_terms"
    else:
        category = "coefficient_or_generalization_failure"

    return {
        "target_terms": ";".join(sorted(expected)),
        "missing_terms": ";".join(missing),
        "extra_terms": ";".join(extra),
        "failure_category": category,
    }


def _mean(values: Iterable[float]) -> float:
    selected = [float(value) for value in values if np.isfinite(float(value))]
    return float(np.mean(selected)) if selected else float("nan")


def _group_summary(rows: list[dict[str, object]]) -> dict[str, object]:
    return {
        "runs": len(rows),
        "strict_exact_recovery": _mean(
            float(row["exact_recovery"]) for row in rows
        ),
        "semantic_interpolation_recovery": _mean(
            float(row["semantic_interpolation_recovery"]) for row in rows
        ),
        "semantic_all_recovery": _mean(
            float(row["semantic_all_recovery"]) for row in rows
        ),
        "semantic_all_relaxed_recovery": _mean(
            float(row["semantic_all_relaxed_recovery"]) for row in rows
        ),
        "interpolation_nmse": _mean(
            float(row["interpolation_nmse"]) for row in rows
        ),
        "mild_extrapolation_nmse": _mean(
            float(row["mild_extrapolation_nmse"]) for row in rows
        ),
        "strong_extrapolation_nmse": _mean(
            float(row["strong_extrapolation_nmse"]) for row in rows
        ),
        "mean_expression_complexity": _mean(
            float(row["expression_complexity"])
            for row in rows
            if float(row["expression_complexity"]) >= 0
        ),
        "parse_failures": int(
            sum(float(row["parse_ok"]) < 0.5 for row in rows)
        ),
    }


def _threshold_sensitivity(
    rows: list[dict[str, object]],
    thresholds: tuple[float, ...] = (1e-4, 1e-3, 1e-2),
) -> dict[str, dict[str, float]]:
    by_method: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        by_method[str(row["method"])].append(row)
    result: dict[str, dict[str, float]] = {}
    metric_names = (
        "interpolation_nmse",
        "client_support_nmse",
        "mild_extrapolation_nmse",
        "strong_extrapolation_nmse",
    )
    for method, selected in sorted(by_method.items()):
        method_result: dict[str, float] = {}
        for threshold in thresholds:
            successes = 0
            for row in selected:
                values = [float(row[name]) for name in metric_names]
                if all(np.isfinite(value) for value in values) and max(values) <= threshold:
                    successes += 1
            method_result[f"{threshold:.0e}"] = successes / len(selected)
        result[method] = method_result
    return result


def analyze_rows(
    input_rows: list[dict[str, str]],
    *,
    samples: int = 4000,
    strict_threshold: float = STRICT_SEMANTIC_THRESHOLD,
    relaxed_threshold: float = RELAXED_SEMANTIC_THRESHOLD,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    enriched: list[dict[str, object]] = []
    for row in input_rows:
        metrics = semantic_metrics_for_row(
            row,
            samples=samples,
            strict_threshold=strict_threshold,
            relaxed_threshold=relaxed_threshold,
        )
        enriched.append(
            {
                **row,
                **metrics.to_dict(),
                **classify_row(row, metrics),
            }
        )

    by_method: dict[str, list[dict[str, object]]] = defaultdict(list)
    by_breakdown: dict[
        tuple[str, str, str, str], list[dict[str, object]]
    ] = defaultdict(list)
    for row in enriched:
        method = str(row["method"])
        by_method[method].append(row)
        by_breakdown[
            (
                method,
                str(row["benchmark"]),
                str(row["scenario"]),
                str(row["noise_ratio"]),
            )
        ].append(row)

    identities = [
        (
            row["benchmark"],
            row["scenario"],
            row["noise_ratio"],
            row["samples_per_client"],
            row["num_clients"],
            row["seed"],
            row["method"],
        )
        for row in enriched
    ]
    fedfalsify_failures = [
        row
        for row in enriched
        if row["method"] == "fedfalsify-v05"
        and float(row["exact_recovery"]) < 0.5
    ]
    failure_categories: dict[str, int] = defaultdict(int)
    for row in fedfalsify_failures:
        failure_categories[str(row["failure_category"])] += 1

    summary = {
        "schema_version": 1,
        "analysis": "transactions semantic-equivalence and failure taxonomy",
        "input_rows": len(enriched),
        "unique_method_condition_rows": len(set(identities)),
        "duplicate_method_condition_rows": len(enriched) - len(set(identities)),
        "strict_semantic_threshold": strict_threshold,
        "relaxed_semantic_threshold": relaxed_threshold,
        "domain_samples": samples,
        "methods": {
            method: _group_summary(rows)
            for method, rows in sorted(by_method.items())
        },
        "semantic_threshold_sensitivity": _threshold_sensitivity(enriched),
        "breakdown": [
            {
                "method": key[0],
                "benchmark": key[1],
                "scenario": key[2],
                "noise_ratio": key[3],
                **_group_summary(rows),
            }
            for key, rows in sorted(by_breakdown.items())
        ],
        "fedfalsify_strict_failures": {
            "count": len(fedfalsify_failures),
            "categories": dict(sorted(failure_categories.items())),
        },
        "scientific_boundary": [
            "This is a post-hoc analysis of frozen v0.6 evidence.",
            "It must not be used to retune seeds 9001--9020.",
            "Semantic thresholds must be reported with sensitivity analyses.",
            "Functional equivalence does not imply mechanistic identifiability.",
        ],
    }
    return enriched, summary


def _write_csv(rows: list[dict[str, object]], path: Path) -> None:
    if not rows:
        raise ValueError("cannot write an empty CSV")
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def run_analysis(
    input_path: Path,
    output_dir: Path,
    *,
    samples: int = 4000,
    strict_threshold: float = STRICT_SEMANTIC_THRESHOLD,
    relaxed_threshold: float = RELAXED_SEMANTIC_THRESHOLD,
) -> dict[str, object]:
    with input_path.open(newline="", encoding="utf-8") as handle:
        input_rows = list(csv.DictReader(handle))
    if not input_rows:
        raise ValueError(f"no rows found in {input_path}")

    enriched, summary = analyze_rows(
        input_rows,
        samples=samples,
        strict_threshold=strict_threshold,
        relaxed_threshold=relaxed_threshold,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    semantic_path = output_dir / "transactions_semantic_rows.csv"
    summary_path = output_dir / "transactions_summary.json"
    failures_path = output_dir / "fedfalsify_failure_taxonomy.csv"

    _write_csv(enriched, semantic_path)
    failures = [
        row
        for row in enriched
        if row["method"] == "fedfalsify-v05"
        and float(row["exact_recovery"]) < 0.5
    ]
    if failures:
        _write_csv(failures, failures_path)
    else:
        failures_path.write_text("", encoding="utf-8")
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(f"Analyzed {len(enriched)} method-runs")
    print(
        "FedFalsify strict failures:",
        summary["fedfalsify_strict_failures"]["count"],
    )
    print(f"Wrote {semantic_path}")
    print(f"Wrote {failures_path}")
    print(f"Wrote {summary_path}")
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Analyze frozen FedFalsify evidence using semantic equivalence, "
            "extrapolation, complexity and failure taxonomy."
        )
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--samples", type=int, default=4000)
    parser.add_argument(
        "--strict-threshold",
        type=float,
        default=STRICT_SEMANTIC_THRESHOLD,
    )
    parser.add_argument(
        "--relaxed-threshold",
        type=float,
        default=RELAXED_SEMANTIC_THRESHOLD,
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.samples < 200:
        raise ValueError("use at least 200 samples per semantic domain")
    if not 0 < args.strict_threshold <= args.relaxed_threshold:
        raise ValueError(
            "require 0 < strict-threshold <= relaxed-threshold"
        )
    run_analysis(
        args.input,
        args.output_dir,
        samples=args.samples,
        strict_threshold=args.strict_threshold,
        relaxed_threshold=args.relaxed_threshold,
    )


if __name__ == "__main__":
    main()
