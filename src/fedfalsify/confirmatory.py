"""Matched confirmatory runner for FedFalsify and controlled SR baselines."""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from statistics import mean
from time import perf_counter
from typing import Iterable

import numpy as np

from .baselines import fedfalsify_method
from .benchmarks import (
    BENCHMARKS,
    benchmark_catalog,
    generate_benchmark,
    generate_global_test_data,
)
from .client import FederatedFalsifierClient
from .expression_baselines import TreeSearchOutput, run_tree_search
from .replacement import FederatedCoreReplacement
from .statistics import mcnemar_exact, paired_bootstrap_difference, wilson_interval

METHODS = (
    "fedfalsify-v05",
    "centralized-tree-gp",
    "federated-tree-gp-style",
    "centralized-residual-counterexample-gp",
)
DEFAULT_SEEDS = tuple(range(5001, 5006))
DEFAULT_SCENARIOS = ("complementary", "spurious", "exception")
DEFAULT_NOISE = (0.0, 0.03, 0.10)
DEFAULT_SAMPLES = (120, 300)
DEFAULT_CLIENTS = (4,)


@dataclass(frozen=True)
class ConfirmatoryRow:
    benchmark: str
    scenario: str
    noise_ratio: float
    samples_per_client: int
    num_clients: int
    seed: int
    method: str
    exact_recovery: float
    term_precision: float
    term_recall: float
    test_nmse: float
    train_mse: float
    spurious_accepted: float
    exception_recovered: float
    runtime_seconds: float
    communication_bytes: int
    search_evaluations: int
    discovered_terms: str
    expression: str
    stop_reason: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _term_metrics(
    predicted: Iterable[str], target: Iterable[str]
) -> tuple[float, float, float]:
    predicted_set = set(predicted)
    target_set = set(target)
    intersection = predicted_set & target_set
    precision = len(intersection) / len(predicted_set) if predicted_set else float(not target_set)
    recall = len(intersection) / len(target_set) if target_set else 1.0
    return float(predicted_set == target_set), precision, recall


def _prediction_metrics(
    prediction: np.ndarray,
    target: np.ndarray,
) -> float:
    return float(np.mean((target - prediction) ** 2) / max(np.var(target), 1e-12))


def _finite_fedfalsify(
    generated,
    *,
    max_terms: int,
) -> tuple[object, float, int, int, str]:
    catalog = benchmark_catalog(scenario=generated.scenario)
    clients = [
        FederatedFalsifierClient(dataset, catalog) for dataset in generated.clients
    ]
    target_mse = max(generated.noise_std**2 * 2.5, 1e-8)
    start = perf_counter()
    base = fedfalsify_method(
        clients,
        catalog,
        max_terms=max_terms,
        target_mse=target_mse,
        min_repair_score=0.05,
        use_coefficient_heterogeneity=True,
    )
    refined = FederatedCoreReplacement(
        clients,
        catalog,
        max_rounds=3,
        max_removed_terms=2,
    ).refine(base.candidate)
    return (
        refined.candidate,
        perf_counter() - start,
        base.communication_bytes + refined.communication_bytes,
        base.rounds + len(refined.replacements),
        f"{base.stop_reason}; {refined.stop_reason}",
    )


def _evaluate_fedfalsify(
    generated,
    *,
    max_terms: int,
    seed: int,
) -> ConfirmatoryRow:
    candidate, runtime, communication, evaluations, stop_reason = _finite_fedfalsify(
        generated,
        max_terms=max_terms,
    )
    catalog = benchmark_catalog(scenario=generated.scenario)
    predicted = {
        term
        for term, coefficient in zip(candidate.active_terms, candidate.coefficients)
        if term != "1" and abs(coefficient) >= 1e-3
    }
    exact, precision, recall = _term_metrics(predicted, generated.target_terms)
    x_test, y_test = generate_global_test_data(generated, seed=seed + 100_000)
    prediction = candidate.predict(x_test, catalog)
    pooled_x = np.concatenate([dataset.x for dataset in generated.clients], axis=0)
    pooled_y = np.concatenate([dataset.y for dataset in generated.clients], axis=0)
    train_mse = float(np.mean((pooled_y - candidate.predict(pooled_x, catalog)) ** 2))
    spurious = float(bool({"x4", "x4^2"} & predicted))
    exception = "I(x3>1)*x3^2"
    exception_recovered = float(
        exception in predicted
        if generated.scenario == "exception"
        else exception not in predicted
    )
    return ConfirmatoryRow(
        benchmark=generated.spec.name,
        scenario=generated.scenario,
        noise_ratio=generated.noise_std
        / max(float(np.std(y_test)), 1e-12),
        samples_per_client=len(generated.clients[0].y),
        num_clients=len(generated.clients),
        seed=seed,
        method="fedfalsify-v05",
        exact_recovery=exact,
        term_precision=precision,
        term_recall=recall,
        test_nmse=_prediction_metrics(prediction, y_test),
        train_mse=train_mse,
        spurious_accepted=spurious,
        exception_recovered=exception_recovered,
        runtime_seconds=runtime,
        communication_bytes=communication,
        search_evaluations=evaluations,
        discovered_terms=";".join(sorted(predicted)),
        expression=candidate.expression(catalog),
        stop_reason=stop_reason,
    )


