"""Small official-PySR execution and archiving runner."""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from .benchmarks import generate_benchmark, generate_global_test_data
from .pysr_adapter import run_pysr


@dataclass(frozen=True)
class PySRStudyRow:
    benchmark: str
    scenario: str
    seed: int
    samples_per_client: int
    noise_ratio: float
    niterations: int
    populations: int
    population_size: int
    maxsize: int
    available: bool
    test_nmse: float
    runtime_seconds: float
    equation: str
    note: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def run_study(
    *,
    benchmark: str = "base",
    scenarios: tuple[str, ...] = ("complementary", "spurious"),
    seed: int = 8001,
    samples_per_client: int = 120,
    noise_ratio: float = 0.03,
    niterations: int = 40,
    populations: int = 6,
    population_size: int = 40,
    maxsize: int = 18,
) -> list[PySRStudyRow]:
    rows: list[PySRStudyRow] = []
    for scenario in scenarios:
        generated = generate_benchmark(
            benchmark,
            scenario=scenario,
            samples_per_client=samples_per_client,
            noise_ratio=noise_ratio,
            seed=seed,
            num_clients=4,
        )
        x_test, y_test = generate_global_test_data(generated, seed=seed + 100_000)
        output = run_pysr(
            generated.clients,
            x_test,
            seed=seed,
            niterations=niterations,
            populations=populations,
            population_size=population_size,
            maxsize=maxsize,
        )
        if output.available:
            nmse = float(
                np.mean((y_test - output.predictions) ** 2)
                / max(np.var(y_test), 1e-12)
            )
        else:
            nmse = float("nan")
        rows.append(
            PySRStudyRow(
                benchmark=benchmark,
                scenario=scenario,
                seed=seed,
                samples_per_client=samples_per_client,
                noise_ratio=noise_ratio,
                niterations=niterations,
                populations=populations,
                population_size=population_size,
                maxsize=maxsize,
                available=output.available,
                test_nmse=nmse,
                runtime_seconds=output.runtime_seconds,
                equation=output.equation,
                note=output.note,
            )
        )
    return rows


def write_csv(rows: list[PySRStudyRow], output: Path) -> None:
    if not rows:
        raise ValueError("no PySR rows to write")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].to_dict()))
        writer.writeheader()
        writer.writerows(row.to_dict() for row in rows)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run an official PySR pooled-data baseline."
    )
    parser.add_argument("--benchmark", default="base")
    parser.add_argument("--scenarios", default="complementary,spurious")
    parser.add_argument("--seed", type=int, default=8001)
    parser.add_argument("--samples", type=int, default=120)
    parser.add_argument("--noise-ratio", type=float, default=0.03)
    parser.add_argument("--niterations", type=int, default=40)
    parser.add_argument("--populations", type=int, default=6)
    parser.add_argument("--population-size", type=int, default=40)
    parser.add_argument("--maxsize", type=int, default=18)
    parser.add_argument(
        "--output", type=Path, default=Path("results/v06_official_pysr.csv")
    )
    parser.add_argument("--smoke", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    scenarios = tuple(
        item.strip() for item in args.scenarios.split(",") if item.strip()
    )
    if args.smoke:
        niterations = 5
        populations = 2
        population_size = 20
        maxsize = 14
        samples = 60
        scenarios = ("complementary",)
    else:
        niterations = args.niterations
        populations = args.populations
        population_size = args.population_size
        maxsize = args.maxsize
        samples = args.samples
    rows = run_study(
        benchmark=args.benchmark,
        scenarios=scenarios,
        seed=args.seed,
        samples_per_client=samples,
        noise_ratio=args.noise_ratio,
        niterations=niterations,
        populations=populations,
        population_size=population_size,
        maxsize=maxsize,
    )
    if not all(row.available for row in rows):
        raise RuntimeError("official PySR is unavailable; install the sr extra")
    write_csv(rows, args.output)
    for row in rows:
        print(
            f"scenario={row.scenario} nmse={row.test_nmse:.6g} "
            f"runtime={row.runtime_seconds:.3f}s equation={row.equation}"
        )
    print(f"Wrote {len(rows)} rows to {args.output}")


if __name__ == "__main__":
    main()
