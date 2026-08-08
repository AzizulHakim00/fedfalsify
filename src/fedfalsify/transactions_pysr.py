"""Transactions-scale official PySR comparison on fresh seeds.

The runner uses the official Julia-backed PySR package through the existing
adapter.  It separates unsupported exception grammars from search failures and
evaluates discovered equations on interpolation, client-support, and two
extrapolation domains.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
from importlib import metadata
import json
from pathlib import Path
import platform
from typing import Iterable

import numpy as np

from .benchmarks import (
    BENCHMARKS,
    benchmark_catalog,
    evaluate_terms,
    generate_benchmark,
    generate_global_test_data,
)
from .pysr_adapter import run_pysr
from .transactions_analysis import _extrapolation_data, normalized_mse
from .transactions_analysis_fixed import evaluate_expression, expression_complexity


FROZEN_CONFIRMATORY_SEEDS = frozenset(range(9001, 9021))
DEFAULT_DEVELOPMENT_SEEDS = tuple(range(10001, 10004))
SUPPORTED_SCENARIOS = frozenset({"complementary", "spurious"})


@dataclass(frozen=True)
class TransactionsPySRRow:
    benchmark: str
    scenario: str
    noise_ratio: float
    samples_per_client: int
    num_clients: int
    seed: int
    method: str
    grammar_supported: bool
    package_available: bool
    completed: bool
    niterations: int
    populations: int
    population_size: int
    maxsize: int
    nominal_population_updates: int
    runtime_seconds: float
    interpolation_nmse: float
    client_support_nmse: float
    mild_extrapolation_nmse: float
    strong_extrapolation_nmse: float
    semantic_all_1e4: float
    semantic_all_1e3: float
    semantic_all_1e2: float
    expression_complexity: int
    equation: str
    note: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def validate_fresh_seeds(seeds: Iterable[int]) -> tuple[int, ...]:
    values = tuple(int(seed) for seed in seeds)
    overlap = sorted(FROZEN_CONFIRMATORY_SEEDS & set(values))
    if overlap:
        raise ValueError(
            "official PySR Transactions runs must not reuse frozen seeds: "
            f"{overlap}"
        )
    if len(values) != len(set(values)):
        raise ValueError("PySR seeds must be unique")
    return values


def _semantic_success(values: tuple[float, ...], threshold: float) -> float:
    return float(
        all(np.isfinite(value) for value in values)
        and max(values) <= threshold
    )


def _unsupported_row(
    *,
    benchmark: str,
    scenario: str,
    noise_ratio: float,
    samples_per_client: int,
    num_clients: int,
    seed: int,
    niterations: int,
    populations: int,
    population_size: int,
    maxsize: int,
) -> TransactionsPySRRow:
    return TransactionsPySRRow(
        benchmark=benchmark,
        scenario=scenario,
        noise_ratio=noise_ratio,
        samples_per_client=samples_per_client,
        num_clients=num_clients,
        seed=seed,
        method="official-pysr",
        grammar_supported=False,
        package_available=True,
        completed=False,
        niterations=niterations,
        populations=populations,
        population_size=population_size,
        maxsize=maxsize,
        nominal_population_updates=niterations * populations * population_size,
        runtime_seconds=0.0,
        interpolation_nmse=float("nan"),
        client_support_nmse=float("nan"),
        mild_extrapolation_nmse=float("nan"),
        strong_extrapolation_nmse=float("nan"),
        semantic_all_1e4=float("nan"),
        semantic_all_1e3=float("nan"),
        semantic_all_1e2=float("nan"),
        expression_complexity=-1,
        equation="",
        note=(
            "Unsupported condition: the shared official PySR grammar does not "
            "contain the restricted indicator-gated exception operator."
        ),
    )


def run_condition(
    *,
    benchmark: str,
    scenario: str,
    noise_ratio: float,
    samples_per_client: int,
    num_clients: int,
    seed: int,
    niterations: int,
    populations: int,
    population_size: int,
    maxsize: int,
    semantic_samples: int = 4000,
) -> TransactionsPySRRow:
    if scenario not in SUPPORTED_SCENARIOS:
        return _unsupported_row(
            benchmark=benchmark,
            scenario=scenario,
            noise_ratio=noise_ratio,
            samples_per_client=samples_per_client,
            num_clients=num_clients,
            seed=seed,
            niterations=niterations,
            populations=populations,
            population_size=population_size,
            maxsize=maxsize,
        )

    generated = generate_benchmark(
        benchmark,
        scenario=scenario,
        samples_per_client=samples_per_client,
        noise_ratio=noise_ratio,
        seed=seed,
        num_clients=num_clients,
    )
    x_interpolation, y_interpolation = generate_global_test_data(
        generated,
        samples=semantic_samples,
        seed=seed + 100_000,
    )
    output = run_pysr(
        generated.clients,
        x_interpolation,
        seed=seed,
        niterations=niterations,
        populations=populations,
        population_size=population_size,
        maxsize=maxsize,
    )
    if not output.available:
        return TransactionsPySRRow(
            benchmark=benchmark,
            scenario=scenario,
            noise_ratio=noise_ratio,
            samples_per_client=samples_per_client,
            num_clients=num_clients,
            seed=seed,
            method="official-pysr",
            grammar_supported=True,
            package_available=False,
            completed=False,
            niterations=niterations,
            populations=populations,
            population_size=population_size,
            maxsize=maxsize,
            nominal_population_updates=niterations * populations * population_size,
            runtime_seconds=output.runtime_seconds,
            interpolation_nmse=float("nan"),
            client_support_nmse=float("nan"),
            mild_extrapolation_nmse=float("nan"),
            strong_extrapolation_nmse=float("nan"),
            semantic_all_1e4=0.0,
            semantic_all_1e3=0.0,
            semantic_all_1e2=0.0,
            expression_complexity=-1,
            equation="",
            note=output.note,
        )

    interpolation_nmse = normalized_mse(output.predictions, y_interpolation)
    client_x = np.concatenate([client.x for client in generated.clients], axis=0)
    client_y = evaluate_terms(
        client_x,
        generated.target_coefficients,
        benchmark_catalog(scenario=scenario),
    )
    x_mild, y_mild = _extrapolation_data(
        generated,
        scale=1.25,
        samples=semantic_samples,
        seed=seed + 200_000,
    )
    x_strong, y_strong = _extrapolation_data(
        generated,
        scale=1.50,
        samples=semantic_samples,
        seed=seed + 300_000,
    )

    try:
        client_prediction, _ = evaluate_expression(output.equation, client_x)
        mild_prediction, _ = evaluate_expression(output.equation, x_mild)
        strong_prediction, _ = evaluate_expression(output.equation, x_strong)
        client_nmse = normalized_mse(client_prediction, client_y)
        mild_nmse = normalized_mse(mild_prediction, y_mild)
        strong_nmse = normalized_mse(strong_prediction, y_strong)
        complexity = expression_complexity(output.equation)
        completed = True
        note = output.note
    except (SyntaxError, ValueError, FloatingPointError, OverflowError) as exc:
        client_nmse = float("nan")
        mild_nmse = float("nan")
        strong_nmse = float("nan")
        complexity = -1
        completed = False
        note = f"Equation export parse failure: {type(exc).__name__}: {exc}"

    semantic_values = (
        interpolation_nmse,
        client_nmse,
        mild_nmse,
        strong_nmse,
    )
    return TransactionsPySRRow(
        benchmark=benchmark,
        scenario=scenario,
        noise_ratio=noise_ratio,
        samples_per_client=samples_per_client,
        num_clients=num_clients,
        seed=seed,
        method="official-pysr",
        grammar_supported=True,
        package_available=True,
        completed=completed,
        niterations=niterations,
        populations=populations,
        population_size=population_size,
        maxsize=maxsize,
        nominal_population_updates=niterations * populations * population_size,
        runtime_seconds=output.runtime_seconds,
        interpolation_nmse=interpolation_nmse,
        client_support_nmse=client_nmse,
        mild_extrapolation_nmse=mild_nmse,
        strong_extrapolation_nmse=strong_nmse,
        semantic_all_1e4=_semantic_success(semantic_values, 1e-4),
        semantic_all_1e3=_semantic_success(semantic_values, 1e-3),
        semantic_all_1e2=_semantic_success(semantic_values, 1e-2),
        expression_complexity=complexity,
        equation=output.equation,
        note=note,
    )


def run_matrix(
    *,
    benchmarks: tuple[str, ...] = tuple(BENCHMARKS),
    scenarios: tuple[str, ...] = ("complementary", "spurious"),
    noise_ratios: tuple[float, ...] = (0.03, 0.10),
    samples_per_client: int = 300,
    num_clients: int = 4,
    seeds: tuple[int, ...] = DEFAULT_DEVELOPMENT_SEEDS,
    niterations: int = 40,
    populations: int = 6,
    population_size: int = 40,
    maxsize: int = 18,
    semantic_samples: int = 4000,
) -> list[TransactionsPySRRow]:
    seeds = validate_fresh_seeds(seeds)
    unknown_benchmarks = sorted(set(benchmarks) - set(BENCHMARKS))
    if unknown_benchmarks:
        raise KeyError(f"unknown benchmarks: {unknown_benchmarks}")
    rows: list[TransactionsPySRRow] = []
    for benchmark in benchmarks:
        for scenario in scenarios:
            for noise_ratio in noise_ratios:
                for seed in seeds:
                    rows.append(
                        run_condition(
                            benchmark=benchmark,
                            scenario=scenario,
                            noise_ratio=noise_ratio,
                            samples_per_client=samples_per_client,
                            num_clients=num_clients,
                            seed=seed,
                            niterations=niterations,
                            populations=populations,
                            population_size=population_size,
                            maxsize=maxsize,
                            semantic_samples=semantic_samples,
                        )
                    )
    return rows


def write_outputs(
    rows: list[TransactionsPySRRow],
    output: Path,
    manifest_path: Path,
) -> None:
    if not rows:
        raise ValueError("no official PySR rows to write")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].to_dict()))
        writer.writeheader()
        writer.writerows(row.to_dict() for row in rows)

    try:
        pysr_version = metadata.version("pysr")
    except metadata.PackageNotFoundError:
        pysr_version = "unavailable"
    supported = [row for row in rows if row.grammar_supported]
    completed = [row for row in supported if row.completed]
    manifest = {
        "schema_version": 1,
        "status": "completed" if len(completed) == len(supported) else "incomplete",
        "method": "official-pysr",
        "python": platform.python_version(),
        "pysr_version": pysr_version,
        "rows": len(rows),
        "supported_rows": len(supported),
        "unsupported_rows": len(rows) - len(supported),
        "completed_supported_rows": len(completed),
        "seed_policy": "fresh seeds; 9001--9020 rejected",
        "scientific_boundary": [
            "Official pooled-data PySR comparison.",
            "Indicator-gated exception conditions are unsupported by the shared grammar.",
            "Nominal population updates are not exact candidate-evaluation counts.",
            "Equal-wall-clock and equal-evaluation regimes require separate calibration."
        ],
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def _parse_strings(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _parse_floats(value: str) -> tuple[float, ...]:
    return tuple(float(item.strip()) for item in value.split(",") if item.strip())


def _parse_ints(value: str) -> tuple[int, ...]:
    values: list[int] = []
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        if "-" in item:
            start_text, end_text = item.split("-", 1)
            start, end = int(start_text), int(end_text)
            if end < start:
                raise ValueError(f"invalid seed range: {item}")
            values.extend(range(start, end + 1))
        else:
            values.append(int(item))
    return tuple(values)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a fresh-seed official PySR Transactions comparison."
    )
    parser.add_argument("--benchmarks", default=",".join(BENCHMARKS))
    parser.add_argument("--scenarios", default="complementary,spurious")
    parser.add_argument("--noise", default="0.03,0.10")
    parser.add_argument("--samples", type=int, default=300)
    parser.add_argument("--clients", type=int, default=4)
    parser.add_argument(
        "--seeds", default=",".join(map(str, DEFAULT_DEVELOPMENT_SEEDS))
    )
    parser.add_argument("--niterations", type=int, default=40)
    parser.add_argument("--populations", type=int, default=6)
    parser.add_argument("--population-size", type=int, default=40)
    parser.add_argument("--maxsize", type=int, default=18)
    parser.add_argument("--semantic-samples", type=int, default=4000)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/transactions_pysr/rows.csv"),
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("results/transactions_pysr/manifest.json"),
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    rows = run_matrix(
        benchmarks=_parse_strings(args.benchmarks),
        scenarios=_parse_strings(args.scenarios),
        noise_ratios=_parse_floats(args.noise),
        samples_per_client=args.samples,
        num_clients=args.clients,
        seeds=_parse_ints(args.seeds),
        niterations=args.niterations,
        populations=args.populations,
        population_size=args.population_size,
        maxsize=args.maxsize,
        semantic_samples=args.semantic_samples,
    )
    unavailable = [row for row in rows if row.grammar_supported and not row.package_available]
    if unavailable:
        raise RuntimeError('official PySR is unavailable; install with ".[sr]"')
    write_outputs(rows, args.output, args.manifest)
    print(f"Wrote {len(rows)} official PySR rows to {args.output}")
    print(f"Wrote manifest to {args.manifest}")


if __name__ == "__main__":
    main()
