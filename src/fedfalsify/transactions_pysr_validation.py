"""Preregistered matched validation of FedFalsify against official PySR.

This module evaluates both methods on identical fresh validation conditions.
The primary endpoint is deterministic all-domain semantic recovery at NMSE
1e-3 under the quality PySR budget.  Exception conditions are deliberately
excluded because the shared official PySR grammar lacks the restricted gate.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass, replace
from importlib import metadata
import json
from pathlib import Path
import platform
import subprocess
from time import perf_counter
from typing import Iterable

import numpy as np

from .baselines import fedfalsify_method
from .benchmarks import (
    BENCHMARKS,
    benchmark_catalog,
    evaluate_terms,
    generate_benchmark,
    generate_global_test_data,
)
from .client import FederatedFalsifierClient
from .replacement import FederatedCoreReplacement
from .statistics import holm_adjust, mcnemar_exact, paired_bootstrap_difference, wilson_interval
from .transactions_analysis import _extrapolation_data, normalized_mse
from .transactions_pysr import run_condition


FROZEN_CONFIRMATORY_SEEDS = frozenset(range(9001, 9021))
DEVELOPMENT_SEEDS = frozenset(range(10001, 10501))
VALIDATION_SEEDS = tuple(range(10501, 10506))
FINAL_CONFIRMATION_START = 11001
SUPPORTED_SCENARIOS = ("complementary", "spurious")

BUDGETS: dict[str, dict[str, int]] = {
    "compact": {
        "niterations": 5,
        "populations": 2,
        "population_size": 20,
        "maxsize": 18,
    },
    "quality": {
        "niterations": 20,
        "populations": 4,
        "population_size": 30,
        "maxsize": 18,
    },
}


@dataclass(frozen=True)
class PySRValidationRow:
    benchmark: str
    scenario: str
    noise_ratio: float
    samples_per_client: int
    num_clients: int
    seed: int
    regime: str
    method: str
    grammar_supported: bool
    completed: bool
    raw_data_pooled: bool
    strict_exact_recovery: float
    semantic_all_1e4: float
    semantic_all_1e3: float
    semantic_all_1e2: float
    interpolation_nmse: float
    client_support_nmse: float
    mild_extrapolation_nmse: float
    strong_extrapolation_nmse: float
    expression_complexity: int
    runtime_seconds: float
    communication_bytes: int
    nominal_population_updates: int
    expression: str
    note: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def validate_validation_seeds(seeds: Iterable[int]) -> tuple[int, ...]:
    values = tuple(int(seed) for seed in seeds)
    if not values:
        raise ValueError("at least one validation seed is required")
    if len(values) != len(set(values)):
        raise ValueError("validation seeds must be unique")
    forbidden = sorted((FROZEN_CONFIRMATORY_SEEDS | DEVELOPMENT_SEEDS) & set(values))
    if forbidden:
        raise ValueError(f"validation study cannot reuse frozen/development seeds: {forbidden}")
    final_overlap = sorted(seed for seed in values if seed >= FINAL_CONFIRMATION_START)
    if final_overlap:
        raise ValueError(
            "validation study must leave final confirmation seeds untouched: "
            f"{final_overlap}"
        )
    unexpected = sorted(set(values) - set(VALIDATION_SEEDS))
    if unexpected:
        raise ValueError(
            "the preregistered validation study permits only seeds 10501--10505: "
            f"{unexpected}"
        )
    return values


def _semantic_success(values: tuple[float, ...], threshold: float) -> float:
    return float(
        all(np.isfinite(value) for value in values)
        and max(values) <= threshold
    )


def _fit_fedfalsify(generated) -> tuple[object, float, int, str]:
    catalog = benchmark_catalog(scenario=generated.scenario)
    clients = [FederatedFalsifierClient(dataset, catalog) for dataset in generated.clients]
    target_mse = max(generated.noise_std**2 * 2.5, 1e-8)
    start = perf_counter()
    base = fedfalsify_method(
        clients,
        catalog,
        max_terms=6,
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
    runtime = perf_counter() - start
    communication = base.communication_bytes + refined.communication_bytes
    stop_reason = f"{base.stop_reason}; {refined.stop_reason}"
    return refined.candidate, runtime, communication, stop_reason


def _fedfalsify_row(
    *,
    benchmark: str,
    scenario: str,
    noise_ratio: float,
    samples_per_client: int,
    num_clients: int,
    seed: int,
) -> PySRValidationRow:
    generated = generate_benchmark(
        benchmark,
        scenario=scenario,
        samples_per_client=samples_per_client,
        noise_ratio=noise_ratio,
        seed=seed,
        num_clients=num_clients,
    )
    candidate, runtime, communication, stop_reason = _fit_fedfalsify(generated)
    catalog = benchmark_catalog(scenario=scenario)
    active = {
        term
        for term, coefficient in zip(candidate.active_terms, candidate.coefficients)
        if term != "1" and abs(float(coefficient)) >= 1e-3
    }
    strict = float(active == set(generated.target_terms))

    x_interpolation, y_interpolation = generate_global_test_data(
        generated,
        samples=4000,
        seed=seed + 100_000,
    )
    client_x = np.concatenate([client.x for client in generated.clients], axis=0)
    client_y = evaluate_terms(client_x, generated.target_coefficients, catalog)
    x_mild, y_mild = _extrapolation_data(
        generated,
        scale=1.25,
        samples=4000,
        seed=seed + 200_000,
    )
    x_strong, y_strong = _extrapolation_data(
        generated,
        scale=1.50,
        samples=4000,
        seed=seed + 300_000,
    )
    values = (
        normalized_mse(candidate.predict(x_interpolation, catalog), y_interpolation),
        normalized_mse(candidate.predict(client_x, catalog), client_y),
        normalized_mse(candidate.predict(x_mild, catalog), y_mild),
        normalized_mse(candidate.predict(x_strong, catalog), y_strong),
    )
    return PySRValidationRow(
        benchmark=benchmark,
        scenario=scenario,
        noise_ratio=noise_ratio,
        samples_per_client=samples_per_client,
        num_clients=num_clients,
        seed=seed,
        regime="",
        method="fedfalsify-v05",
        grammar_supported=True,
        completed=True,
        raw_data_pooled=False,
        strict_exact_recovery=strict,
        semantic_all_1e4=_semantic_success(values, 1e-4),
        semantic_all_1e3=_semantic_success(values, 1e-3),
        semantic_all_1e2=_semantic_success(values, 1e-2),
        interpolation_nmse=values[0],
        client_support_nmse=values[1],
        mild_extrapolation_nmse=values[2],
        strong_extrapolation_nmse=values[3],
        expression_complexity=catalog.complexity(candidate.active_terms),
        runtime_seconds=runtime,
        communication_bytes=communication,
        nominal_population_updates=0,
        expression=candidate.expression(catalog),
        note=stop_reason,
    )


def _pysr_row(
    *,
    benchmark: str,
    scenario: str,
    noise_ratio: float,
    samples_per_client: int,
    num_clients: int,
    seed: int,
    regime: str,
) -> PySRValidationRow:
    budget = BUDGETS[regime]
    item = run_condition(
        benchmark=benchmark,
        scenario=scenario,
        noise_ratio=noise_ratio,
        samples_per_client=samples_per_client,
        num_clients=num_clients,
        seed=seed,
        semantic_samples=4000,
        **budget,
    )
    return PySRValidationRow(
        benchmark=item.benchmark,
        scenario=item.scenario,
        noise_ratio=item.noise_ratio,
        samples_per_client=item.samples_per_client,
        num_clients=item.num_clients,
        seed=item.seed,
        regime=regime,
        method="official-pysr",
        grammar_supported=item.grammar_supported,
        completed=item.completed,
        raw_data_pooled=True,
        strict_exact_recovery=float("nan"),
        semantic_all_1e4=item.semantic_all_1e4,
        semantic_all_1e3=item.semantic_all_1e3,
        semantic_all_1e2=item.semantic_all_1e2,
        interpolation_nmse=item.interpolation_nmse,
        client_support_nmse=item.client_support_nmse,
        mild_extrapolation_nmse=item.mild_extrapolation_nmse,
        strong_extrapolation_nmse=item.strong_extrapolation_nmse,
        expression_complexity=item.expression_complexity,
        runtime_seconds=item.runtime_seconds,
        communication_bytes=0,
        nominal_population_updates=item.nominal_population_updates,
        expression=item.equation,
        note=item.note,
    )


def run_seed(
    *,
    seed: int,
    benchmarks: tuple[str, ...] = tuple(BENCHMARKS),
    scenarios: tuple[str, ...] = SUPPORTED_SCENARIOS,
    noise_ratios: tuple[float, ...] = (0.03, 0.10),
    samples_per_client: int = 300,
    num_clients: int = 4,
    regimes: tuple[str, ...] = tuple(BUDGETS),
) -> list[PySRValidationRow]:
    validate_validation_seeds((seed,))
    unknown_benchmarks = sorted(set(benchmarks) - set(BENCHMARKS))
    if unknown_benchmarks:
        raise KeyError(f"unknown benchmarks: {unknown_benchmarks}")
    unknown_scenarios = sorted(set(scenarios) - set(SUPPORTED_SCENARIOS))
    if unknown_scenarios:
        raise ValueError(f"unsupported primary validation scenarios: {unknown_scenarios}")
    unknown_regimes = sorted(set(regimes) - set(BUDGETS))
    if unknown_regimes:
        raise KeyError(f"unknown PySR budgets: {unknown_regimes}")

    rows: list[PySRValidationRow] = []
    for benchmark in benchmarks:
        for scenario in scenarios:
            for noise_ratio in noise_ratios:
                fed = _fedfalsify_row(
                    benchmark=benchmark,
                    scenario=scenario,
                    noise_ratio=noise_ratio,
                    samples_per_client=samples_per_client,
                    num_clients=num_clients,
                    seed=seed,
                )
                for regime in regimes:
                    rows.append(replace(fed, regime=regime))
                    rows.append(
                        _pysr_row(
                            benchmark=benchmark,
                            scenario=scenario,
                            noise_ratio=noise_ratio,
                            samples_per_client=samples_per_client,
                            num_clients=num_clients,
                            seed=seed,
                            regime=regime,
                        )
                    )
    return rows


def _identity(row: PySRValidationRow) -> tuple[object, ...]:
    return (
        row.benchmark,
        row.scenario,
        row.noise_ratio,
        row.samples_per_client,
        row.num_clients,
        row.seed,
        row.regime,
    )


def summarize(rows: list[PySRValidationRow]) -> dict[str, object]:
    if not rows:
        raise ValueError("no validation rows supplied")
    identities: dict[tuple[object, ...], dict[str, PySRValidationRow]] = {}
    for row in rows:
        identities.setdefault(_identity(row), {})[row.method] = row
    if any(set(pair) != {"fedfalsify-v05", "official-pysr"} for pair in identities.values()):
        raise ValueError("every validation condition must contain exactly two methods")

    method_summary: dict[str, dict[str, object]] = {}
    for regime in BUDGETS:
        for method in ("fedfalsify-v05", "official-pysr"):
            subset = [row for row in rows if row.regime == regime and row.method == method]
            successes = int(sum(row.semantic_all_1e3 for row in subset))
            method_summary[f"{regime}:{method}"] = {
                "runs": len(subset),
                "completed": int(sum(row.completed for row in subset)),
                "semantic_all_1e4": float(np.mean([row.semantic_all_1e4 for row in subset])),
                "semantic_all_1e3": float(np.mean([row.semantic_all_1e3 for row in subset])),
                "semantic_all_1e2": float(np.mean([row.semantic_all_1e2 for row in subset])),
                "semantic_1e3_wilson_95": wilson_interval(successes, len(subset)),
                "strong_extrapolation_nmse": float(
                    np.mean([row.strong_extrapolation_nmse for row in subset])
                ),
                "runtime_seconds": float(np.mean([row.runtime_seconds for row in subset])),
                "expression_complexity": float(
                    np.mean([row.expression_complexity for row in subset])
                ),
                "raw_data_pooled": method == "official-pysr",
                "strict_exact_recovery": (
                    float(np.mean([row.strict_exact_recovery for row in subset]))
                    if method == "fedfalsify-v05"
                    else None
                ),
            }

    paired: dict[str, dict[str, object]] = {}
    primary_p: dict[str, float] = {}
    for regime in BUDGETS:
        ordered = sorted(
            (identity, pair)
            for identity, pair in identities.items()
            if identity[-1] == regime
        )
        fed = [pair["fedfalsify-v05"] for _, pair in ordered]
        pysr = [pair["official-pysr"] for _, pair in ordered]
        semantic_test = mcnemar_exact(
            [row.semantic_all_1e3 for row in fed],
            [row.semantic_all_1e3 for row in pysr],
        )
        primary_p[regime] = semantic_test.exact_p_value
        paired[regime] = {
            "pairs": len(fed),
            "semantic_1e3_mcnemar": asdict(semantic_test),
            "semantic_1e2_mcnemar": asdict(
                mcnemar_exact(
                    [row.semantic_all_1e2 for row in fed],
                    [row.semantic_all_1e2 for row in pysr],
                )
            ),
            "strong_extrapolation_pysr_minus_fedfalsify": asdict(
                paired_bootstrap_difference(
                    [row.strong_extrapolation_nmse for row in fed],
                    [row.strong_extrapolation_nmse for row in pysr],
                    resamples=5000,
                    seed=20260804,
                )
            ),
            "runtime_pysr_minus_fedfalsify": asdict(
                paired_bootstrap_difference(
                    [row.runtime_seconds for row in fed],
                    [row.runtime_seconds for row in pysr],
                    resamples=5000,
                    seed=20260805,
                )
            ),
        }
    adjusted = holm_adjust(primary_p)
    for regime, value in adjusted.items():
        paired[regime]["semantic_1e3_holm_adjusted_p"] = value

    by_benchmark: dict[str, dict[str, float]] = {}
    for benchmark in BENCHMARKS:
        for regime in BUDGETS:
            for method in ("fedfalsify-v05", "official-pysr"):
                subset = [
                    row
                    for row in rows
                    if row.benchmark == benchmark
                    and row.regime == regime
                    and row.method == method
                ]
                if subset:
                    by_benchmark[f"{benchmark}:{regime}:{method}"] = {
                        "runs": len(subset),
                        "semantic_all_1e3": float(
                            np.mean([row.semantic_all_1e3 for row in subset])
                        ),
                        "semantic_all_1e2": float(
                            np.mean([row.semantic_all_1e2 for row in subset])
                        ),
                        "strong_extrapolation_nmse": float(
                            np.mean([row.strong_extrapolation_nmse for row in subset])
                        ),
                    }

    return {
        "schema_version": 1,
        "status": "validation",
        "primary_endpoint": "quality-regime all-domain semantic recovery at NMSE 1e-3",
        "rows": len(rows),
        "pairs": len(identities),
        "seeds": sorted({row.seed for row in rows}),
        "methods": method_summary,
        "paired": paired,
        "by_benchmark": by_benchmark,
        "protocol": {
            "benchmarks": list(BENCHMARKS),
            "scenarios": list(SUPPORTED_SCENARIOS),
            "noise_ratios": [0.03, 0.10],
            "samples_per_client": 300,
            "clients": 4,
            "validation_seeds": list(VALIDATION_SEEDS),
            "budgets": BUDGETS,
            "semantic_samples_per_domain": 4000,
            "final_confirmation_start": FINAL_CONFIRMATION_START,
        },
        "scientific_boundary": [
            "Official PySR pools raw observations; FedFalsify does not.",
            "Strict structural recovery is reported only for finite-catalog FedFalsify.",
            "Primary matched inference uses deterministic all-domain semantic recovery.",
            "Exception scenarios are excluded because the shared PySR grammar is unsupported.",
            "Seeds 11001 and above remain untouched for final confirmation.",
        ],
    }


def write_csv(rows: list[PySRValidationRow], output: Path) -> None:
    if not rows:
        raise ValueError("no validation rows to write")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].to_dict()))
        writer.writeheader()
        writer.writerows(row.to_dict() for row in rows)


def read_csv(paths: Iterable[Path]) -> list[PySRValidationRow]:
    rows: list[PySRValidationRow] = []
    bool_fields = {"grammar_supported", "completed", "raw_data_pooled"}
    int_fields = {
        "samples_per_client",
        "num_clients",
        "seed",
        "expression_complexity",
        "communication_bytes",
        "nominal_population_updates",
    }
    float_fields = {
        "noise_ratio",
        "strict_exact_recovery",
        "semantic_all_1e4",
        "semantic_all_1e3",
        "semantic_all_1e2",
        "interpolation_nmse",
        "client_support_nmse",
        "mild_extrapolation_nmse",
        "strong_extrapolation_nmse",
        "runtime_seconds",
    }
    for path in paths:
        with path.open(newline="", encoding="utf-8") as handle:
            for item in csv.DictReader(handle):
                values: dict[str, object] = dict(item)
                for field in bool_fields:
                    values[field] = str(item[field]).lower() == "true"
                for field in int_fields:
                    values[field] = int(item[field])
                for field in float_fields:
                    values[field] = float(item[field])
                rows.append(PySRValidationRow(**values))
    return rows


def environment_manifest(seed: int) -> dict[str, object]:
    try:
        pysr_version = metadata.version("pysr")
    except metadata.PackageNotFoundError:
        pysr_version = "unavailable"
    try:
        julia = subprocess.check_output(["julia", "--version"], text=True).strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        julia = "unavailable"
    return {
        "schema_version": 1,
        "status": "seed-complete",
        "seed": seed,
        "python": platform.python_version(),
        "pysr": pysr_version,
        "julia": julia,
        "budgets": BUDGETS,
        "seed_policy": "preregistered validation seed; final seeds untouched",
    }


def _parse_strings(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _parse_floats(value: str) -> tuple[float, ...]:
    return tuple(float(item.strip()) for item in value.split(",") if item.strip())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    seed_parser = subparsers.add_parser("run-seed")
    seed_parser.add_argument("--seed", type=int, required=True)
    seed_parser.add_argument("--benchmarks", default=",".join(BENCHMARKS))
    seed_parser.add_argument("--scenarios", default=",".join(SUPPORTED_SCENARIOS))
    seed_parser.add_argument("--noise", default="0.03,0.10")
    seed_parser.add_argument("--samples", type=int, default=300)
    seed_parser.add_argument("--clients", type=int, default=4)
    seed_parser.add_argument("--regimes", default=",".join(BUDGETS))
    seed_parser.add_argument("--output", type=Path, required=True)
    seed_parser.add_argument("--manifest", type=Path, required=True)

    aggregate_parser = subparsers.add_parser("aggregate")
    aggregate_parser.add_argument("--inputs", nargs="+", type=Path, required=True)
    aggregate_parser.add_argument("--output", type=Path, required=True)
    aggregate_parser.add_argument("--summary", type=Path, required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "run-seed":
        rows = run_seed(
            seed=args.seed,
            benchmarks=_parse_strings(args.benchmarks),
            scenarios=_parse_strings(args.scenarios),
            noise_ratios=_parse_floats(args.noise),
            samples_per_client=args.samples,
            num_clients=args.clients,
            regimes=_parse_strings(args.regimes),
        )
        write_csv(rows, args.output)
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(
            json.dumps(environment_manifest(args.seed), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        print(f"Wrote {len(rows)} validation rows for seed {args.seed}")
        return

    rows = read_csv(args.inputs)
    validate_validation_seeds({row.seed for row in rows})
    write_csv(rows, args.output)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(
        json.dumps(summarize(rows), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(f"Aggregated {len(rows)} rows from {len(args.inputs)} files")


if __name__ == "__main__":
    main()