def _evaluate_tree(
    generated,
    *,
    mode: str,
    seed: int,
    population_size: int,
    generations: int,
    max_genes: int,
) -> ConfirmatoryRow:
    output: TreeSearchOutput = run_tree_search(
        generated.clients,
        mode=mode,
        seed=seed,
        population_size=population_size,
        generations=generations,
        max_genes=max_genes,
        max_complexity=7,
    )
    predicted = set(output.model.active_terms())
    exact, precision, recall = _term_metrics(predicted, generated.target_terms)
    x_test, y_test = generate_global_test_data(generated, seed=seed + 100_000)
    prediction = output.model.predict(x_test)
    pooled_x = np.concatenate([dataset.x for dataset in generated.clients], axis=0)
    pooled_y = np.concatenate([dataset.y for dataset in generated.clients], axis=0)
    train_mse = float(np.mean((pooled_y - output.model.predict(pooled_x)) ** 2))
    spurious = float(any("x4" in term for term in predicted))
    exception = "I(x3>1)*x3^2"
    exception_recovered = float(
        exception in predicted
        if generated.scenario == "exception"
        else exception not in predicted
    )
    return ConfirmatoryRow(
        benchmark=generated.spec.name,
        scenario=generated.scenario,
        noise_ratio=generated.noise_std
        / max(float(np.std(y_test)), 1e-12),
        samples_per_client=len(generated.clients[0].y),
        num_clients=len(generated.clients),
        seed=seed,
        method=output.method,
        exact_recovery=exact,
        term_precision=precision,
        term_recall=recall,
        test_nmse=_prediction_metrics(prediction, y_test),
        train_mse=train_mse,
        spurious_accepted=spurious,
        exception_recovered=exception_recovered,
        runtime_seconds=output.runtime_seconds,
        communication_bytes=output.communication_bytes,
        search_evaluations=output.evaluations,
        discovered_terms=";".join(sorted(predicted)),
        expression=output.model.expression(),
        stop_reason=output.stop_reason,
    )


def run_study(
    *,
    benchmarks: tuple[str, ...] = tuple(BENCHMARKS),
    scenarios: tuple[str, ...] = DEFAULT_SCENARIOS,
    noise_ratios: tuple[float, ...] = DEFAULT_NOISE,
    samples_per_client: tuple[int, ...] = DEFAULT_SAMPLES,
    client_counts: tuple[int, ...] = DEFAULT_CLIENTS,
    seeds: tuple[int, ...] = DEFAULT_SEEDS,
    methods: tuple[str, ...] = METHODS,
    max_terms: int = 6,
    population_size: int = 48,
    generations: int = 12,
    max_genes: int = 4,
) -> list[ConfirmatoryRow]:
    rows: list[ConfirmatoryRow] = []
    mode_by_method = {
        "centralized-tree-gp": "centralized",
        "federated-tree-gp-style": "federated",
        "centralized-residual-counterexample-gp": "counterexample",
    }
    for benchmark in benchmarks:
        for scenario in scenarios:
            for noise_ratio in noise_ratios:
                for sample_count in samples_per_client:
                    for client_count in client_counts:
                        for seed in seeds:
                            generated = generate_benchmark(
                                benchmark,
                                scenario=scenario,
                                samples_per_client=sample_count,
                                noise_ratio=noise_ratio,
                                seed=seed,
                                num_clients=client_count,
                            )
                            for method in methods:
                                if method == "fedfalsify-v05":
                                    row = _evaluate_fedfalsify(
                                        generated,
                                        max_terms=max_terms,
                                        seed=seed,
                                    )
                                else:
                                    if method not in mode_by_method:
                                        raise KeyError(f"unknown confirmatory method: {method}")
                                    row = _evaluate_tree(
                                        generated,
                                        mode=mode_by_method[method],
                                        seed=seed,
                                        population_size=population_size,
                                        generations=generations,
                                        max_genes=max_genes,
                                    )
                                # Store requested noise, not the realized outcome scale ratio.
                                rows.append(
                                    ConfirmatoryRow(
                                        **{
                                            **row.to_dict(),
                                            "noise_ratio": noise_ratio,
                                        }
                                    )
                                )
    return rows


def write_csv(rows: list[ConfirmatoryRow], output: Path) -> None:
    if not rows:
        raise ValueError("no confirmatory rows to write")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].to_dict()))
        writer.writeheader()
        writer.writerows(row.to_dict() for row in rows)


def _pair_key(row: ConfirmatoryRow) -> tuple[object, ...]:
    return (
        row.benchmark,
        row.scenario,
        row.noise_ratio,
        row.samples_per_client,
        row.num_clients,
        row.seed,
    )


