"""Unified, reproducible pilot runner for preregistered FedFalsify comparisons."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from statistics import mean
from typing import Iterable

from .baselines import (
    centralized_forward,
    fedfalsify_method,
    local_forward,
    random_repair,
    score_only_federated,
)
from .benchmarks import BENCHMARKS, Scenario, benchmark_catalog, generate_benchmark
from .client import FederatedFalsifierClient
from .evaluation import EvaluationRow, evaluate_output

DEFAULT_METHODS = (
    "centralized-forward",
    "local-only-forward",
    "score-only-federated",
    "random-repair",
    "fedfalsify",
)
DEFAULT_SCENARIOS: tuple[Scenario, ...] = (
    "complementary",
    "spurious",
    "exception",
)


def _csv_list(value: str, cast=str) -> tuple:
    return tuple(cast(item.strip()) for item in value.split(",") if item.strip())


def run_one(
    *,
    benchmark: str,
    scenario: Scenario,
    noise_ratio: float,
    seed: int,
    method: str,
    samples_per_client: int,
    max_terms: int,
) -> EvaluationRow:
    generated = generate_benchmark(
        benchmark,
        scenario=scenario,
        samples_per_client=samples_per_client,
        noise_ratio=noise_ratio,
        seed=seed,
    )
    catalog = benchmark_catalog(scenario=scenario)
    clients = [
        FederatedFalsifierClient(dataset, catalog) for dataset in generated.clients
    ]
    target_mse = max(generated.noise_std**2 * 2.5, 1e-8)

    if method == "centralized-forward":
        output = centralized_forward(generated.clients, catalog, max_terms=max_terms)
    elif method == "local-only-forward":
        output = local_forward(generated.clients, catalog, max_terms=max_terms)
    elif method == "score-only-federated":
        output = score_only_federated(clients, catalog, max_terms=max_terms)
    elif method == "random-repair":
        output = random_repair(clients, catalog, max_terms=max_terms, seed=seed)
    elif method == "fedfalsify":
        output = fedfalsify_method(
            clients,
            catalog,
            max_terms=max_terms,
            target_mse=target_mse,
        )
    else:
        raise KeyError(f"Unknown method: {method}")

    return evaluate_output(
        output,
        generated,
        catalog,
        noise_ratio=noise_ratio,
        seed=seed,
    )


def run_pilot(
    *,
    benchmarks: Iterable[str],
    scenarios: Iterable[Scenario],
    noise_ratios: Iterable[float],
    seeds: Iterable[int],
    methods: Iterable[str],
    samples_per_client: int = 300,
    max_terms: int = 6,
) -> list[EvaluationRow]:
    rows: list[EvaluationRow] = []
    for benchmark in benchmarks:
        for scenario in scenarios:
            for noise_ratio in noise_ratios:
                for seed in seeds:
                    for method in methods:
                        rows.append(
                            run_one(
                                benchmark=benchmark,
                                scenario=scenario,
                                noise_ratio=noise_ratio,
                                seed=seed,
                                method=method,
                                samples_per_client=samples_per_client,
                                max_terms=max_terms,
                            )
                        )
    return rows


def write_csv(rows: list[EvaluationRow], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError("No experiment rows to write")
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].to_dict()))
        writer.writeheader()
        writer.writerows(row.to_dict() for row in rows)


def print_summary(rows: list[EvaluationRow]) -> None:
    print("\nPilot summary (mean over requested settings)")
    print("=" * 88)
    print(
        f"{'method':26} {'exact':>8} {'precision':>10} "
        f"{'recall':>8} {'NMSE':>10} {'spur.':>8}"
    )
    for method in sorted({row.method for row in rows}):
        selected = [row for row in rows if row.method == method]
        print(
            f"{method:26} "
            f"{mean(row.exact_recovery for row in selected):8.3f} "
            f"{mean(row.term_precision for row in selected):10.3f} "
            f"{mean(row.term_recall for row in selected):8.3f} "
            f"{mean(row.test_nmse for row in selected):10.4f} "
            f"{mean(row.spurious_accepted for row in selected):8.3f}"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the preregistered FedFalsify pilot matrix."
    )
    parser.add_argument("--benchmarks", default=",".join(BENCHMARKS))
    parser.add_argument("--scenarios", default=",".join(DEFAULT_SCENARIOS))
    parser.add_argument("--noise-ratios", default="0,0.03,0.10")
    parser.add_argument("--seeds", default="2026,2027,2028,2029,2030")
    parser.add_argument("--methods", default=",".join(DEFAULT_METHODS))
    parser.add_argument("--samples", type=int, default=300)
    parser.add_argument("--max-terms", type=int, default=6)
    parser.add_argument(
        "--output", type=Path, default=Path("results/pilot.csv")
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Run one benchmark, three scenarios, one seed and all methods for CI.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.smoke:
        benchmarks = ("base",)
        scenarios: tuple[Scenario, ...] = DEFAULT_SCENARIOS
        noise_ratios = (0.03,)
        seeds = (2026,)
    else:
        benchmarks = _csv_list(args.benchmarks)
        scenarios = _csv_list(args.scenarios)
        noise_ratios = _csv_list(args.noise_ratios, float)
        seeds = _csv_list(args.seeds, int)
    methods = _csv_list(args.methods)
    rows = run_pilot(
        benchmarks=benchmarks,
        scenarios=scenarios,
        noise_ratios=noise_ratios,
        seeds=seeds,
        methods=methods,
        samples_per_client=args.samples,
        max_terms=args.max_terms,
    )
    write_csv(rows, args.output)
    print_summary(rows)
    print(f"\nWrote {len(rows)} rows to {args.output}")


if __name__ == "__main__":
    main()
