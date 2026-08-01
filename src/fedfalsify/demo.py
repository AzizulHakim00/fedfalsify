"""Command-line demonstration of the first FedFalsify milestone."""

from __future__ import annotations

import argparse

from .basis import TermCatalog
from .client import FederatedFalsifierClient
from .data import generate_heterogeneous_clients
from .server import FedFalsifyDiscovery


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Discover a hidden equation from federated falsification certificates."
    )
    parser.add_argument("--samples", type=int, default=500)
    parser.add_argument("--noise", type=float, default=0.03)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--rounds", type=int, default=8)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    catalog = TermCatalog()
    datasets = generate_heterogeneous_clients(
        samples_per_client=args.samples,
        noise_std=args.noise,
        seed=args.seed,
    )
    clients = [FederatedFalsifierClient(dataset, catalog) for dataset in datasets]
    discovery = FedFalsifyDiscovery(
        clients,
        catalog,
        max_rounds=args.rounds,
        target_mse=max(args.noise**2 * 2.5, 1e-5),
    )
    result = discovery.discover()

    print("FedFalsify discovery trace")
    print("=" * 72)
    for record in result.history:
        repair = record.selected_repair or "stop"
        score = "-" if record.repair_score is None else f"{record.repair_score:.4f}"
        print(
            f"round={record.round_index:02d}  "
            f"mse={record.weighted_mse:.6f}  "
            f"worst={record.worst_client_mse:.6f}  "
            f"repair={repair:<9} score={score}"
        )
        print(f"  hypothesis: {record.candidate.expression(catalog)}")

    print("-" * 72)
    print(f"final: {result.candidate.expression(catalog)}")
    print(f"terms: {', '.join(result.candidate.active_terms)}")
    print(f"status: {result.stop_reason}")
    print("ground truth: 2·x₁ + 1·sin(x₂) + 0.5·x₃²")


if __name__ == "__main__":
    main()
