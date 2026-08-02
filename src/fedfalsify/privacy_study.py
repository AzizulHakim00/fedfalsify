"""Certificate sensitivity and noise-budgeted FedFalsify ablation runner."""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean
from time import perf_counter

import numpy as np

from .baselines import fedfalsify_method
from .benchmarks import benchmark_catalog, generate_benchmark, generate_global_test_data
from .client import FederatedFalsifierClient
from .privacy import NoisyCertificateClient, leave_one_out_sensitivity
from .replacement import FederatedCoreReplacement

DEFAULT_MULTIPLIERS = (0.0, 0.10, 0.25, 0.50, 1.0)
DEFAULT_SEEDS = tuple(range(7001, 7006))


@dataclass(frozen=True)
class PrivacyStudyRow:
    benchmark: str
    scenario: str
    seed: int
    samples_per_client: int
    noise_ratio: float
    certificate_noise_multiplier: float
    exact_recovery: float
    test_nmse: float
    exception_recovered: float
    runtime_seconds: float
    communication_bytes: int
    discovered_terms: str
    loo_median_l2_change: float
    loo_maximum_l2_change: float
    privacy_scope: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _run_once(
    *,
    benchmark: str,
    scenario: str,
    seed: int,
    samples_per_client: int,
    noise_ratio: float,
    multiplier: float,
) -> PrivacyStudyRow:
    generated = generate_benchmark(
        benchmark,
        scenario=scenario,
        samples_per_client=samples_per_client,
        noise_ratio=noise_ratio,
        seed=seed,
        num_clients=4,
    )
    catalog = benchmark_catalog(scenario=scenario)
    clean_clients = [
        FederatedFalsifierClient(dataset, catalog) for dataset in generated.clients
    ]
    wrapped = [
        NoisyCertificateClient(
            client,
            noise_multiplier=multiplier,
            clip_value=10.0,
            seed=seed + index * 1009,
        )
        for index, client in enumerate(clean_clients)
    ]
    target_mse = max(generated.noise_std**2 * 2.5, 1e-8)
    start = perf_counter()
    base = fedfalsify_method(
        wrapped,
        catalog,
        max_terms=6,
        target_mse=target_mse,
        min_repair_score=0.05,
        use_coefficient_heterogeneity=True,
    )
    refined = FederatedCoreReplacement(
        wrapped,
        catalog,
        max_rounds=3,
        max_removed_terms=2,
    ).refine(base.candidate)
    runtime = perf_counter() - start
    candidate = refined.candidate
    predicted = {
        term
        for term, coefficient in zip(candidate.active_terms, candidate.coefficients)
        if term != "1" and abs(coefficient) >= 1e-3
    }
    target = set(generated.target_terms)
    x_test, y_test = generate_global_test_data(generated, seed=seed + 100_000)
    prediction = candidate.predict(x_test, catalog)
    nmse = float(np.mean((y_test - prediction) ** 2) / max(np.var(y_test), 1e-12))
    exception_term = "I(x3>1)*x3^2"
    exception = float(
        exception_term in predicted
        if scenario == "exception"
        else exception_term not in predicted
    )
    sensitivity = leave_one_out_sensitivity(
        generated.clients[0],
        catalog,
        candidate,
        max_records=min(16, samples_per_client),
        seed=seed + 91,
    )
    return PrivacyStudyRow(
        benchmark=benchmark,
        scenario=scenario,
        seed=seed,
        samples_per_client=samples_per_client,
        noise_ratio=noise_ratio,
        certificate_noise_multiplier=multiplier,
        exact_recovery=float(predicted == target),
        test_nmse=nmse,
        exception_recovered=exception,
        runtime_seconds=runtime,
        communication_bytes=base.communication_bytes + refined.communication_bytes,
        discovered_terms=";".join(sorted(predicted)),
        loo_median_l2_change=sensitivity.median_l2_change,
        loo_maximum_l2_change=sensitivity.maximum_l2_change,
        privacy_scope=(
            "certificate-only Gaussian noise; fit summaries remain unperturbed; "
            "not a differential-privacy guarantee"
        ),
    )


