"""Preregistered v0.4 coefficient-heterogeneity ablation study."""

from __future__ import annotations

import argparse
from pathlib import Path
from statistics import mean

from .benchmarks import BENCHMARKS
from .experiments import print_summary, run_pilot, write_csv

METHODS = ("fedfalsify-no-heterogeneity", "fedfalsify")


def run_study(
    *,
    benchmarks: tuple[str, ...] = tuple(BENCHMARKS),
    seeds: tuple[int, ...] = (2026, 2027, 2028, 2029, 2030),
    samples: tuple[int, ...] = (120, 300),
    noise_ratio: float = 0.03,
    max_terms: int = 6,
):
    rows = []
    for sample_count in samples:
        rows.extend(
            run_pilot(
                benchmarks=benchmarks,
                scenarios=("exception",),
                noise_ratios=(noise_ratio,),
                seeds=seeds,
                methods=METHODS,
                samples_per_client=sample_count,
                max_terms=max_terms,
            )
        )
    return rows


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compare FedFalsify with and without coefficient-heterogeneity "
            "certificates on restricted-domain exceptions."
        )
    )
    parser.add_argument("--output", type=Path, default=Path("results/v04.csv"))
    parser.add_argument("--smoke", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.smoke:
        rows = run_study(
            benchmarks=("base",),
            seeds=(2026, 2027, 2028),
            samples=(120,),
        )
    else:
        rows = run_study()
    write_csv(rows, args.output)
    print_summary(rows)
    print("\nException recovery comparison")
    print("=" * 64)
    for method in METHODS:
        selected = [row for row in rows if row.method == method]
        print(
            f"{method:32} "
            f"exception={mean(row.exception_recovered for row in selected):.3f} "
            f"exact={mean(row.exact_recovery for row in selected):.3f} "
            f"nmse={mean(row.test_nmse for row in selected):.5f}"
        )
    print(f"\nWrote {len(rows)} rows to {args.output}")


if __name__ == "__main__":
    main()
