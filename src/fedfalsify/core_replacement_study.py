"""Disjoint-seed v0.4 versus v0.5 core-surrogate replacement study."""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict
from pathlib import Path
from statistics import mean
from time import perf_counter

from .baselines import MethodOutput, fedfalsify_method
from .benchmarks import BENCHMARKS, benchmark_catalog, generate_benchmark
from .client import FederatedFalsifierClient
from .evaluation import EvaluationRow, evaluate_output
from .replacement import FederatedCoreReplacement, ReplacementCertificate

METHODS = ("fedfalsify-v04", "fedfalsify-v05-core-replacement")
DEFAULT_SEEDS = tuple(range(3031, 3041))
DEFAULT_SAMPLE_SIZES = (120, 300)


def _run_method(
    *,
    benchmark: str,
    seed: int,
    samples_per_client: int,
    noise_ratio: float,
    max_terms: int,
    method: str,
) -> tuple[EvaluationRow, tuple[ReplacementCertificate, ...]]:
    generated = generate_benchmark(
        benchmark,
        scenario="exception",
        samples_per_client=samples_per_client,
        noise_ratio=noise_ratio,
        seed=seed,
    )
    catalog = benchmark_catalog(scenario="exception")
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
        use_coefficient_heterogeneity=True,
    )
    replacements: tuple[ReplacementCertificate, ...] = ()
    if method == "fedfalsify-v04":
        output = MethodOutput(
            method,
            base.candidates,
            base.rounds,
            base.communication_bytes,
            perf_counter() - start,
            base.stop_reason,
        )
    elif method == "fedfalsify-v05-core-replacement":
        refined = FederatedCoreReplacement(
            clients,
            catalog,
            max_rounds=3,
            max_removed_terms=2,
        ).refine(base.candidate)
        replacements = refined.replacements
        output = MethodOutput(
            method,
            (refined.candidate,),
            base.rounds + len(refined.replacements),
            base.communication_bytes + refined.communication_bytes,
            perf_counter() - start,
            f"{base.stop_reason}; {refined.stop_reason}",
        )
    else:
        raise KeyError(f"Unknown method: {method}")
    return (
        evaluate_output(
            output,
            generated,
            catalog,
            noise_ratio=noise_ratio,
            seed=seed,
        ),
        replacements,
    )


def run_study(
    *,
    benchmarks: tuple[str, ...] = tuple(BENCHMARKS),
    seeds: tuple[int, ...] = DEFAULT_SEEDS,
    sample_sizes: tuple[int, ...] = DEFAULT_SAMPLE_SIZES,
    methods: tuple[str, ...] = METHODS,
    noise_ratio: float = 0.03,
    max_terms: int = 6,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for benchmark in benchmarks:
        for samples_per_client in sample_sizes:
            for seed in seeds:
                for method in methods:
                    evaluation, replacements = _run_method(
                        benchmark=benchmark,
                        seed=seed,
                        samples_per_client=samples_per_client,
                        noise_ratio=noise_ratio,
                        max_terms=max_terms,
                        method=method,
                    )
                    record = evaluation.to_dict()
                    record["samples_per_client"] = samples_per_client
                    record["replacement_count"] = len(replacements)
                    record["replacement_ledger"] = " | ".join(
                        f"{'+'.join(item.removed_terms)}->{item.added_term}"
                        for item in replacements
                    )
                    rows.append(record)
    return rows


def write_csv(rows: list[dict[str, object]], output: Path) -> None:
    if not rows:
        raise ValueError("No study rows to write")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def print_summary(rows: list[dict[str, object]]) -> None:
    print("\nCore-surrogate replacement summary")
    print("=" * 96)
    print(
        f"{'method':38} {'exact':>8} {'precision':>10} {'recall':>8} "
        f"{'NMSE':>10} {'exception':>10} {'repl.':>8}"
    )
    for method in METHODS:
        selected = [row for row in rows if row["method"] == method]
        if not selected:
            continue
        print(
            f"{method:38} "
            f"{mean(float(row['exact_recovery']) for row in selected):8.3f} "
            f"{mean(float(row['term_precision']) for row in selected):10.3f} "
            f"{mean(float(row['term_recall']) for row in selected):8.3f} "
            f"{mean(float(row['test_nmse']) for row in selected):10.5f} "
            f"{mean(float(row['exception_recovered']) for row in selected):10.3f} "
            f"{mean(float(row['replacement_count']) for row in selected):8.3f}"
        )
    failures = [
        row
        for row in rows
        if row["method"] == "fedfalsify-v05-core-replacement"
        and float(row["exact_recovery"]) < 1.0
    ]
    print(f"\nv0.5 retained failures: {len(failures)}")
    for row in failures[:20]:
        print(
            f"- {row['benchmark']} seed={row['seed']} samples={row['samples_per_client']} "
            f"terms={row['discovered_terms']} replacements={row['replacement_ledger']}"
        )


def _parse_ints(value: str) -> tuple[int, ...]:
    return tuple(int(item.strip()) for item in value.split(",") if item.strip())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compare v0.4 with v0.5 federated core-surrogate replacement."
    )
    parser.add_argument("--benchmarks", default=",".join(BENCHMARKS))
    parser.add_argument("--seeds", default=",".join(map(str, DEFAULT_SEEDS)))
    parser.add_argument(
        "--sample-sizes", default=",".join(map(str, DEFAULT_SAMPLE_SIZES))
    )
    parser.add_argument("--noise-ratio", type=float, default=0.03)
    parser.add_argument("--max-terms", type=int, default=6)
    parser.add_argument(
        "--output", type=Path, default=Path("results/v05_core_replacement.csv")
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Run a small targeted matrix for CI.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.smoke:
        benchmarks = ("base", "poly3")
        seeds = (2030, 3031)
        sample_sizes = (120,)
    else:
        benchmarks = tuple(
            item.strip() for item in args.benchmarks.split(",") if item.strip()
        )
        seeds = _parse_ints(args.seeds)
        sample_sizes = _parse_ints(args.sample_sizes)
    rows = run_study(
        benchmarks=benchmarks,
        seeds=seeds,
        sample_sizes=sample_sizes,
        noise_ratio=args.noise_ratio,
        max_terms=args.max_terms,
    )
    write_csv(rows, args.output)
    print_summary(rows)
    print(f"\nWrote {len(rows)} rows to {args.output}")


if __name__ == "__main__":
    main()
