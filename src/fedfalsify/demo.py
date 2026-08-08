"""Command-line demonstrations of the FedFalsify research milestones."""

from __future__ import annotations

import argparse

from .basis import TermCatalog
from .benchmarks import run_exception_benchmark, run_spurious_correlation_benchmark
from .client import FederatedFalsifierClient
from .data import generate_heterogeneous_clients
from .server import DiscoveryResult, FedFalsifyDiscovery


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Discover hidden mechanisms from federated falsification certificates."
    )
    parser.add_argument(
        "--benchmark",
        choices=("base", "spurious", "exception"),
        default="base",
    )
    parser.add_argument("--samples", type=int, default=500)
    parser.add_argument("--noise", type=float, default=0.03)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--rounds", type=int, default=8)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.benchmark == "spurious":
        benchmark = run_spurious_correlation_benchmark(
            seed=args.seed,
            samples_per_client=args.samples,
            noise_std=args.noise,
        )
        catalog = TermCatalog()
        result = benchmark.result
        title = benchmark.name
    elif args.benchmark == "exception":
        benchmark = run_exception_benchmark(
            seed=args.seed,
            samples_per_client=args.samples,
            noise_std=args.noise,
        )
        catalog = TermCatalog(include_exception_terms=True)
        result = benchmark.result
        title = benchmark.name
    else:
        catalog = TermCatalog()
        datasets = generate_heterogeneous_clients(
            samples_per_client=args.samples,
            noise_std=args.noise,
            seed=args.seed,
        )
        clients = [FederatedFalsifierClient(dataset, catalog) for dataset in datasets]
        result = FedFalsifyDiscovery(
            clients,
            catalog,
            max_rounds=args.rounds,
            target_mse=max(args.noise**2 * 2.5, 1e-5),
        ).discover()
        title = "complementary-domain mechanism recovery"

    _print_result(title, result, catalog)


def _print_result(title: str, result: DiscoveryResult, catalog: TermCatalog) -> None:
    print(f"FedFalsify: {title}")
    print("=" * 86)
    for record in result.history:
        repair = record.selected_repair or "stop"
        kind = record.repair_kind or "-"
        score = "-" if record.repair_score is None else f"{record.repair_score:.4f}"
        print(
            f"round={record.round_index:02d} mse={record.weighted_mse:.6f} "
            f"worst={record.worst_client_mse:.6f} repair={repair:<18} "
            f"kind={kind:<9} score={score} "
            f"support={record.supporting_clients}/{record.observable_clients}"
        )
        print(f"  hypothesis: {record.candidate.expression(catalog)}")

    print("-" * 86)
    print(f"final: {result.candidate.expression(catalog)}")
    print(f"invariant core: {result.candidate.invariant_expression(catalog)}")
    exceptions = result.candidate.exception_expressions(catalog)
    print(f"exceptions: {', '.join(exceptions) if exceptions else 'none'}")
    print(f"status: {result.stop_reason}")


if __name__ == "__main__":
    main()