def run_study(
    *,
    benchmarks: tuple[str, ...] = ("base",),
    scenarios: tuple[str, ...] = ("complementary", "exception"),
    seeds: tuple[int, ...] = DEFAULT_SEEDS,
    multipliers: tuple[float, ...] = DEFAULT_MULTIPLIERS,
    samples_per_client: int = 120,
    noise_ratio: float = 0.03,
) -> list[PrivacyStudyRow]:
    rows: list[PrivacyStudyRow] = []
    for benchmark in benchmarks:
        for scenario in scenarios:
            for seed in seeds:
                for multiplier in multipliers:
                    rows.append(
                        _run_once(
                            benchmark=benchmark,
                            scenario=scenario,
                            seed=seed,
                            samples_per_client=samples_per_client,
                            noise_ratio=noise_ratio,
                            multiplier=multiplier,
                        )
                    )
    return rows


def write_csv(rows: list[PrivacyStudyRow], output: Path) -> None:
    if not rows:
        raise ValueError("no privacy-study rows to write")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].to_dict()))
        writer.writeheader()
        writer.writerows(row.to_dict() for row in rows)


def print_summary(rows: list[PrivacyStudyRow]) -> None:
    print("Certificate-noise ablation (not formal DP)")
    print("=" * 88)
    print(f"{'multiplier':>12} {'runs':>6} {'exact':>9} {'NMSE':>12} {'exception':>11}")
    for multiplier in sorted({row.certificate_noise_multiplier for row in rows}):
        selected = [row for row in rows if row.certificate_noise_multiplier == multiplier]
        print(
            f"{multiplier:12.3f} {len(selected):6d} "
            f"{mean(row.exact_recovery for row in selected):9.3f} "
            f"{mean(row.test_nmse for row in selected):12.6f} "
            f"{mean(row.exception_recovered for row in selected):11.3f}"
        )
    print(
        "\nLeave-one-out sensitivity is a leakage proxy, not a membership-inference proof."
    )


def _parse_strings(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _parse_ints(value: str) -> tuple[int, ...]:
    return tuple(int(item.strip()) for item in value.split(",") if item.strip())


def _parse_floats(value: str) -> tuple[float, ...]:
    return tuple(float(item.strip()) for item in value.split(",") if item.strip())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run certificate sensitivity and noise-budget ablations."
    )
    parser.add_argument("--benchmarks", default="base")
    parser.add_argument("--scenarios", default="complementary,exception")
    parser.add_argument("--seeds", default=",".join(map(str, DEFAULT_SEEDS)))
    parser.add_argument("--multipliers", default=",".join(map(str, DEFAULT_MULTIPLIERS)))
    parser.add_argument("--samples", type=int, default=120)
    parser.add_argument("--noise-ratio", type=float, default=0.03)
    parser.add_argument(
        "--output", type=Path, default=Path("results/v06_privacy_ablation.csv")
    )
    parser.add_argument("--smoke", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.smoke:
        settings = {
            "benchmarks": ("base",),
            "scenarios": ("complementary",),
            "seeds": (7001,),
            "multipliers": (0.0, 0.25),
            "samples_per_client": 60,
            "noise_ratio": 0.03,
        }
    else:
        settings = {
            "benchmarks": _parse_strings(args.benchmarks),
            "scenarios": _parse_strings(args.scenarios),
            "seeds": _parse_ints(args.seeds),
            "multipliers": _parse_floats(args.multipliers),
            "samples_per_client": args.samples,
            "noise_ratio": args.noise_ratio,
        }
    rows = run_study(**settings)
    write_csv(rows, args.output)
    print_summary(rows)
    print(f"\nWrote {len(rows)} rows to {args.output}")


if __name__ == "__main__":
    main()