def summarize(
    rows: list[ConfirmatoryRow],
    *,
    reference: str = "fedfalsify-v05",
    bootstrap_resamples: int = 2000,
) -> dict[str, object]:
    by_method: dict[str, list[ConfirmatoryRow]] = {}
    for row in rows:
        by_method.setdefault(row.method, []).append(row)
    summary: dict[str, object] = {"methods": {}, "paired": {}}
    for method, selected in sorted(by_method.items()):
        exact_successes = int(sum(row.exact_recovery for row in selected))
        lower, upper = wilson_interval(exact_successes, len(selected))
        summary["methods"][method] = {
            "runs": len(selected),
            "exact_recovery": mean(row.exact_recovery for row in selected),
            "exact_wilson_95": [lower, upper],
            "term_precision": mean(row.term_precision for row in selected),
            "term_recall": mean(row.term_recall for row in selected),
            "test_nmse": mean(row.test_nmse for row in selected),
            "spurious_accepted": mean(row.spurious_accepted for row in selected),
            "exception_recovered": mean(row.exception_recovered for row in selected),
            "runtime_seconds": mean(row.runtime_seconds for row in selected),
            "communication_bytes": mean(row.communication_bytes for row in selected),
        }
    if reference not in by_method:
        return summary
    reference_map = {_pair_key(row): row for row in by_method[reference]}
    for method, selected in sorted(by_method.items()):
        if method == reference:
            continue
        comparator_map = {_pair_key(row): row for row in selected}
        common = sorted(set(reference_map) & set(comparator_map))
        if not common:
            continue
        reference_exact = [reference_map[key].exact_recovery for key in common]
        comparator_exact = [comparator_map[key].exact_recovery for key in common]
        mcnemar = mcnemar_exact(reference_exact, comparator_exact)
        nmse = paired_bootstrap_difference(
            [reference_map[key].test_nmse for key in common],
            [comparator_map[key].test_nmse for key in common],
            resamples=bootstrap_resamples,
            seed=6201,
        )
        runtime = paired_bootstrap_difference(
            [reference_map[key].runtime_seconds for key in common],
            [comparator_map[key].runtime_seconds for key in common],
            resamples=bootstrap_resamples,
            seed=6202,
        )
        summary["paired"][method] = {
            "pairs": len(common),
            "mcnemar": asdict(mcnemar),
            "nmse_comparator_minus_reference": asdict(nmse),
            "runtime_comparator_minus_reference": asdict(runtime),
        }
    return summary


def _parse_strings(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _parse_ints(value: str) -> tuple[int, ...]:
    return tuple(int(item.strip()) for item in value.split(",") if item.strip())


def _parse_floats(value: str) -> tuple[float, ...]:
    return tuple(float(item.strip()) for item in value.split(",") if item.strip())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run matched FedFalsify v0.6 confirmatory baselines."
    )
    parser.add_argument("--benchmarks", default=",".join(BENCHMARKS))
    parser.add_argument("--scenarios", default=",".join(DEFAULT_SCENARIOS))
    parser.add_argument("--noise", default=",".join(map(str, DEFAULT_NOISE)))
    parser.add_argument("--samples", default=",".join(map(str, DEFAULT_SAMPLES)))
    parser.add_argument("--clients", default=",".join(map(str, DEFAULT_CLIENTS)))
    parser.add_argument("--seeds", default=",".join(map(str, DEFAULT_SEEDS)))
    parser.add_argument("--methods", default=",".join(METHODS))
    parser.add_argument("--max-terms", type=int, default=6)
    parser.add_argument("--population-size", type=int, default=48)
    parser.add_argument("--generations", type=int, default=12)
    parser.add_argument("--max-genes", type=int, default=4)
    parser.add_argument("--bootstrap-resamples", type=int, default=2000)
    parser.add_argument(
        "--output", type=Path, default=Path("results/v06_confirmatory.csv")
    )
    parser.add_argument(
        "--summary", type=Path, default=Path("results/v06_confirmatory_summary.json")
    )
    parser.add_argument("--smoke", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.smoke:
        settings = {
            "benchmarks": ("base",),
            "scenarios": ("complementary", "exception"),
            "noise_ratios": (0.03,),
            "samples_per_client": (60,),
            "client_counts": (4,),
            "seeds": (5001,),
            "methods": METHODS,
            "population_size": 12,
            "generations": 2,
            "max_genes": 3,
        }
        bootstrap_resamples = 500
    else:
        settings = {
            "benchmarks": _parse_strings(args.benchmarks),
            "scenarios": _parse_strings(args.scenarios),
            "noise_ratios": _parse_floats(args.noise),
            "samples_per_client": _parse_ints(args.samples),
            "client_counts": _parse_ints(args.clients),
            "seeds": _parse_ints(args.seeds),
            "methods": _parse_strings(args.methods),
            "population_size": args.population_size,
            "generations": args.generations,
            "max_genes": args.max_genes,
        }
        bootstrap_resamples = args.bootstrap_resamples
    rows = run_study(max_terms=args.max_terms, **settings)
    write_csv(rows, args.output)
    report = summarize(rows, bootstrap_resamples=bootstrap_resamples)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"Wrote {len(rows)} rows to {args.output}")


if __name__ == "__main__":
    main()
